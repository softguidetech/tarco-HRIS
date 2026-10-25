# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .tarco_common import tarco_post_adjustment


class TarcoHrOvertime(models.Model):
    _name = 'tarco.hr.overtime'
    _description = 'Overtime Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(default='/', copy=False)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department')
    line_ids = fields.One2many('tarco.hr.overtime.line', 'overtime_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_hours = fields.Float(compute='_compute_totals', store=True)
    total_amount = fields.Monetary(compute='_compute_totals', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.depends('line_ids.hours', 'line_ids.amount')
    def _compute_totals(self):
        for batch in self:
            batch.total_hours = sum(batch.line_ids.mapped('hours'))
            batch.total_amount = sum(batch.line_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.overtime') or '/'
        return super().create(vals_list)

    def action_fill(self):
        day_model = self.env['tarco.hr.attendance.day']
        for batch in self:
            employees = self.env['hr.employee'].search([
                ('company_id', '=', batch.company_id.id),
                ('department_id', '=', batch.department_id.id),
            ]) if batch.department_id else None
            day_model.sync_range(batch.date_from, batch.date_to, employees)
            domain = [
                ('work_date', '>=', batch.date_from),
                ('work_date', '<=', batch.date_to),
                ('company_id', '=', batch.company_id.id),
                ('overtime_hours', '>', 0),
                ('overtime_line_id', '=', False),
            ]
            if batch.department_id:
                domain.append(('department_id', '=', batch.department_id.id))
            grouped = {}
            for day in day_model.search(domain):
                bucket = grouped.setdefault(day.employee_id, self.env['tarco.hr.attendance.day'])
                grouped[day.employee_id] = bucket | day
            batch.line_ids.filtered(lambda line: not line.salary_attachment_id).unlink()
            for employee, days in grouped.items():
                hours_15 = sum(days.filtered(lambda day: day.overtime_rate == 1.5).mapped('overtime_hours'))
                hours_20 = sum(days.filtered(lambda day: day.overtime_rate == 2.0).mapped('overtime_hours'))
                line = self.env['tarco.hr.overtime.line'].create({
                    'overtime_id': batch.id,
                    'employee_id': employee.id,
                    'hours_15': hours_15,
                    'hours_20': hours_20,
                    'hours': hours_15 + hours_20,
                    'amount': sum(days.mapped('overtime_amount')),
                })
                days.write({'overtime_line_id': line.id})
        return True

    def action_confirm(self):
        for batch in self:
            for line in batch.line_ids:
                if line.salary_attachment_id or line.amount <= 0:
                    continue
                attachment = tarco_post_adjustment(
                    self.env, line.employee_id, True, line.amount,
                    _('Overtime %s') % batch.name, batch.date_to,
                )
                line.salary_attachment_id = attachment
            batch.state = 'confirmed'

    def action_cancel(self):
        for batch in self:
            batch.line_ids.overtime_day_ids.write({'overtime_line_id': False})
            batch.state = 'cancel'


class TarcoHrOvertimeLine(models.Model):
    _name = 'tarco.hr.overtime.line'
    _description = 'Overtime Line'

    overtime_id = fields.Many2one('tarco.hr.overtime', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='overtime_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    hours_15 = fields.Float(string='Hours x 1.5')
    hours_20 = fields.Float(string='Hours x 2')
    hours = fields.Float()
    amount = fields.Monetary()
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)
    overtime_day_ids = fields.One2many('tarco.hr.attendance.day', 'overtime_line_id')
