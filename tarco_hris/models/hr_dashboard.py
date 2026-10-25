# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class TarcoHrDashboard(models.TransientModel):
    _name = 'tarco.hr.dashboard'
    _description = 'Tarco HRIS Dashboard'

    name = fields.Char(default='HRIS Dashboard')
    is_hr = fields.Boolean(compute='_compute_scope')
    employee_id = fields.Many2one('hr.employee', compute='_compute_scope')
    scope_label = fields.Char(compute='_compute_scope')
    month_label = fields.Char(compute='_compute_scope')
    currency_id = fields.Many2one('res.currency', compute='_compute_scope')

    employee_count = fields.Integer(compute='_compute_kpis')
    probation_count = fields.Integer(compute='_compute_kpis')
    renewal_count = fields.Integer(compute='_compute_kpis')
    applicant_count = fields.Integer(compute='_compute_kpis')
    holiday_draft_count = fields.Integer(compute='_compute_kpis')

    late_count = fields.Integer(compute='_compute_kpis')
    absent_count = fields.Integer(compute='_compute_kpis')
    leave_pending_count = fields.Integer(compute='_compute_kpis')
    leave_month_days = fields.Float(compute='_compute_kpis')
    mission_open_count = fields.Integer(compute='_compute_kpis')
    overtime_hours = fields.Float(compute='_compute_kpis')
    overtime_amount = fields.Monetary(compute='_compute_kpis')
    penalty_draft_count = fields.Integer(compute='_compute_kpis')
    penalty_month_count = fields.Integer(compute='_compute_kpis')
    penalty_amount = fields.Monetary(compute='_compute_kpis')
    reward_count = fields.Integer(compute='_compute_kpis')
    reward_amount = fields.Monetary(compute='_compute_kpis')
    advance_running_count = fields.Integer(compute='_compute_kpis')
    advance_balance = fields.Monetary(compute='_compute_kpis')
    encashment_count = fields.Integer(compute='_compute_kpis')
    encashment_amount = fields.Monetary(compute='_compute_kpis')
    kpi_count = fields.Integer(compute='_compute_kpis')

    late_day_ids = fields.Many2many('tarco.hr.attendance.day', compute='_compute_lists')
    leave_ids = fields.Many2many('hr.leave', compute='_compute_lists')
    mission_ids = fields.Many2many('tarco.hr.mission', compute='_compute_lists')
    penalty_ids = fields.Many2many('tarco.hr.penalty', compute='_compute_lists')
    reward_ids = fields.Many2many('tarco.hr.reward', compute='_compute_lists')
    advance_ids = fields.Many2many('tarco.hr.advance', compute='_compute_lists')
    kpi_ids = fields.Many2many('tarco.hr.kpi.review', compute='_compute_lists')

    def _is_hr(self):
        return self.env.user.has_group('hr.group_hr_user')

    def _employee_ids(self):
        if self._is_hr():
            return None
        return self.env.user.employee_id.ids

    def _month_bounds(self):
        today = fields.Date.context_today(self)
        start = today.replace(day=1)
        return start, start + relativedelta(months=1, days=-1)

    def _domain(self, field='employee_id'):
        domain = []
        ids = self._employee_ids()
        if ids is None:
            return domain
        if not ids:
            return [('id', '=', False)]
        return [(field, 'in', ids)]

    @api.depends_context('uid', 'company')
    def _compute_scope(self):
        today = fields.Date.context_today(self)
        months = [
            _('January'), _('February'), _('March'), _('April'), _('May'), _('June'),
            _('July'), _('August'), _('September'), _('October'), _('November'), _('December'),
        ]
        for dash in self:
            dash.is_hr = dash._is_hr()
            dash.employee_id = self.env.user.employee_id
            dash.currency_id = self.env.company.currency_id
            dash.month_label = '%s %s' % (months[today.month - 1], today.year)
            if dash.is_hr:
                dash.scope_label = _('Company overview — all Tarco HRIS records')
            elif dash.employee_id:
                dash.scope_label = _('My records only — %s') % dash.employee_id.display_name
            else:
                dash.scope_label = _('No employee is linked to this user')

    @api.depends_context('uid', 'company')
    def _compute_kpis(self):
        month_start, month_end = self._month_bounds()
        company = self.env.company
        for dash in self:
            emp_domain = dash._domain()
            line_domain = dash._domain('line_ids.employee_id')

            employees = self.env['hr.employee']
            if dash.is_hr:
                employees = self.env['hr.employee'].search([
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                    ('tarco_resignation_date', '=', False),
                ])
                dash.employee_count = len(employees)
                dash.probation_count = self.env['hr.employee'].search_count([
                    ('company_id', '=', company.id),
                    ('tarco_due_kind', '=', 'probation'),
                ])
                dash.renewal_count = self.env['hr.employee'].search_count([
                    ('company_id', '=', company.id),
                    ('tarco_due_kind', '=', 'renewal'),
                ])
                dash.applicant_count = self.env['hr.applicant'].search_count([
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                ])
                dash.holiday_draft_count = self.env['tarco.hr.public.holiday'].search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'draft'),
                ])
            else:
                dash.employee_count = 1 if dash.employee_id else 0
                dash.probation_count = dash.renewal_count = 0
                dash.applicant_count = dash.holiday_draft_count = 0

            days = self.env['tarco.hr.attendance.day'].search(
                emp_domain + [
                    ('work_date', '>=', month_start),
                    ('work_date', '<=', month_end),
                    ('company_id', '=', company.id),
                ]
            )
            dash.late_count = len(days.filtered(lambda day: day.late_minutes > 0 or day.status == 'late'))
            dash.absent_count = len(days.filtered(lambda day: day.status == 'absent'))

            leaves = self.env['hr.leave'].search(emp_domain + [
                ('state', 'in', ('confirm', 'validate1')),
            ])
            dash.leave_pending_count = len(leaves)
            approved = self.env['hr.leave'].search(emp_domain + [
                ('state', '=', 'validate'),
                ('request_date_from', '<=', month_end),
                ('request_date_to', '>=', month_start),
            ])
            dash.leave_month_days = sum(approved.mapped('number_of_days'))

            dash.mission_open_count = self.env['tarco.hr.mission'].search_count(
                line_domain + [('state', 'in', ('draft', 'approved'))]
            )

            ot_lines = self.env['tarco.hr.overtime.line'].search(
                emp_domain + [
                    ('overtime_id.date_from', '<=', month_end),
                    ('overtime_id.date_to', '>=', month_start),
                    ('overtime_id.state', '!=', 'cancel'),
                    ('company_id', '=', company.id),
                ]
            )
            dash.overtime_hours = sum(ot_lines.mapped('hours'))
            dash.overtime_amount = sum(ot_lines.mapped('amount'))

            penalties = self.env['tarco.hr.penalty'].search(
                line_domain + [('state', '!=', 'cancel'), ('company_id', '=', company.id)]
            )
            dash.penalty_draft_count = len(penalties.filtered(lambda rec: rec.state == 'draft'))
            month_penalties = penalties.filtered(
                lambda rec: rec.penalty_date and month_start <= rec.penalty_date <= month_end
            )
            dash.penalty_month_count = len(month_penalties)
            dash.penalty_amount = sum(month_penalties.mapped('total_amount'))

            rewards = self.env['tarco.hr.reward'].search(
                emp_domain + [
                    ('state', '!=', 'cancel'),
                    ('reward_date', '>=', month_start),
                    ('reward_date', '<=', month_end),
                    ('company_id', '=', company.id),
                ]
            )
            dash.reward_count = len(rewards)
            dash.reward_amount = sum(rewards.mapped('amount'))

            advances = self.env['tarco.hr.advance'].search(
                emp_domain + [('state', '=', 'running'), ('company_id', '=', company.id)]
            )
            dash.advance_running_count = len(advances)
            dash.advance_balance = sum(advances.mapped('remaining_amount'))

            encashments = self.env['tarco.hr.leave.encashment'].search(
                emp_domain + [
                    ('state', '=', 'confirmed'),
                    ('encash_date', '>=', month_start),
                    ('encash_date', '<=', month_end),
                    ('company_id', '=', company.id),
                ]
            )
            dash.encashment_count = len(encashments)
            dash.encashment_amount = sum(encashments.mapped('amount'))

            dash.kpi_count = self.env['tarco.hr.kpi.review'].search_count(
                emp_domain + [('company_id', '=', company.id)]
            )

    @api.depends_context('uid', 'company')
    def _compute_lists(self):
        month_start, month_end = self._month_bounds()
        company = self.env.company
        for dash in self:
            emp_domain = dash._domain()
            line_domain = dash._domain('line_ids.employee_id')
            days = self.env['tarco.hr.attendance.day'].search(
                emp_domain + [
                    ('work_date', '>=', month_start),
                    ('work_date', '<=', month_end),
                    ('company_id', '=', company.id),
                ],
                order='work_date desc',
                limit=80,
            )
            dash.late_day_ids = days.filtered(
                lambda day: day.late_minutes > 0 or day.status in ('late', 'absent')
            )[:20]
            dash.leave_ids = self.env['hr.leave'].search(
                emp_domain + [('state', 'in', ('confirm', 'validate1', 'validate'))],
                order='request_date_from desc',
                limit=20,
            )
            dash.mission_ids = self.env['tarco.hr.mission'].search(
                line_domain + [('state', '!=', 'cancel')],
                order='date_start desc',
                limit=20,
            )
            dash.penalty_ids = self.env['tarco.hr.penalty'].search(
                line_domain + [('state', '!=', 'cancel'), ('company_id', '=', company.id)],
                order='penalty_date desc',
                limit=20,
            )
            dash.reward_ids = self.env['tarco.hr.reward'].search(
                emp_domain + [('company_id', '=', company.id)],
                order='reward_date desc',
                limit=20,
            )
            dash.advance_ids = self.env['tarco.hr.advance'].search(
                emp_domain + [('company_id', '=', company.id)],
                order='id desc',
                limit=20,
            )
            dash.kpi_ids = self.env['tarco.hr.kpi.review'].search(
                emp_domain + [('company_id', '=', company.id)],
                order='date_to desc',
                limit=20,
            )

    @api.model
    def action_open(self):
        dash = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _('HRIS Dashboard'),
            'res_model': 'tarco.hr.dashboard',
            'res_id': dash.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_refresh(self):
        return self.action_open()

    def _open(self, model, name, domain, view_mode='list,form', context=None):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': view_mode,
            'domain': domain,
            'context': context or {},
        }

    def action_open_employees(self):
        domain = [('company_id', '=', self.env.company.id), ('active', '=', True)]
        ids = self._employee_ids()
        if ids is not None:
            domain.append(('id', 'in', ids or [0]))
        return self._open('hr.employee', _('Employees'), domain)

    def action_open_probation(self):
        return self._open('hr.employee', _('Probation ending'), [('tarco_due_kind', '=', 'probation')])

    def action_open_renewal(self):
        return self._open('hr.employee', _('Renewals due'), [('tarco_due_kind', '=', 'renewal')])

    def action_open_applicants(self):
        return self._open('hr.applicant', _('Applicants'), [('active', '=', True)], 'list,kanban,form')

    def action_open_holidays(self):
        return self._open('tarco.hr.public.holiday', _('Official holidays'), [('state', '=', 'draft')])

    def action_open_late(self):
        start, end = self._month_bounds()
        return self._open(
            'tarco.hr.attendance.day', _('Late this month'),
            self._domain() + [
                ('work_date', '>=', start), ('work_date', '<=', end),
                '|', ('late_minutes', '>', 0), ('status', '=', 'late'),
            ],
            'list',
        )

    def action_open_absent(self):
        start, end = self._month_bounds()
        return self._open(
            'tarco.hr.attendance.day', _('Absent this month'),
            self._domain() + [
                ('work_date', '>=', start), ('work_date', '<=', end), ('status', '=', 'absent'),
            ],
            'list',
        )

    def action_open_leave(self):
        return self._open(
            'hr.leave', _('Leave requests'),
            self._domain() + [('state', 'in', ('confirm', 'validate1', 'validate', 'draft'))],
        )

    def action_open_missions(self):
        return self._open(
            'tarco.hr.mission', _('Missions'),
            self._domain('line_ids.employee_id') + [('state', '!=', 'cancel')],
        )

    def action_open_overtime(self):
        return self._open(
            'tarco.hr.overtime', _('Overtime'),
            self._domain('line_ids.employee_id') + [('state', '!=', 'cancel')],
        )

    def action_open_penalties(self):
        return self._open(
            'tarco.hr.penalty', _('Penalties'),
            self._domain('line_ids.employee_id') + [('state', '!=', 'cancel')],
        )

    def action_open_rewards(self):
        return self._open(
            'tarco.hr.reward', _('Rewards'),
            self._domain() + [('state', '!=', 'cancel')],
        )

    def action_open_advances(self):
        return self._open(
            'tarco.hr.advance', _('Advances and loans'),
            self._domain() + [('state', '!=', 'cancel')],
        )

    def action_open_encashment(self):
        return self._open(
            'tarco.hr.leave.encashment', _('Leave encashment'),
            self._domain(),
        )

    def action_open_kpi(self):
        return self._open('tarco.hr.kpi.review', _('KPI reviews'), self._domain())
