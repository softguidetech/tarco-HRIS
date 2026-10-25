# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .tarco_common import tarco_daily_wage, tarco_hourly_wage, tarco_post_adjustment


class TarcoHrPenaltyRule(models.Model):
    _name = 'tarco.hr.penalty.rule'
    _description = 'Penalty Rule'
    _order = 'code'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    category = fields.Selection([
        ('late', 'Lateness'),
        ('absence', 'Absence'),
        ('conduct', 'Conduct'),
    ], required=True, default='conduct')
    calculation = fields.Selection([
        ('fixed', 'Fixed amount'),
        ('days', 'Days of wage'),
        ('hours', 'Hours of wage'),
        ('percent', 'Percent of basic salary'),
    ], required=True, default='days')
    fixed_amount = fields.Float()
    default_days = fields.Float(default=1.0)
    default_hours = fields.Float()
    default_percent = fields.Float()
    reason_text = fields.Text(required=True, translate=True)
    active = fields.Boolean(default=True)
    auto_from_attendance = fields.Boolean(string='Suggest from attendance')

    _code_unique = models.Constraint('unique(code)', 'Penalty rule code must be unique.')

    def amount_for(self, employee, days=None, hours=None):
        self.ensure_one()
        days = self.default_days if days is None else days
        hours = self.default_hours if hours is None else hours
        if self.calculation == 'fixed':
            return self.fixed_amount or 0.0
        if self.calculation == 'days':
            return (days or 0.0) * tarco_daily_wage(employee)
        if self.calculation == 'hours':
            return (hours or 0.0) * tarco_hourly_wage(employee)
        basic = employee.tarco_basic_wage or employee.tarco_gross_wage or 0.0
        return basic * (self.default_percent or 0.0) / 100.0


class TarcoHrPenalty(models.Model):
    _name = 'tarco.hr.penalty'
    _description = 'Employee Penalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'penalty_date desc, id desc'

    name = fields.Char(default='/', copy=False)
    rule_id = fields.Many2one('tarco.hr.penalty.rule', required=True, tracking=True)
    penalty_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    start_date = fields.Date(string='Applied from', default=fields.Date.context_today)
    reason = fields.Text(
        string='Reason',
        required=True,
        help='Why this penalty applies. Generated penalties list the attendance facts to check.',
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Fill from department')
    line_ids = fields.One2many('tarco.hr.penalty.line', 'penalty_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_amount = fields.Monetary(compute='_compute_total_amount', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for penalty in self:
            penalty.total_amount = sum(penalty.line_ids.mapped('amount'))

    @api.onchange('rule_id')
    def _onchange_rule_id(self):
        if self.rule_id:
            self.reason = self.rule_id.reason_text

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.penalty') or '/'
            if vals.get('rule_id') and not vals.get('reason'):
                vals['reason'] = self.env['tarco.hr.penalty.rule'].browse(vals['rule_id']).reason_text
        return super().create(vals_list)

    def action_fill_department(self):
        for penalty in self:
            if not penalty.department_id:
                raise UserError(_('Choose a department first.'))
            employees = self.env['hr.employee'].search([
                ('department_id', '=', penalty.department_id.id),
                ('company_id', '=', penalty.company_id.id),
            ])
            existing = set(penalty.line_ids.employee_id.ids)
            penalty.write({'line_ids': [
                (0, 0, {'employee_id': employee.id})
                for employee in employees if employee.id not in existing
            ]})

    def action_confirm(self):
        drafts = self.filtered(lambda penalty: penalty.state == 'draft')
        for penalty in drafts:
            for line in penalty.line_ids:
                if line.salary_attachment_id or line.amount <= 0:
                    continue
                attachment = tarco_post_adjustment(
                    self.env, line.employee_id, False, line.amount,
                    _('Penalty %s') % penalty.rule_id.name, penalty.start_date or penalty.penalty_date,
                )
                line.salary_attachment_id = attachment
            penalty.state = 'confirmed'
        if not drafts:
            message = _('No draft penalties to confirm.')
            kind = 'warning'
        else:
            message = _('%s penalty/penalties confirmed and posted to payroll.') % len(drafts)
            kind = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': kind,
                'message': message,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_refresh_reason(self):
        Day = self.env['tarco.hr.attendance.day']
        updated = self.env['tarco.hr.penalty']
        for penalty in self:
            if penalty.state == 'cancel' or not penalty.line_ids:
                continue
            if penalty.rule_id.category not in ('late', 'absence'):
                continue
            kind = 'late' if penalty.rule_id.category == 'late' else 'absence'
            parts = []
            for line in penalty.line_ids:
                day = Day.search([
                    ('employee_id', '=', line.employee_id.id),
                    ('work_date', '=', penalty.penalty_date),
                ], limit=1)
                if day:
                    parts.append(day.attendance_penalty_reason(kind))
            if parts:
                penalty.reason = '\n\n'.join(parts)
                updated |= penalty
        if not updated:
            message = _('No attendance facts found to fill the reason.')
            kind = 'warning'
        else:
            message = _('Reason updated from attendance for %s penalty/penalties.') % len(updated)
            kind = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': kind,
                'message': message,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }


class TarcoHrPenaltyLine(models.Model):
    _name = 'tarco.hr.penalty.line'
    _description = 'Penalty Employee'

    penalty_id = fields.Many2one('tarco.hr.penalty', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='penalty_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    days = fields.Float()
    hours = fields.Float()
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=False)
    repeat_count = fields.Integer(compute='_compute_repeat_count')
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)
    basic_wage = fields.Monetary(related='employee_id.tarco_basic_wage')
    gross_wage = fields.Monetary(related='employee_id.tarco_gross_wage')

    @api.depends('employee_id', 'penalty_id.rule_id', 'days', 'hours')
    def _compute_amount(self):
        for line in self:
            rule = line.penalty_id.rule_id
            if not rule or not line.employee_id:
                line.amount = 0.0
                continue
            line.amount = rule.amount_for(
                line.employee_id,
                days=line.days if line.days else None,
                hours=line.hours if line.hours else None,
            )

    @api.depends('employee_id', 'penalty_id.rule_id', 'penalty_id.penalty_date')
    def _compute_repeat_count(self):
        for line in self:
            if not line.employee_id or not line.penalty_id.rule_id:
                line.repeat_count = 0
                continue
            line.repeat_count = self.search_count([
                ('employee_id', '=', line.employee_id.id),
                ('penalty_id.rule_id', '=', line.penalty_id.rule_id.id),
                ('penalty_id.state', '!=', 'cancel'),
                ('penalty_id.penalty_date', '<=', line.penalty_id.penalty_date or fields.Date.context_today(self)),
            ])
