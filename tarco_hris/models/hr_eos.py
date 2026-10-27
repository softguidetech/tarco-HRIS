# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .tarco_common import tarco_eos_gratuity, tarco_gross, tarco_post_adjustment


class TarcoHrEos(models.Model):
    _name = 'tarco.hr.eos'
    _description = 'End of Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'last_working_day desc, id desc'

    name = fields.Char(default='/', copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, index=True)
    employee_code = fields.Char(related='employee_id.employee_code', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    job_id = fields.Many2one(related='employee_id.job_id')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    hire_date = fields.Date(related='employee_id.tarco_hire_date')
    last_working_day = fields.Date(
        required=True, tracking=True, default=fields.Date.context_today,
        string='Last working day',
    )
    exit_kind = fields.Selection([
        ('resign', 'Resignation'),
        ('fired', 'Dismissal / Fired'),
        ('contract_end', 'Contract end'),
        ('retirement', 'Retirement'),
    ], required=True, default='resign', tracking=True)
    misconduct = fields.Boolean(
        string='Dismissed for misconduct',
        help='Labour Act 1997: no gratuity when service is ended for misconduct. Calculated amount becomes 0.',
    )
    amount_mode = fields.Selection([
        ('calculate', 'Calculate'),
        ('fixed', 'Fixed amount'),
    ], required=True, default='calculate', tracking=True, string='Amount')
    wage_base = fields.Monetary(
        string='Wage used',
        compute='_compute_wage_base',
        store=True,
        readonly=False,
        tracking=True,
        help='Last gross salary. Change it if finance should calculate on another figure.',
    )
    service_years = fields.Integer(compute='_compute_service', store=True)
    service_months = fields.Integer(compute='_compute_service', store=True)
    service_days = fields.Integer(compute='_compute_service', store=True)
    service_display = fields.Char(string='Length of service', compute='_compute_service', store=True)
    years_float = fields.Float(compute='_compute_service', store=True, digits=(16, 4))
    first_band_years = fields.Float(
        string='Years (first 5)', compute='_compute_amounts', store=True, compute_sudo=True, digits=(16, 4),
    )
    extra_years = fields.Float(
        string='Years after 5', compute='_compute_amounts', store=True, compute_sudo=True, digits=(16, 4),
    )
    first_band_amount = fields.Monetary(
        string='First 5 years (0.5 month each)', compute='_compute_amounts', store=True, compute_sudo=True,
    )
    extra_amount = fields.Monetary(
        string='After 5 years (1 month each)', compute='_compute_amounts', store=True, compute_sudo=True,
    )
    calculated_amount = fields.Monetary(
        string='Calculated amount', compute='_compute_amounts', store=True, compute_sudo=True,
    )
    formula_note = fields.Char(compute='_compute_amounts', store=True, compute_sudo=True)
    fixed_amount = fields.Monetary(string='Fixed amount for finance', tracking=True)
    amount = fields.Monetary(
        string='Amount to pay',
        compute='_compute_amount',
        store=True,
        tracking=True,
        help='What finance will pay. Calculated from the Labour Act, or the fixed amount you type.',
    )
    record_exit = fields.Boolean(
        string='Register exit and return custody',
        default=True,
        help='Set the last working day on the employee and return issued custody.',
    )
    custody_outstanding_count = fields.Integer(compute='_compute_custody')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_pay', 'Sent to finance'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)

    @api.depends('employee_id', 'employee_id.tarco_gross_wage', 'employee_id.tarco_basic_wage')
    def _compute_wage_base(self):
        for rec in self:
            rec.wage_base = tarco_gross(rec.employee_id)

    @api.depends('employee_id', 'employee_id.tarco_hire_date', 'employee_id.tarco_rehire_date', 'last_working_day')
    def _compute_service(self):
        for rec in self:
            start = rec.employee_id.tarco_rehire_date or rec.employee_id.tarco_hire_date
            end = rec.last_working_day or fields.Date.context_today(rec)
            if not start or end < start:
                rec.service_years = rec.service_months = rec.service_days = 0
                rec.years_float = 0.0
                rec.service_display = False
                continue
            delta = relativedelta(end, start)
            rec.service_years = delta.years
            rec.service_months = delta.months
            rec.service_days = delta.days
            rec.years_float = delta.years + delta.months / 12.0 + delta.days / 365.0
            rec.service_display = _('%s years, %s months, %s days') % (
                delta.years, delta.months, delta.days,
            )

    @api.depends('wage_base', 'years_float', 'misconduct')
    def _compute_amounts(self):
        for rec in self:
            years = rec.years_float or 0.0
            first = min(years, 5.0)
            extra = max(years - 5.0, 0.0)
            rec.first_band_years = first
            rec.extra_years = extra
            rec.first_band_amount = (rec.wage_base or 0.0) * first * 0.5
            rec.extra_amount = (rec.wage_base or 0.0) * extra
            if rec.misconduct:
                rec.calculated_amount = 0.0
                rec.formula_note = _('No gratuity: dismissed for misconduct.')
            else:
                rec.calculated_amount = tarco_eos_gratuity(rec.wage_base, years)
                rec.formula_note = _(
                    'Labour Act 1997: 0.5 × wage × first 5 years + 1 × wage × years after 5.'
                )

    @api.depends('amount_mode', 'calculated_amount', 'fixed_amount')
    def _compute_amount(self):
        for rec in self:
            if rec.amount_mode == 'fixed':
                rec.amount = rec.fixed_amount or 0.0
            else:
                rec.amount = rec.calculated_amount or 0.0

    @api.depends('employee_id')
    def _compute_custody(self):
        for rec in self:
            rec.custody_outstanding_count = len(
                rec.employee_id.tarco_asset_ids.filtered(lambda asset: asset.state == 'issued')
            )

    @api.constrains('fixed_amount', 'amount_mode')
    def _check_fixed_amount(self):
        for rec in self:
            if rec.amount_mode == 'fixed' and (rec.fixed_amount or 0.0) < 0:
                raise ValidationError(_('The fixed amount cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.eos') or '/'
        return super().create(vals_list)

    def action_send_to_finance(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('%s is not a draft end of service.') % rec.name)
            if rec.record_exit:
                rec._apply_exit()
            attachment = self.env['hr.salary.attachment']
            if rec.amount > 0:
                attachment = tarco_post_adjustment(
                    self.env, rec.employee_id, True, rec.amount,
                    _('End of service %s') % rec.name, rec.last_working_day,
                )
            rec.write({
                'salary_attachment_id': attachment.id if attachment else False,
                'state': 'to_pay',
            })
            rec.message_post(body=_(
                'Sent to finance. Amount to pay: %s. It appears on the next payslip as a Tarco Earning '
                '(or pay outside payroll and click Mark paid).'
            ) % rec.amount)
        return True

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'to_pay':
                raise UserError(_('%s has not been sent to finance yet.') % rec.name)
            rec.state = 'paid'
            if rec.salary_attachment_id and rec.salary_attachment_id.state == 'open':
                rec.salary_attachment_id.write({
                    'state': 'close',
                    'paid_amount': rec.amount,
                    'date_end': rec.last_working_day,
                })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_('A paid end of service cannot be cancelled.'))
            if rec.salary_attachment_id and rec.salary_attachment_id.state == 'open':
                rec.salary_attachment_id.write({
                    'state': 'close',
                    'date_end': fields.Date.context_today(rec),
                    'paid_amount': 0.0,
                })
            rec.state = 'cancel'

    def action_draft(self):
        self.filtered(lambda rec: rec.state == 'cancel').write({'state': 'draft'})

    def _apply_exit(self):
        self.ensure_one()
        employee = self.employee_id
        reason_label = dict(self._fields['exit_kind'].selection).get(self.exit_kind)
        issued = employee.tarco_asset_ids.filtered(lambda rec: rec.state == 'issued')
        issued.action_release_on_exit(self.last_working_day, reason_label)
        employee.tarco_requirement_ids.filtered(lambda rec: rec.state == 'todo').action_cancel()
        vals = {
            'tarco_resignation_date': self.last_working_day,
            'departure_date': self.last_working_day,
        }
        reason = self._departure_reason()
        if reason:
            vals['departure_reason_id'] = reason.id
        employee.with_context(tarco_skip_custody_release=True).write(vals)
        employee.message_post(body=_(
            'End of service %s (%s). Payable: %s. Issued custody returned.'
        ) % (self.name, reason_label, self.amount))

    def _departure_reason(self):
        Reason = self.env['hr.departure.reason']
        if self.exit_kind == 'fired':
            return (
                Reason.search([('name', 'ilike', 'fired')], limit=1)
                or Reason.search([('name', 'ilike', 'dismiss')], limit=1)
                or Reason.search([('name', 'ilike', 'terminat')], limit=1)
            )
        if self.exit_kind == 'retirement':
            return Reason.search([('name', 'ilike', 'retir')], limit=1)
        if self.exit_kind == 'contract_end':
            return (
                Reason.search([('name', 'ilike', 'contract')], limit=1)
                or Reason.search([('name', 'ilike', 'end')], limit=1)
            )
        return Reason.search([('name', 'ilike', 'resign')], limit=1)

    def action_print(self):
        return self.env.ref('tarco_hris.action_report_eos').report_action(self)

    def action_open_salary_attachment(self):
        self.ensure_one()
        if not self.salary_attachment_id:
            raise UserError(_('No payroll line has been sent to finance yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Salary adjustment'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'form',
            'res_id': self.salary_attachment_id.id,
        }

    def _sync_paid_from_attachments(self):
        recs = self.search([('state', '=', 'to_pay'), ('salary_attachment_id', '!=', False)])
        for rec in recs:
            attachment = rec.salary_attachment_id
            paid = attachment.paid_amount or 0.0
            if attachment.state == 'close' or paid + 0.009 >= rec.amount:
                rec.state = 'paid'
