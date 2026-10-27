# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


PARAM_KEY = 'tarco_hris.demo_active'


class TarcoHrDemoWizard(models.TransientModel):
    _name = 'tarco.hr.demo.wizard'
    _description = 'Tarco HRIS Demo Data'

    demo_active = fields.Boolean(
        string='Activate demo data',
        help='When ticked, sample records are created in every Tarco HRIS screen. '
             'When unticked, only those sample records are removed. Your own data is kept.',
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        values['demo_active'] = self.env['ir.config_parameter'].sudo().get_param(PARAM_KEY) == 'True'
        return values

    def action_apply(self):
        self.ensure_one()
        if self.demo_active:
            if self.env['ir.config_parameter'].sudo().get_param(PARAM_KEY) == 'True':
                self._unload()
            self._load()
            message = _('Demo data is now active in every Tarco HRIS section.')
        else:
            self._unload()
            message = _('All Tarco HRIS demo data has been removed.')
        self.env['ir.config_parameter'].sudo().set_param(PARAM_KEY, str(self.demo_active))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _make(self, model, values):
        values = dict(values)
        if 'tarco_is_demo' in self.env[model]._fields:
            values['tarco_is_demo'] = True
        return self.env[model].sudo().with_context(
            mail_notrack=True, tracking_disable=True, mail_create_nolog=True,
            no_mail_to_attendees=True,
        ).create(values)

    def _demo(self, model):
        return self.env[model].sudo().with_context(active_test=False).search([('tarco_is_demo', '=', True)])

    def _safe(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception:
            return False

    def _unload(self):
        employees = self._demo('hr.employee')
        attachments = self.env['hr.salary.attachment'].sudo()
        for model, field_name in (
            ('tarco.hr.overtime.line', 'salary_attachment_id'),
            ('tarco.hr.penalty.line', 'salary_attachment_id'),
            ('tarco.hr.reward', 'salary_attachment_id'),
            ('tarco.hr.advance', 'salary_attachment_id'),
            ('tarco.hr.leave.encashment', 'salary_attachment_id'),
            ('hr.leave', 'tarco_salary_attachment_id'),
        ):
            if field_name in self.env[model]._fields:
                domain = [(field_name, '!=', False)]
                if 'tarco_is_demo' in self.env[model]._fields:
                    domain = ['|', ('tarco_is_demo', '=', True), ('employee_id', 'in', employees.ids)] if 'employee_id' in self.env[model]._fields else [('tarco_is_demo', '=', True)]
                    if model.endswith('.line'):
                        parent = 'overtime_id' if 'overtime' in model else 'penalty_id'
                        domain = ['|', (parent + '.tarco_is_demo', '=', True), ('employee_id', 'in', employees.ids)]
                attachments |= self.env[model].sudo().search(domain).mapped(field_name)
        attachments |= self._demo('hr.salary.attachment')
        if employees:
            attachments |= self.env['hr.salary.attachment'].sudo().search([('employee_ids', 'in', employees.ids)])

        for records, action in (
            (self._demo('tarco.hr.overtime').filtered(lambda rec: rec.state == 'confirmed'), 'action_cancel'),
            (self._demo('tarco.hr.penalty').filtered(lambda rec: rec.state == 'confirmed'), 'action_cancel'),
            (self._demo('tarco.hr.advance').filtered(lambda rec: rec.state == 'running'), 'action_cancel'),
            (self._demo('tarco.hr.mission').filtered(lambda rec: rec.state in ('approved', 'done')), 'action_cancel'),
        ):
            self._safe(getattr(records, action))

        leaves = self._demo('hr.leave')
        if employees:
            leaves |= self.env['hr.leave'].sudo().search([('employee_id', 'in', employees.ids)])
        for leave in leaves:
            if leave.state == 'validate' and hasattr(leave, 'action_refuse'):
                self._safe(leave.action_refuse)
            elif leave.state not in ('draft', 'cancel', 'refuse') and hasattr(leave, 'action_draft'):
                self._safe(leave.action_draft)

        allocations = self._demo('hr.leave.allocation')
        if employees:
            allocations |= self.env['hr.leave.allocation'].sudo().search([('employee_id', 'in', employees.ids)])
        for allocation in allocations:
            if allocation.state == 'validate' and hasattr(allocation, 'action_refuse'):
                self._safe(allocation.action_refuse)

        meetings = self._demo('calendar.event')
        if 'tarco_meeting_id' in self.env['hr.applicant']._fields:
            meetings |= self._demo('hr.applicant').mapped('tarco_meeting_id')

        holidays = self._demo('tarco.hr.public.holiday')
        calendar_leaves = holidays.mapped('calendar_leave_id') | self._demo('resource.calendar.leaves')

        if employees:
            self.env['tarco.hr.attendance.day'].sudo().search([('employee_id', 'in', employees.ids)]).unlink()
            self.env['hr.attendance'].sudo().search([('employee_id', 'in', employees.ids)]).unlink()
            self.env['tarco.hr.asset'].sudo().search([('employee_id', 'in', employees.ids)]).unlink()
            self.env['tarco.hr.requirement'].sudo().search([('employee_id', 'in', employees.ids)]).unlink()

        for model in (
            'tarco.hr.kpi.review', 'tarco.hr.kpi.template', 'tarco.hr.overtime', 'tarco.hr.penalty',
            'tarco.hr.reward', 'tarco.hr.advance', 'tarco.hr.leave.encashment', 'tarco.hr.mission',
            'tarco.hr.asset', 'tarco.hr.requirement',
            'tarco.hr.onboarding', 'tarco.hr.document', 'tarco.hr.public.holiday',
        ):
            self._demo(model).unlink()

        leaves.unlink()
        allocations.unlink()
        meetings.unlink()
        calendar_leaves.unlink()
        if attachments:
            attachments.sudo().write({'state': 'close'})
            attachments.sudo().unlink()
        self._demo('hr.applicant').unlink()
        self._demo('hr.job').write({'no_of_recruitment': 0})
        self._demo('hr.job').unlink()
        employees.unlink()
        self._demo('hr.department').unlink()

    def _load(self):
        company = self.env.company
        shift = self.env.ref('tarco_hris.shift_day_0800_1600', raise_if_not_found=False)
        late_rule = self.env.ref('tarco_hris.penalty_rule_late', raise_if_not_found=False)
        conduct = self.env.ref('tarco_hris.penalty_rule_conduct', raise_if_not_found=False)
        annual = self.env.ref('tarco_hris.leave_type_annual', raise_if_not_found=False)
        casual = self.env.ref('tarco_hris.leave_type_casual', raise_if_not_found=False)
        sick = self.env.ref('tarco_hris.leave_type_sick', raise_if_not_found=False)
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        today = fields.Date.context_today(self)

        root = self._department('Tarco Aviation')
        operations = self._department('Operations', parent=root)
        finance = self._department('Finance', parent=root)
        human_resources = self._department('Human Resources', parent=root)
        jobs = {
            'technician': self._job('Technician', operations),
            'accountant': self._job('Accountant', finance),
            'pilot': self._job('Pilot', operations),
            'officer': self._job('HR Officer', human_resources),
        }

        people = [
            {
                'name': 'Ahmed Hassan', 'department': operations, 'job': jobs['technician'],
                'hire': today - relativedelta(years=2, months=7), 'scheme': '21',
                'basic': 4500, 'cola': 400, 'transport': 300, 'housing': 800,
                'tax': True, 'auto': True, 'tax_rate': 10, 'ins': True, 'ins_rate': 5,
            },
            {
                'name': 'Fatima Ali', 'department': finance, 'job': jobs['accountant'],
                'hire': today - relativedelta(years=1, months=2), 'scheme': '30',
                'basic': 6200, 'cola': 500, 'transport': 350, 'housing': 1000,
                'tax': True, 'auto': False, 'tax_rate': 10, 'ins': True, 'ins_rate': 5,
            },
            {
                'name': 'Omar Ibrahim', 'department': operations, 'job': jobs['pilot'],
                'hire': today - relativedelta(years=3), 'scheme': '30',
                'basic': 12000, 'cola': 800, 'transport': 500, 'housing': 2000,
                'tax': True, 'auto': True, 'tax_rate': 15, 'ins': False, 'ins_rate': 0,
                'exempt': True,
            },
            {
                'name': 'Sara Mohamed', 'department': human_resources, 'job': jobs['officer'],
                'hire': today - relativedelta(days=40), 'scheme': '21',
                'basic': 3800, 'cola': 300, 'transport': 250, 'housing': 600,
                'tax': False, 'auto': False, 'tax_rate': 0, 'ins': False, 'ins_rate': 0,
            },
            {
                'name': 'Khalid Yousif', 'department': operations, 'job': jobs['technician'],
                'hire': today - relativedelta(years=4), 'scheme': '21',
                'basic': 4000, 'cola': 300, 'transport': 250, 'housing': 500,
                'tax': False, 'auto': False, 'tax_rate': 0, 'ins': False, 'ins_rate': 0,
                'resign': today - relativedelta(months=1),
            },
            {
                'name': 'Nour Eldeen', 'department': finance, 'job': jobs['accountant'],
                'hire': today - relativedelta(years=5), 'scheme': '21',
                'basic': 5000, 'cola': 400, 'transport': 300, 'housing': 700,
                'tax': True, 'auto': False, 'tax_rate': 10, 'ins': True, 'ins_rate': 5,
                'rehire': today - relativedelta(months=2),
            },
        ]
        employees = self.env['hr.employee']
        by_name = {}
        for person in people:
            employee = self._make('hr.employee', {
                'name': person['name'],
                'company_id': company.id,
                'department_id': person['department'].id,
                'job_id': person['job'].id,
                'tarco_hire_date': person['hire'],
                'tarco_leave_scheme': person['scheme'],
                'tarco_basic_wage': person['basic'],
                'tarco_cola': person['cola'],
                'tarco_transport_allowance': person['transport'],
                'tarco_housing_allowance': person['housing'],
                'tarco_subject_to_tax': person['tax'],
                'tarco_tax_rate': person['tax_rate'],
                'tarco_subject_to_insurance': person['ins'],
                'tarco_insurance_rate': person['ins_rate'],
                'tarco_auto_statutory': person['auto'],
                'tarco_shift_id': shift.id if shift else False,
                'tarco_exempt_late': person.get('exempt', False),
                'work_email': '%s@demo.tarco.local' % person['name'].split()[0].lower(),
                'private_phone': '050%07d' % (1000000 + len(by_name)),
                'birthday': person['hire'] - relativedelta(years=28),
                'sex': 'female' if person['name'].split()[0] in ('Fatima', 'Sara', 'Nour') else 'male',
                'marital': 'married' if person.get('resign') or person.get('rehire') else 'single',
            })
            if person.get('resign'):
                employee.tarco_resignation_date = person['resign']
            if person.get('rehire'):
                employee.tarco_rehire_date = person['rehire']
                employee.tarco_resignation_date = False
            employees |= employee
            by_name[person['name']] = employee

        ahmed, fatima, omar, sara = (by_name[name] for name in (
            'Ahmed Hassan', 'Fatima Ali', 'Omar Ibrahim', 'Sara Mohamed'))
        khalid = by_name['Khalid Yousif']
        nour = by_name['Nour Eldeen']
        omar.parent_id = False
        fatima.parent_id = omar
        sara.parent_id = fatima
        ahmed.parent_id = omar
        khalid.parent_id = omar
        nour.parent_id = fatima
        for dept, manager in (
            (root, omar), (operations, omar), (finance, fatima), (human_resources, sara),
        ):
            if dept.tarco_is_demo:
                dept.manager_id = manager

        for employee, kinds in (
            (ahmed, [('hiring', 'national_id'), ('hiring', 'photo'), ('audit', 'contract')]),
            (sara, [('hiring', 'qualification'), ('audit', 'application')]),
        ):
            for group, kind in kinds:
                self._make('tarco.hr.document', {
                    'employee_id': employee.id,
                    'group_type': group,
                    'kind': kind,
                    'received': True,
                    'document_date': employee.tarco_hire_date,
                    'note': 'Demo document',
                })

        notice = self._make('tarco.hr.onboarding', {
            'employee_id': sara.id,
            'need_training': True,
            'need_computer': True,
            'need_mobile': True,
            'need_uniform': True,
            'need_badge': True,
            'note': 'Desk on the second floor. Badge from security.',
        })
        self._safe(notice.action_send)
        notice.requirement_ids.write({'tarco_is_demo': True})

        computer = self.env.ref('tarco_hris.asset_type_computer', raise_if_not_found=False)
        mobile = self.env.ref('tarco_hris.asset_type_mobile', raise_if_not_found=False)
        uniform = self.env.ref('tarco_hris.asset_type_uniform', raise_if_not_found=False)
        badge = self.env.ref('tarco_hris.asset_type_badge', raise_if_not_found=False)
        if computer:
            ahmed_pc = self._make('tarco.hr.asset', {
                'employee_id': ahmed.id,
                'type_id': computer.id,
                'description': 'Dell Latitude 5540',
                'serial': 'DL-AH-5540',
                'condition_issue': 'New',
                'issue_date': ahmed.tarco_hire_date,
            })
            self._safe(ahmed_pc.action_issue)
            fatima_pc = self._make('tarco.hr.asset', {
                'employee_id': fatima.id,
                'type_id': computer.id,
                'description': 'HP EliteBook 840',
                'serial': 'HP-FA-840',
                'condition_issue': 'Good',
                'issue_date': fatima.tarco_hire_date,
            })
            self._safe(fatima_pc.action_issue)
            khalid_pc = self._make('tarco.hr.asset', {
                'employee_id': khalid.id,
                'type_id': computer.id,
                'description': 'Lenovo ThinkPad',
                'serial': 'LN-KY-01',
                'issue_date': khalid.tarco_hire_date,
            })
            self._safe(khalid_pc.action_issue)
            if khalid_pc.state == 'issued':
                khalid_pc.write({
                    'state': 'returned',
                    'return_date': khalid.tarco_resignation_date,
                    'condition_return': 'Returned at end of service',
                })
        if mobile:
            ahmed_phone = self._make('tarco.hr.asset', {
                'employee_id': ahmed.id,
                'type_id': mobile.id,
                'description': 'Samsung Galaxy A55',
                'serial': 'SM-AH-A55',
                'issue_date': ahmed.tarco_hire_date,
            })
            self._safe(ahmed_phone.action_issue)
        if uniform:
            uniform_req = notice.requirement_ids.filtered(lambda rec: rec.kind == 'uniform')[:1]
            if uniform_req:
                self._safe(uniform_req.action_issue_custody)
                if uniform_req.asset_id:
                    uniform_req.asset_id.write({
                        'tarco_is_demo': True,
                        'description': 'Office uniform set',
                        'serial': 'UNI-SM-01',
                    })
        if badge:
            nour_badge = self._make('tarco.hr.asset', {
                'employee_id': nour.id,
                'type_id': badge.id,
                'description': 'Staff badge',
                'serial': 'BDG-NE-01',
                'issue_date': nour.tarco_rehire_date or nour.tarco_hire_date,
            })
            self._safe(nour_badge.action_issue)

        year = today.year
        for name, day, month in (
            ('Eid al-Fitr (demo)', 1, 4),
            ('Independence Day (demo)', 1, 1),
        ):
            holiday = self._make('tarco.hr.public.holiday', {
                'name': name,
                'holiday_date': fields.Date.from_string('%s-%02d-%02d' % (year, month, day)),
                'company_id': company.id,
            })
            self._safe(holiday.action_publish)
            if holiday.calendar_leave_id:
                holiday.calendar_leave_id.tarco_is_demo = True

        self._safe(employees.action_tarco_apply_leave_scheme)
        allocations = self.env['hr.leave.allocation'].sudo().search([('employee_id', 'in', employees.ids)])
        allocations.write({'tarco_is_demo': True})

        for employee, leave_type, start, days, mode in (
            (ahmed, annual, today - relativedelta(days=20), 3, 'balance'),
            (fatima, casual, today - relativedelta(days=8), 1, 'balance'),
            (omar, sick, today - relativedelta(days=12), 2, 'partial'),
        ):
            if not leave_type:
                continue
            leave = self._create_leave(employee, leave_type, start, days, mode)
            if leave and mode == 'partial':
                leave.tarco_deduction_percent = 50.0

        encash = self._make('tarco.hr.leave.encashment', {
            'employee_id': omar.id,
            'days': 3,
            'encash_date': today.replace(day=1),
        })
        self._safe(encash.action_confirm)

        self._create_attendance(employees.filtered(lambda emp: not emp.tarco_resignation_date), today)
        self.env['tarco.hr.attendance.day'].sudo().sync_range(
            today - timedelta(days=14), today, employees.filtered(lambda emp: not emp.tarco_resignation_date),
        )
        days = self.env['tarco.hr.attendance.day'].sudo().search([('employee_id', 'in', employees.ids)])
        days.write({'tarco_is_demo': True})

        mission = self._make('tarco.hr.mission', {
            'place': 'Cairo',
            'purpose': 'Aircraft inspection and station visit.',
            'date_start': today + timedelta(days=5),
            'date_end': today + timedelta(days=7),
            'hour_start': 7.5,
            'hour_end': 18.0,
            'per_diem': 150,
            'currency_id': usd.id if usd and usd.active else company.currency_id.id,
            'company_id': company.id,
            'line_ids': [(0, 0, {'employee_id': ahmed.id}), (0, 0, {'employee_id': omar.id})],
        })
        self._safe(mission.action_approve)
        if mission.line_ids.calendar_event_id:
            mission.line_ids.calendar_event_id.tarco_is_demo = True

        overtime = self._make('tarco.hr.overtime', {
            'date_from': today - timedelta(days=14),
            'date_to': today,
            'company_id': company.id,
        })
        self._safe(overtime.action_fill)
        self._safe(overtime.action_confirm)

        if conduct:
            penalty = self._make('tarco.hr.penalty', {
                'rule_id': conduct.id,
                'penalty_date': today - timedelta(days=3),
                'start_date': today.replace(day=1),
                'line_ids': [(0, 0, {'employee_id': ahmed.id, 'amount': 150})],
            })
            self._safe(penalty.action_confirm)
        if late_rule:
            self._make('tarco.hr.penalty', {
                'rule_id': late_rule.id,
                'penalty_date': today - timedelta(days=1),
                'line_ids': [(0, 0, {'employee_id': fatima.id, 'hours': 1})],
            })

        reward = self._make('tarco.hr.reward', {
            'employee_id': fatima.id,
            'reason': 'Outstanding month-end closing',
            'mode': 'amount',
            'amount': 500,
            'reward_date': today - timedelta(days=2),
        })
        self._safe(reward.action_confirm)

        short = self._make('tarco.hr.advance', {
            'employee_id': ahmed.id,
            'advance_type': 'short',
            'description': 'Emergency short advance',
            'amount': 400,
            'due_date': today.replace(day=1) + relativedelta(months=1),
        })
        self._safe(short.action_confirm)
        loan = self._make('tarco.hr.advance', {
            'employee_id': fatima.id,
            'advance_type': 'long',
            'description': 'Laptop purchase loan',
            'amount': 1800,
            'installment_count': 6,
            'due_date': today.replace(day=1),
        })
        self._safe(loan.action_confirm)

        self._safe(fatima.action_tarco_post_statutory)

        template = self._make('tarco.hr.kpi.template', {
            'name': 'Office staff review',
            'company_id': company.id,
            'line_ids': [
                (0, 0, {'name': 'Quality of work', 'weight': 2, 'max_score': 5}),
                (0, 0, {'name': 'Attendance and punctuality', 'weight': 1, 'max_score': 5}),
                (0, 0, {'name': 'Teamwork', 'weight': 1, 'max_score': 5}),
            ],
        })
        review = self._make('tarco.hr.kpi.review', {
            'employee_id': fatima.id,
            'template_id': template.id,
            'date_from': today.replace(day=1) - relativedelta(months=1),
            'date_to': today.replace(day=1) - timedelta(days=1),
        })
        self._safe(review.action_load_template)
        scores = (4.5, 4.0, 5.0)
        for line, score in zip(review.line_ids, scores):
            line.score = score
        review.output_ids = [(0, 0, {
            'output_date': today - timedelta(days=10),
            'description': 'Closed the monthly accounts on time',
            'quality': 5,
        })]
        self._safe(review.action_done)

        self._load_recruitment(company, jobs['officer'], today)
        self.env['hr.salary.attachment'].sudo().search([
            ('employee_ids', 'in', employees.ids),
            ('tarco_is_demo', '=', False),
        ]).write({'tarco_is_demo': True})

    def _department(self, name, parent=None):
        existing = self.env['hr.department'].sudo().search([('name', '=', name)], limit=1)
        if existing:
            if parent and existing.tarco_is_demo and existing.parent_id != parent:
                existing.parent_id = parent
            return existing
        values = {'name': name, 'company_id': self.env.company.id}
        if parent:
            values['parent_id'] = parent.id
        return self._make('hr.department', values)

    def _job(self, name, department):
        existing = self.env['hr.job'].sudo().search([
            ('name', '=', name), ('department_id', '=', department.id),
        ], limit=1)
        if existing:
            return existing
        return self._make('hr.job', {
            'name': name,
            'department_id': department.id,
            'company_id': self.env.company.id,
        })

    def _create_leave(self, employee, leave_type, start, days, mode):
        end = start + timedelta(days=days - 1)
        try:
            leave = self._make('hr.leave', {
                'name': 'Demo leave',
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': start,
                'request_date_to': end,
                'tarco_deduction_mode': mode,
            })
        except Exception:
            return self.env['hr.leave']
        if hasattr(leave, 'action_approve'):
            self._safe(leave.action_approve)
        if hasattr(leave, 'action_validate'):
            self._safe(leave.action_validate)
        elif hasattr(leave, '_action_validate'):
            self._safe(leave._action_validate)
        return leave

    def _create_attendance(self, employees, today):
        Attendance = self.env['hr.attendance'].sudo()
        created = 0
        for offset in range(12, 0, -1):
            day = today - timedelta(days=offset)
            if day.weekday() == 4:
                continue
            for index, employee in enumerate(employees):
                if employee.tarco_hire_date and day < employee.tarco_hire_date:
                    continue
                late = 10 if index % 3 == 0 else 0
                overtime = 90 if index % 2 == 0 else 0
                check_in = datetime.combine(day, time(8, 0)) + timedelta(minutes=late)
                check_out = datetime.combine(day, time(16, 5)) + timedelta(minutes=overtime)
                if Attendance.search_count([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', datetime.combine(day, time.min)),
                    ('check_in', '<=', datetime.combine(day, time.max)),
                ]):
                    continue
                self._make('hr.attendance', {
                    'employee_id': employee.id,
                    'check_in': fields.Datetime.to_string(check_in),
                    'check_out': fields.Datetime.to_string(check_out),
                })
                created += 1
        return created

    def _load_recruitment(self, company, officer_job, today):
        job = self._make('hr.job', {
            'name': 'Cabin Crew',
            'department_id': officer_job.department_id.id,
            'company_id': company.id,
            'tarco_approved_headcount': 4,
            'tarco_years_experience': 2,
            'tarco_qualification': 'secondary',
            'tarco_expected_wage': 3500,
            'tarco_skills': 'Customer service, English, swimming certificate',
            'tarco_question_ids': [
                (0, 0, {'name': 'Do you have a valid passport?', 'expected_answer': 'yes'}),
                (0, 0, {'name': 'Years of cabin experience', 'expected_answer': '2'}),
            ],
        })
        job.action_open_vacancies()
        applicants = (
            ('Lina Farouk', 'shortlisted', 'first', 'yes', '2', 'bachelor'),
            ('Hassan Adel', 'maybe', 'none', 'yes', '1', 'diploma'),
            ('Mona Saleh', 'rejected', 'none', 'no', '0', 'secondary'),
        )
        for name, track, round_name, passport, years, qualification in applicants:
            vals = {
                'partner_name': name,
                'email_from': '%s@demo.apply.local' % name.split()[0].lower(),
                'partner_phone': '0550000%s' % years,
                'job_id': job.id,
                'tarco_track': track,
                'tarco_interview_round': round_name,
                'tarco_years_experience': float(years),
                'tarco_qualification': qualification,
            }
            if round_name != 'none':
                vals['tarco_interview_datetime'] = fields.Datetime.to_string(
                    datetime.combine(today + timedelta(days=4), time(10, 0)))
            applicant = self._make('hr.applicant', vals)
            answers = []
            for question, answer in zip(job.tarco_question_ids, (passport, years)):
                answers.append((0, 0, {'question_id': question.id, 'answer': answer}))
            if answers:
                applicant.tarco_answer_ids = answers
            if round_name != 'none':
                self._safe(applicant.action_send_interview)
                if applicant.tarco_meeting_id:
                    applicant.tarco_meeting_id.tarco_is_demo = True
