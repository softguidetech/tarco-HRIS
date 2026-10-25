# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .tarco_common import tarco_daily_wage, tarco_post_adjustment


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    tarco_kind = fields.Selection([
        ('annual', 'Annual'),
        ('casual', 'Casual'),
        ('sick', 'Sick'),
        ('official', 'Official'),
        ('unpaid', 'Unpaid'),
        ('other', 'Other'),
    ], string='Tarco leave kind')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def write(self, vals):
        if self.env.context.get('install_mode'):
            self = self.with_context(leave_skip_state_check=True, leave_skip_date_check=True)
        return super().write(vals)

    def _check_date_state(self):
        if self.env.context.get('install_mode') or self.env.context.get('leave_skip_state_check'):
            return
        return super()._check_date_state()

    tarco_deduction_mode = fields.Selection([
        ('balance', 'From balance / full pay'),
        ('salary', 'Deduct from salary'),
        ('partial', 'Partial salary deduction'),
    ], string='Deduction', default='balance', tracking=True)
    tarco_deduction_percent = fields.Float(string='Deduction %')
    tarco_taken_month = fields.Float(string='Taken this month', compute='_compute_tarco_taken_month')
    tarco_remaining_days = fields.Float(string='Scheme balance', compute='_compute_tarco_taken_month')
    tarco_salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)

    @api.depends('employee_id', 'holiday_status_id', 'request_date_from')
    def _compute_tarco_taken_month(self):
        for leave in self:
            leave.tarco_taken_month = 0.0
            leave.tarco_remaining_days = 0.0
            if not leave.employee_id or not leave.holiday_status_id or not leave.request_date_from:
                continue
            month_start = leave.request_date_from.replace(day=1)
            next_month = month_start.month + 1
            year = month_start.year + (1 if next_month == 13 else 0)
            next_month = 1 if next_month == 13 else next_month
            month_end = month_start.replace(year=year, month=next_month, day=1)
            taken = self.search([
                ('id', '!=', leave._origin.id or 0),
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('state', '=', 'validate'),
                ('request_date_from', '>=', month_start),
                ('request_date_from', '<', month_end),
            ])
            leave.tarco_taken_month = sum(taken.mapped('number_of_days'))
            kind = leave.holiday_status_id.tarco_kind
            year_start = leave.request_date_from.replace(month=1, day=1)
            year_end = leave.request_date_from.replace(month=12, day=31)
            year_taken = self.search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('state', '=', 'validate'),
                ('request_date_from', '>=', year_start),
                ('request_date_from', '<=', year_end),
            ])
            entitlement = 0.0
            if kind == 'casual':
                entitlement = leave.employee_id.tarco_casual_days
            elif kind == 'annual':
                entitlement = leave.employee_id.tarco_regular_days
            leave.tarco_remaining_days = entitlement - sum(year_taken.mapped('number_of_days'))

    def _action_validate(self, check_state=True):
        result = super()._action_validate(check_state=check_state)
        for leave in self:
            leave._tarco_post_leave_deduction()
        return result

    def _tarco_post_leave_deduction(self):
        self.ensure_one()
        if self.tarco_salary_attachment_id or self.tarco_deduction_mode == 'balance':
            return
        percent = 100.0 if self.tarco_deduction_mode == 'salary' else (self.tarco_deduction_percent or 0.0)
        if percent <= 0 or not self.employee_id:
            return
        amount = (self.number_of_days or 0.0) * tarco_daily_wage(self.employee_id) * percent / 100.0
        if amount <= 0:
            return
        attachment = tarco_post_adjustment(
            self.env, self.employee_id, False, amount,
            _('Leave deduction %s') % (self.employee_id.display_name),
            self.request_date_from,
        )
        if attachment:
            self.tarco_salary_attachment_id = attachment.id


class TarcoHrLeaveEncashment(models.Model):
    _name = 'tarco.hr.leave.encashment'
    _description = 'Leave Encashment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    encash_date = fields.Date(default=fields.Date.context_today, required=True)
    days = fields.Float(required=True, default=1.0)
    daily_rate = fields.Monetary(compute='_compute_amount', store=True, readonly=False)
    amount = fields.Monetary(compute='_compute_amount', store=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=True)
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)

    @api.depends('employee_id', 'days', 'daily_rate')
    def _compute_amount(self):
        for record in self:
            rate = record.daily_rate
            if not rate and record.employee_id:
                rate = tarco_daily_wage(record.employee_id)
                record.daily_rate = rate
            record.amount = (record.days or 0.0) * (rate or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.leave.encashment') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if not record.salary_attachment_id and record.amount > 0:
                attachment = tarco_post_adjustment(
                    self.env, record.employee_id, True, record.amount,
                    _('Leave encashment %s') % record.employee_id.display_name,
                    record.encash_date,
                )
                record.salary_attachment_id = attachment
            record.state = 'confirmed'
