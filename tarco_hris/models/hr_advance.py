# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .tarco_common import tarco_gross, tarco_post_adjustment


class TarcoHrAdvance(models.Model):
    _name = 'tarco.hr.advance'
    _description = 'Salary Advance or Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    advance_type = fields.Selection([
        ('short', 'Short advance'),
        ('long', 'Long-term loan'),
        ('goods', 'Goods purchase'),
        ('other', 'Other deduction'),
    ], required=True, default='short', tracking=True)
    description = fields.Char(required=True)
    amount = fields.Monetary(required=True, tracking=True)
    installment_count = fields.Integer(default=1)
    monthly_amount = fields.Monetary(compute='_compute_monthly_amount', store=True, readonly=False)
    due_date = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('tarco.hr.advance.line', 'advance_id')
    paid_amount = fields.Monetary(compute='_compute_balances', store=True)
    remaining_amount = fields.Monetary(compute='_compute_balances', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)

    @api.depends('amount', 'installment_count', 'advance_type')
    def _compute_monthly_amount(self):
        for advance in self:
            count = advance.installment_count or 1
            if advance.advance_type == 'short':
                count = 1
            advance.monthly_amount = (advance.amount or 0.0) / count

    @api.depends('line_ids.amount', 'line_ids.state', 'amount')
    def _compute_balances(self):
        for advance in self:
            paid = sum(advance.line_ids.filtered(lambda line: line.state == 'paid').mapped('amount'))
            advance.paid_amount = paid
            advance.remaining_amount = (advance.amount or 0.0) - paid

    @api.constrains('monthly_amount', 'employee_id', 'amount')
    def _check_salary_cap(self):
        for advance in self:
            wage = tarco_gross(advance.employee_id)
            if wage and advance.monthly_amount and advance.monthly_amount - wage > 0.009:
                raise ValidationError(
                    _('The installment for %s cannot exceed the employee salary (%s).')
                    % (advance.employee_id.name, '%.2f' % wage)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.advance') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for advance in self:
            advance.line_ids.unlink()
            count = 1 if advance.advance_type == 'short' else max(advance.installment_count or 1, 1)
            monthly = advance.amount / count
            due = advance.due_date
            remaining = advance.amount
            lines = []
            for index in range(count):
                portion = monthly if index < count - 1 else remaining
                remaining -= portion
                lines.append((0, 0, {
                    'due_date': due,
                    'amount': portion,
                    'sequence': index + 1,
                }))
                due = due + relativedelta(months=1)
            duration = 'one' if count == 1 else 'limited'
            attachment = tarco_post_adjustment(
                self.env, advance.employee_id, False, monthly,
                advance.description, advance.due_date,
                duration_type=duration, total_amount=advance.amount,
            )
            advance.write({
                'line_ids': lines,
                'salary_attachment_id': attachment.id,
                'state': 'running',
                'installment_count': count,
            })

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def _cron_sync_paid(self):
        advances = self.search([('state', '=', 'running'), ('salary_attachment_id', '!=', False)])
        for advance in advances:
            paid = advance.salary_attachment_id.paid_amount or 0.0
            covered = paid
            for line in advance.line_ids.sorted('sequence'):
                if covered + 0.009 >= line.amount:
                    line.state = 'paid'
                    covered -= line.amount
                else:
                    line.state = 'due'
            if advance.remaining_amount <= 0.009:
                advance.state = 'done'
