# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from .tarco_common import (
    QUALIFICATION_SELECTION,
    RELIGION_SELECTION,
    tarco_daily_wage,
    tarco_gross,
    tarco_hierarchy_read,
    tarco_post_adjustment,
)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    _employee_code_unique = models.Constraint(
        'unique(employee_code)',
        'The employee code is already used.',
    )

    employee_code = fields.Char(
        string='Employee Code',
        copy=False,
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
        help='Primary key used to search and link every HR record.',
    )
    section_id = fields.Many2one(
        'hr.department', string='Section', tracking=True, groups='hr.group_hr_user',
    )
    tarco_experience_years = fields.Float(string='Years of Experience', groups='hr.group_hr_user', tracking=True)
    tarco_religion = fields.Selection(RELIGION_SELECTION, string='Religion', groups='hr.group_hr_user', tracking=True)
    tarco_state_id = fields.Many2one('res.country.state', string='State', groups='hr.group_hr_user')
    tarco_city = fields.Char(string='City', groups='hr.group_hr_user')
    tarco_district = fields.Char(string='District', groups='hr.group_hr_user')
    tarco_square = fields.Char(string='Block', groups='hr.group_hr_user')

    tarco_hire_date = fields.Date(string='Hire Date', tracking=True, groups='hr.group_hr_user')
    tarco_trial_manual = fields.Boolean(string='Probation Set Manually', groups='hr.group_hr_user')
    tarco_trial_date_end = fields.Date(string='Probation End', tracking=True, groups='hr.group_hr_user')
    tarco_payroll_trial_end = fields.Date(
        related='version_id.trial_date_end',
        string='Probation End (Payroll)',
        store=True,
        groups='hr.group_hr_user',
        help='End of trial period on the Payroll page. Probation ending uses this date only.',
    )
    tarco_renewal_manual = fields.Boolean(string='Renewal Set Manually', groups='hr.group_hr_user')
    tarco_renewal_date = fields.Date(string='Annual Renewal Date', tracking=True, groups='hr.group_hr_user')
    tarco_contract_date_end = fields.Date(
        related='version_id.contract_date_end',
        string='Contract End',
        store=True,
        groups='hr.group_hr_user',
        help='End date of the current contract on the Payroll page. Renewals due uses this date only.',
    )
    tarco_resignation_date = fields.Date(string='Resignation Date', tracking=True, copy=False, groups='hr.group_hr_user')
    tarco_rehire_date = fields.Date(string='Rehire Date', tracking=True, copy=False, groups='hr.group_hr_user')
    tarco_probation_alerted = fields.Boolean(copy=False, groups='hr.group_hr_user')
    tarco_renewal_alerted = fields.Boolean(copy=False, groups='hr.group_hr_user')
    tarco_due_kind = fields.Selection(
        [('probation', 'Probation ending'), ('renewal', 'Renewal due')],
        string='Contract Alert',
        compute='_compute_tarco_due_kind',
        search='_search_tarco_due_kind',
        groups='hr.group_hr_user',
    )
    tarco_service_display = fields.Char(string='Length of Service', compute='_compute_tarco_service', groups='hr.group_hr_user')
    tarco_service_years = fields.Integer(compute='_compute_tarco_service', groups='hr.group_hr_user')
    tarco_service_months = fields.Integer(compute='_compute_tarco_service', groups='hr.group_hr_user')
    tarco_service_days = fields.Integer(compute='_compute_tarco_service', groups='hr.group_hr_user')

    tarco_basic_wage = fields.Monetary(string='Basic Salary', tracking=True, groups='hr.group_hr_user')
    tarco_cola = fields.Monetary(string='Cost of Living Allowance', tracking=True, groups='hr.group_hr_user')
    tarco_transport_allowance = fields.Monetary(string='Transport Allowance', tracking=True, groups='hr.group_hr_user')
    tarco_housing_allowance = fields.Monetary(string='Housing Allowance (بدل السكن)', tracking=True, groups='hr.group_hr_user')
    tarco_other_allowance = fields.Monetary(string='Other Allowances (بدلات أخرى)', tracking=True, groups='hr.group_hr_user')
    tarco_gross_wage = fields.Monetary(
        string='Gross Salary', compute='_compute_tarco_gross_wage', store=True, groups='hr.group_hr_user',
    )
    tarco_subject_to_tax = fields.Boolean(string='Subject to Tax', groups='hr.group_hr_user')
    tarco_tax_rate = fields.Float(string='Tax %', groups='hr.group_hr_user')
    tarco_subject_to_insurance = fields.Boolean(string='Subject to Social Insurance', groups='hr.group_hr_user')
    tarco_insurance_rate = fields.Float(string='Social Insurance %', groups='hr.group_hr_user')
    tarco_auto_statutory = fields.Boolean(
        string='Adjust Taxes Automatically', tracking=True, groups='hr.group_hr_user',
        help='Post the tax and social insurance salary adjustments automatically at the start of every month. '
             'When unticked, an HR officer must click "Post tax and insurance" each month.')
    tarco_statutory_month = fields.Date(
        string='Taxes Posted For', copy=False, readonly=True, groups='hr.group_hr_user',
        help='First day of the last month for which tax and social insurance were posted.')

    tarco_leave_scheme = fields.Selection(
        [('21', '21 days (6 casual + 15 annual)'), ('30', '30 days (6 casual + 24 annual)')],
        string='Annual Leave Scheme',
        default='21',
        groups='hr.group_hr_user',
        tracking=True,
    )
    tarco_casual_days = fields.Float(
        string='Casual Days', compute='_compute_tarco_leave_split', store=True, readonly=False, groups='hr.group_hr_user',
    )
    tarco_regular_days = fields.Float(
        string='Annual Days', compute='_compute_tarco_leave_split', store=True, readonly=False, groups='hr.group_hr_user',
    )
    tarco_shift_id = fields.Many2one('tarco.hr.shift', string='Shift', groups='hr.group_hr_user')
    tarco_exempt_late = fields.Boolean(string='Exempt from Lateness', groups='hr.group_hr_user')
    tarco_overtime_mode = fields.Selection(
        [('time_half', 'Hour x 1.5 / 2'), ('none', 'Do not pay overtime')],
        string='Overtime Calculation',
        default='time_half',
        groups='hr.group_hr_user',
    )
    tarco_document_ids = fields.One2many('tarco.hr.document', 'employee_id', string='Documents', groups='hr.group_hr_user')
    tarco_encashment_ids = fields.One2many(
        'tarco.hr.leave.encashment', 'employee_id', string='Leave Encashment', groups='hr.group_hr_user',
    )
    tarco_document_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_mission_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_penalty_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_reward_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_advance_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_kpi_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_encashment_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_encashment_month_days = fields.Float(
        string='Encashment Days This Month',
        compute='_compute_tarco_encashment_month',
        groups='hr.group_hr_user',
    )
    tarco_encashment_month_amount = fields.Monetary(
        string='Encashment This Month',
        compute='_compute_tarco_encashment_month',
        groups='hr.group_hr_user',
        help='Confirmed leave encashment in the current month. This extra amount is posted to this month\'s payslip.',
    )
    tarco_requirement_ids = fields.One2many(
        'tarco.hr.requirement', 'employee_id', string='Work Requirements', groups='hr.group_hr_user',
    )
    tarco_asset_ids = fields.One2many(
        'tarco.hr.asset', 'employee_id', string='Custody', groups='hr.group_hr_user',
    )
    tarco_requirement_todo_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_asset_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_asset_outstanding_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')
    tarco_eos_count = fields.Integer(compute='_compute_tarco_counts', groups='hr.group_hr_user')

    @api.model
    def _get_certificate_selection(self):
        return QUALIFICATION_SELECTION

    @api.depends(
        'tarco_basic_wage', 'tarco_cola', 'tarco_transport_allowance',
        'tarco_housing_allowance', 'tarco_other_allowance',
    )
    def _compute_tarco_gross_wage(self):
        for employee in self:
            employee.tarco_gross_wage = (
                (employee.tarco_basic_wage or 0.0)
                + (employee.tarco_cola or 0.0)
                + (employee.tarco_transport_allowance or 0.0)
                + (employee.tarco_housing_allowance or 0.0)
                + (employee.tarco_other_allowance or 0.0)
            )

    @api.depends('tarco_leave_scheme')
    def _compute_tarco_leave_split(self):
        for employee in self:
            if employee.tarco_leave_scheme == '30':
                employee.tarco_casual_days = 6
                employee.tarco_regular_days = 24
            else:
                employee.tarco_casual_days = 6
                employee.tarco_regular_days = 15

    @api.depends('tarco_hire_date', 'tarco_resignation_date', 'tarco_rehire_date')
    def _compute_tarco_service(self):
        today = fields.Date.context_today(self)
        for employee in self:
            start = employee.tarco_rehire_date or employee.tarco_hire_date
            end = employee.tarco_resignation_date or today
            if not start or end < start:
                employee.tarco_service_years = 0
                employee.tarco_service_months = 0
                employee.tarco_service_days = 0
                employee.tarco_service_display = False
                continue
            delta = relativedelta(end, start)
            employee.tarco_service_years = delta.years
            employee.tarco_service_months = delta.months
            employee.tarco_service_days = delta.days
            employee.tarco_service_display = _('%s years, %s months, %s days') % (
                delta.years, delta.months, delta.days,
            )

    @api.depends('tarco_payroll_trial_end', 'tarco_contract_date_end', 'tarco_resignation_date')
    def _compute_tarco_due_kind(self):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=10)
        for employee in self:
            kind = False
            if not employee.tarco_resignation_date:
                if employee.tarco_payroll_trial_end and today <= employee.tarco_payroll_trial_end <= limit:
                    kind = 'probation'
                elif employee.tarco_contract_date_end and today <= employee.tarco_contract_date_end <= limit:
                    kind = 'renewal'
            employee.tarco_due_kind = kind

    def _search_tarco_due_kind(self, operator, value):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=10)
        if value == 'probation':
            return [
                ('tarco_payroll_trial_end', '!=', False),
                ('tarco_payroll_trial_end', '>=', today),
                ('tarco_payroll_trial_end', '<=', limit),
                ('tarco_resignation_date', '=', False),
            ]
        if value == 'renewal':
            return [
                ('tarco_contract_date_end', '!=', False),
                ('tarco_contract_date_end', '>=', today),
                ('tarco_contract_date_end', '<=', limit),
                ('tarco_resignation_date', '=', False),
            ]
        return [('id', '=', 0)] if operator == '=' else []

    def _compute_tarco_counts(self):
        for employee in self:
            employee.tarco_document_count = len(employee.tarco_document_ids)
            employee.tarco_mission_count = self.env['tarco.hr.mission.line'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_penalty_count = self.env['tarco.hr.penalty.line'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_reward_count = self.env['tarco.hr.reward'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_advance_count = self.env['tarco.hr.advance'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_kpi_count = self.env['tarco.hr.kpi.review'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_encashment_count = self.env['tarco.hr.leave.encashment'].search_count([
                ('employee_id', '=', employee.id),
            ])
            employee.tarco_requirement_todo_count = self.env['tarco.hr.requirement'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'todo'),
            ])
            assets = self.env['tarco.hr.asset'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'cancel'),
            ])
            employee.tarco_asset_count = len(assets)
            employee.tarco_asset_outstanding_count = len(assets.filtered(lambda rec: rec.state == 'issued'))
            employee.tarco_eos_count = self.env['tarco.hr.eos'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'cancel'),
            ])

    def _compute_tarco_encashment_month(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        Encash = self.env['tarco.hr.leave.encashment']
        for employee in self:
            records = Encash.search([
                ('employee_id', '=', employee.id),
                ('encash_date', '>=', month_start),
                ('encash_date', '<=', month_end),
                ('state', '=', 'confirmed'),
            ])
            employee.tarco_encashment_month_days = sum(records.mapped('days'))
            employee.tarco_encashment_month_amount = sum(records.mapped('amount'))

    def _compute_display_name(self):
        super()._compute_display_name()
        if not (self.env.su or self.env.user.has_group('hr.group_hr_user')):
            return
        for employee in self:
            code = employee.employee_code
            label = employee.display_name or employee.name or ''
            if code and not str(label).startswith('[%s]' % code):
                employee.display_name = '[%s] %s' % (code, label)

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        result = super().name_search(name=name, domain=domain, operator=operator, limit=limit)
        if not name or not (self.env.su or self.env.user.has_group('hr.group_hr_user')):
            return result
        found = {row[0] for row in result}
        remaining = None if not limit else max(limit - len(result), 0)
        if remaining == 0:
            return result
        code_domain = Domain('employee_code', operator, name) & Domain(domain or Domain.TRUE)
        extras = self.search(code_domain, limit=remaining).filtered(lambda employee: employee.id not in found)
        return result + [(employee.id, employee.display_name) for employee in extras]

    @api.model
    def _tarco_prepare_vals(self, vals):
        if vals.get('employee_code') == '':
            vals['employee_code'] = False
        hire = vals.get('tarco_hire_date')
        if hire:
            hire_date = fields.Date.to_date(hire)
            if hire_date and not vals.get('tarco_trial_manual') and not vals.get('tarco_trial_date_end'):
                vals['tarco_trial_date_end'] = hire_date + timedelta(days=89)
            if hire_date and not vals.get('tarco_renewal_manual') and not vals.get('tarco_renewal_date'):
                vals['tarco_renewal_date'] = hire_date + relativedelta(years=1)
        return vals

    @api.model
    def _tarco_next_code(self, join_date, reserved):
        prefix = fields.Date.to_date(join_date).strftime('%Y%m')
        self.env['hr.employee'].flush_model(['employee_code'])
        self.env.cr.execute(
            "SELECT employee_code FROM hr_employee WHERE employee_code LIKE %s", [prefix + '%'])
        used = {row[0] for row in self.env.cr.fetchall()} | reserved
        serials = [int(code[len(prefix):]) for code in used
                   if code.startswith(prefix) and code[len(prefix):].isdigit()]
        code = '%s%03d' % (prefix, max(serials, default=0) + 1)
        reserved.add(code)
        return code

    def _tarco_join_date(self):
        self.ensure_one()
        return (self.tarco_hire_date or self.version_id.contract_date_start
                or (self.create_date and self.create_date.date()) or fields.Date.context_today(self))

    def action_tarco_generate_code(self):
        employees = self.sudo().sorted(lambda employee: (employee._tarco_join_date(), employee.id))
        reserved, changed = set(), 0
        for employee in employees:
            prefix = employee._tarco_join_date().strftime('%Y%m')
            code = employee.employee_code or ''
            if code.startswith(prefix) and code[len(prefix):].isdigit():
                continue
            employee.employee_code = self._tarco_next_code(employee._tarco_join_date(), reserved)
            changed += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if changed else 'info',
                'message': _('%(changed)s employee code(s) generated, %(kept)s already matched the joining month.',
                             changed=changed, kept=len(employees) - changed),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        reserved = set()
        for vals in vals_list:
            self._tarco_prepare_vals(vals)
            if not vals.get('employee_code'):
                join_date = vals.get('tarco_hire_date') or fields.Date.context_today(self)
                vals['employee_code'] = self._tarco_next_code(join_date, reserved)
        records = super().create(vals_list)
        records._tarco_code_to_badge()
        records._tarco_push_contract()
        return records

    def write(self, vals):
        vals = dict(vals)
        if vals.get('employee_code') == '':
            vals['employee_code'] = False
        if 'tarco_trial_date_end' in vals and 'tarco_probation_alerted' not in vals:
            vals['tarco_probation_alerted'] = False
        if 'tarco_renewal_date' in vals and 'tarco_renewal_alerted' not in vals:
            vals['tarco_renewal_alerted'] = False
        if vals.get('tarco_hire_date') and not vals.get('tarco_trial_manual'):
            hire_date = fields.Date.to_date(vals['tarco_hire_date'])
            if 'tarco_trial_date_end' not in vals:
                vals['tarco_trial_date_end'] = hire_date + timedelta(days=89)
            if 'tarco_renewal_date' not in vals and not vals.get('tarco_renewal_manual'):
                vals['tarco_renewal_date'] = hire_date + relativedelta(years=1)
        res = super().write(vals)
        component_keys = {
            'tarco_basic_wage', 'tarco_cola', 'tarco_transport_allowance',
            'tarco_housing_allowance', 'tarco_other_allowance',
            'tarco_hire_date', 'tarco_trial_date_end',
        }
        if component_keys.intersection(vals):
            self._tarco_push_contract()
        if vals.get('employee_code'):
            self._tarco_code_to_badge()
        return res

    def _tarco_code_to_badge(self):
        for employee in self:
            code = employee.employee_code
            if code and not employee.barcode and code.isascii() and code.isalnum() and len(code) <= 18:
                employee.sudo().write({'barcode': code})

    def _tarco_push_contract(self):
        for employee in self:
            version = employee.version_id
            if not version:
                continue
            version_vals = {}
            if employee.tarco_hire_date and version.contract_date_start != employee.tarco_hire_date:
                version_vals['contract_date_start'] = employee.tarco_hire_date
            if employee.tarco_trial_date_end and version.trial_date_end != employee.tarco_trial_date_end:
                version_vals['trial_date_end'] = employee.tarco_trial_date_end
            gross = tarco_gross(employee)
            if employee.tarco_gross_wage and version.wage != gross:
                version_vals['wage'] = gross
            if version_vals:
                version.sudo().write(version_vals)

    @api.onchange('tarco_hire_date')
    def _onchange_tarco_hire_date(self):
        if self.tarco_hire_date and not self.tarco_trial_manual:
            self.tarco_trial_date_end = self.tarco_hire_date + timedelta(days=89)
        if self.tarco_hire_date and not self.tarco_renewal_manual:
            self.tarco_renewal_date = self.tarco_hire_date + relativedelta(years=1)

    @api.onchange('tarco_trial_date_end')
    def _onchange_tarco_trial(self):
        if self.tarco_hire_date and self.tarco_trial_date_end:
            expected = self.tarco_hire_date + timedelta(days=89)
            self.tarco_trial_manual = self.tarco_trial_date_end != expected

    @api.constrains('employee_code')
    def _check_employee_code(self):
        for employee in self:
            if not employee.employee_code:
                continue
            duplicate = self.sudo().search([
                ('employee_code', '=', employee.employee_code),
                ('id', '!=', employee.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_('Employee code %s is already used.') % employee.employee_code)

    def action_tarco_give_custody(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Give custody'),
            'res_model': 'tarco.hr.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

    def _tarco_open_exit(self, kind):
        self.ensure_one()
        title = _('Register dismissal') if kind == 'fired' else _('Register resignation')
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'tarco.hr.exit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_exit_kind': kind,
                'active_id': self.id,
                'active_model': 'hr.employee',
            },
        }

    def action_tarco_resign(self):
        return self._tarco_open_exit('resign')

    def action_tarco_fire(self):
        return self._tarco_open_exit('fired')

    def action_tarco_eos(self):
        self.ensure_one()
        existing = self.env['tarco.hr.eos'].search([
            ('employee_id', '=', self.id),
            ('state', 'in', ('draft', 'to_pay')),
        ], limit=1)
        action = {
            'type': 'ir.actions.act_window',
            'name': _('End of service'),
            'res_model': 'tarco.hr.eos',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_employee_id': self.id,
                'default_exit_kind': 'resign',
            },
        }
        if existing:
            action['res_id'] = existing.id
        return action

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('tarco_skip_custody_release'):
            return res
        exit_date = vals.get('tarco_resignation_date') or vals.get('departure_date')
        if exit_date:
            issued = self.mapped('tarco_asset_ids').filtered(lambda rec: rec.state == 'issued')
            issued.action_release_on_exit(exit_date, _('resignation / dismissal'))
        return res

    def action_tarco_rehire(self):
        today = fields.Date.context_today(self)
        self.write({
            'active': True,
            'tarco_rehire_date': today,
            'tarco_resignation_date': False,
            'departure_date': False,
            'departure_reason_id': False,
            'tarco_trial_manual': False,
            'tarco_renewal_manual': False,
            'tarco_trial_date_end': today + timedelta(days=89),
            'tarco_renewal_date': today + relativedelta(years=1),
            'tarco_probation_alerted': False,
            'tarco_renewal_alerted': False,
        })

    def action_tarco_renew(self):
        for employee in self:
            base = employee.tarco_renewal_date or fields.Date.context_today(self)
            employee.write({
                'tarco_renewal_date': base + relativedelta(years=1),
                'tarco_renewal_manual': True,
                'tarco_renewal_alerted': False,
            })

    def action_tarco_apply_leave_scheme(self):
        annual = self.env.ref('tarco_hris.leave_type_annual', raise_if_not_found=False)
        casual = self.env.ref('tarco_hris.leave_type_casual', raise_if_not_found=False)
        if not annual or not casual:
            raise UserError(_('Tarco leave types are missing. Update the module.'))
        if not self:
            raise UserError(_('Select at least one employee.'))
        year = fields.Date.context_today(self).year
        start = fields.Date.from_string('%s-01-01' % year)
        end = fields.Date.from_string('%s-12-31' % year)
        created = already = skipped = 0
        for employee in self:
            if employee.tarco_resignation_date:
                skipped += 1
                continue
            new_count = 0
            kept_count = 0
            for leave_type, days in (
                (casual, employee.tarco_casual_days),
                (annual, employee.tarco_regular_days),
            ):
                allocation, was_new = self._tarco_allocate(employee, leave_type, days, start, end)
                if was_new:
                    new_count += 1
                elif allocation:
                    kept_count += 1
            if new_count:
                created += 1
            elif kept_count:
                already += 1
            else:
                skipped += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if created else 'info',
                'message': _(
                    'Leave scheme applied for %(year)s: %(created)s employee(s) received allocations, '
                    '%(already)s already had this year, %(skipped)s skipped (resigned or no days).',
                    year=year, created=created, already=already, skipped=skipped,
                ),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def _tarco_allocate(self, employee, leave_type, days, start, end):
        empty = self.env['hr.leave.allocation']
        if not days:
            return empty, False
        existing = empty.sudo().search([
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', leave_type.id),
            ('state', '!=', 'refuse'),
            ('date_from', '>=', start),
            ('date_from', '<=', end),
        ], limit=1)
        if existing:
            return existing, False
        allocation = empty.sudo().create({
            'name': '%s %s' % (leave_type.name, start.year),
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': days,
            'date_from': start,
            'date_to': end,
            'allocation_type': 'regular',
        })
        allocation._action_validate()
        return allocation, True

    def _tarco_post_statutory_month(self, month_start):
        """Post this month's tax and insurance once. Returns the employees that were posted."""
        posted = self.browse()
        for employee in self.sudo():
            if employee.tarco_statutory_month and employee.tarco_statutory_month >= month_start:
                continue
            gross = tarco_gross(employee)
            month_label = month_start.strftime('%m/%Y')
            created = self.env['hr.salary.attachment']
            if employee.tarco_subject_to_tax and employee.tarco_tax_rate and gross:
                created |= tarco_post_adjustment(
                    self.env, employee, False, gross * employee.tarco_tax_rate / 100.0,
                    _('Income tax %(month)s %(employee)s', month=month_label, employee=employee.display_name),
                    month_start,
                )
            if employee.tarco_subject_to_insurance and employee.tarco_insurance_rate and gross:
                created |= tarco_post_adjustment(
                    self.env, employee, False, gross * employee.tarco_insurance_rate / 100.0,
                    _('Social insurance %(month)s %(employee)s', month=month_label, employee=employee.display_name),
                    month_start,
                )
            if created:
                employee.tarco_statutory_month = month_start
                posted |= employee
        return posted

    def action_tarco_post_statutory(self):
        month_start = fields.Date.context_today(self).replace(day=1)
        posted = self._tarco_post_statutory_month(month_start)
        skipped = len(self) - len(posted)
        if posted:
            message = _('Tax and insurance posted for %(count)s employee(s) for %(month)s.',
                        count=len(posted), month=month_start.strftime('%m/%Y'))
            if skipped:
                message += ' ' + _('%s skipped: already posted this month or nothing to deduct.') % skipped
        else:
            message = _('Nothing posted: already posted for %s, or no tax or insurance rate and salary set.') \
                % month_start.strftime('%m/%Y')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if posted else 'warning',
                'message': message,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    @api.model
    def _cron_tarco_auto_statutory(self):
        month_start = fields.Date.context_today(self).replace(day=1)
        employees = self.sudo().search([
            ('tarco_auto_statutory', '=', True),
            '|', ('tarco_subject_to_tax', '=', True), ('tarco_subject_to_insurance', '=', True),
            '|', ('tarco_statutory_month', '=', False), ('tarco_statutory_month', '<', month_start),
            '|', ('tarco_resignation_date', '=', False), ('tarco_resignation_date', '>=', month_start),
        ])
        return employees._tarco_post_statutory_month(month_start)

    def action_tarco_onboarding(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Onboarding Notice'),
            'res_model': 'tarco.hr.onboarding',
            'view_mode': 'form',
            'context': {'default_employee_id': self.id},
        }

    def action_tarco_open_documents(self):
        return self._tarco_open('tarco.hr.document', [('employee_id', 'in', self.ids)])

    def action_tarco_open_missions(self):
        lines = self.env['tarco.hr.mission.line'].search([('employee_id', 'in', self.ids)])
        return self._tarco_open('tarco.hr.mission', [('id', 'in', lines.mission_id.ids)])

    def action_tarco_open_penalties(self):
        lines = self.env['tarco.hr.penalty.line'].search([('employee_id', 'in', self.ids)])
        return self._tarco_open('tarco.hr.penalty', [('id', 'in', lines.penalty_id.ids)])

    def action_tarco_open_rewards(self):
        return self._tarco_open('tarco.hr.reward', [('employee_id', 'in', self.ids)])

    def action_tarco_open_advances(self):
        return self._tarco_open('tarco.hr.advance', [('employee_id', 'in', self.ids)])

    def action_tarco_open_kpi(self):
        return self._tarco_open('tarco.hr.kpi.review', [('employee_id', 'in', self.ids)])

    def action_tarco_open_encashment(self):
        return self._tarco_open('tarco.hr.leave.encashment', [('employee_id', 'in', self.ids)])

    def action_tarco_open_requirements(self):
        return self._tarco_open('tarco.hr.requirement', [('employee_id', 'in', self.ids)])

    def action_tarco_open_assets(self):
        return self._tarco_open('tarco.hr.asset', [('employee_id', 'in', self.ids)])

    def action_tarco_open_eos(self):
        return self._tarco_open('tarco.hr.eos', [('employee_id', 'in', self.ids)])

    def _tarco_open(self, model, domain):
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name if len(self) == 1 else _('Employees'),
            'res_model': model,
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_employee_id': self.id if len(self) == 1 else False},
        }

    def action_tarco_employee_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee File Report'),
            'res_model': 'tarco.hr.employee.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

    @api.model
    def _cron_tarco_contract_alerts(self):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=10)
        employees = self.sudo().search([
            ('active', '=', True),
            ('tarco_resignation_date', '=', False),
            '|',
            '&', ('tarco_payroll_trial_end', '>=', today), ('tarco_payroll_trial_end', '<=', limit),
            '&', ('tarco_contract_date_end', '>=', today), ('tarco_contract_date_end', '<=', limit),
        ])
        for employee in employees:
            employee._tarco_alert_date(
                employee.tarco_payroll_trial_end,
                'tarco_probation_alerted',
                _('Probation ends on %s') % employee.tarco_payroll_trial_end,
            )
            employee._tarco_alert_date(
                employee.tarco_contract_date_end,
                'tarco_renewal_alerted',
                _('Contract expires on %s') % employee.tarco_contract_date_end,
            )

    def _tarco_alert_date(self, due, flag, summary):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if not due or getattr(self, flag) or not (today <= due <= today + timedelta(days=10)):
            return
        user = self.version_id.hr_responsible_id or self.parent_id.user_id or self.env.ref('base.user_admin')
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=due,
            summary=summary,
            note=_('Alert raised within 10 days of the date for %s.') % self.display_name,
            user_id=user.id,
        )
        emails = {
            address for address in (self.work_email, self.parent_id.work_email, user.email) if address
        }
        if emails:
            self.env['mail.mail'].sudo().create({
                'subject': summary,
                'email_to': ','.join(emails),
                'body_html': '<p>%s</p><p>%s</p>' % (summary, self.display_name),
            }).send()
        self.sudo().write({flag: True})

    def tarco_daily_wage(self):
        self.ensure_one()
        return tarco_daily_wage(self)

    @api.model
    def hierarchy_read(self, domain, specification, parent_field, child_field=None, order=None):
        return tarco_hierarchy_read(self, domain, specification, parent_field, order)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    @api.model
    def hierarchy_read(self, domain, specification, parent_field, child_field=None, order=None):
        return tarco_hierarchy_read(self, domain, specification, parent_field, order)
