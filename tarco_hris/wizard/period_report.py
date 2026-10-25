# -*- coding: utf-8 -*-
import re
from datetime import date, datetime, timedelta

from odoo import fields, models, _

from odoo.addons.tarco_hris.models.tarco_common import (
    _NUM_HEADERS, _header_key, fmt_time, markup_sections, money,
)


class TarcoHrPenaltyGenerateWizard(models.TransientModel):
    _name = 'tarco.hr.penalty.generate.wizard'
    _description = 'Generate Attendance Penalties'

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department')
    include_late = fields.Boolean(default=True)
    include_absence = fields.Boolean(default=True)

    def action_generate(self):
        self.env['tarco.hr.attendance.day'].sync_range(self.date_from, self.date_to)
        domain = [
            ('work_date', '>=', self.date_from),
            ('work_date', '<=', self.date_to),
        ]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        days = self.env['tarco.hr.attendance.day'].search(domain)
        created = self.env['tarco.hr.penalty']
        late_rule = self.env.ref('tarco_hris.penalty_rule_late', raise_if_not_found=False)
        absence_rule = self.env.ref('tarco_hris.penalty_rule_absence', raise_if_not_found=False)
        if self.include_late and late_rule:
            created |= self._generate(days.filtered(lambda day: day.late_minutes > 0), late_rule, late=True)
        if self.include_absence and absence_rule:
            created |= self._generate(days.filtered(lambda day: day.status == 'absent'), absence_rule, late=False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated penalties'),
            'res_model': 'tarco.hr.penalty',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
        }

    def _generate(self, days, rule, late):
        created = self.env['tarco.hr.penalty']
        kind = 'late' if late else 'absence'
        for day in days:
            reason = day.attendance_penalty_reason(kind)
            existing = self.env['tarco.hr.penalty.line'].search([
                ('employee_id', '=', day.employee_id.id),
                ('penalty_id.rule_id', '=', rule.id),
                ('penalty_id.penalty_date', '=', day.work_date),
                ('penalty_id.state', '!=', 'cancel'),
            ], limit=1)
            if existing:
                if existing.penalty_id.state == 'draft':
                    existing.penalty_id.reason = reason
                    created |= existing.penalty_id
                continue
            hours = day.late_minutes / 60.0 if late else 0.0
            created |= self.env['tarco.hr.penalty'].create({
                'rule_id': rule.id,
                'penalty_date': day.work_date,
                'start_date': day.work_date,
                'reason': reason,
                'company_id': day.company_id.id,
                'line_ids': [(0, 0, {
                    'employee_id': day.employee_id.id,
                    'hours': hours,
                    'days': 0.0 if late else 1.0,
                })],
            })
        return created


class TarcoHrPeriodReportWizard(models.TransientModel):
    _name = 'tarco.hr.period.report.wizard'
    _description = 'Tarco HR Period Report'

    report_type = fields.Selection([
        ('contract_renewal', 'Contracts to renew'),
        ('service_duration', 'Length of service'),
        ('movement', 'Hires and resignations'),
        ('turnover', 'Turnover rate'),
        ('hire_cost', 'Cost of hires and resignations'),
        ('attendance', 'Attendance'),
        ('leave_month', 'Monthly leave'),
        ('leave_official', 'Official holidays'),
        ('leave_annual', 'Annual leave'),
        ('leave_sick', 'Sick leave'),
        ('leave_encashment', 'Leave encashment cost'),
        ('mission', 'Missions'),
        ('overtime', 'Overtime'),
        ('penalty', 'Penalties'),
        ('reward', 'Rewards'),
        ('advance_due', 'Advances due'),
        ('advance_remaining', 'Remaining advances'),
        ('advance_year', 'Advances paid in the period'),
        ('recruitment', 'Recruitment'),
        ('kpi', 'KPIs'),
    ], required=True, default='contract_renewal')
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department')
    employee_id = fields.Many2one('hr.employee')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def _employees(self):
        domain = [('company_id', '=', self.company_id.id)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.employee_id:
            domain.append(('id', '=', self.employee_id.id))
        return self.env['hr.employee'].search(domain)

    def _in_period(self, value):
        return bool(value and self.date_from <= value <= self.date_to)

    def _report_sections(self):
        method = getattr(self, '_section_%s' % self.report_type)
        return method()

    def get_report_title(self):
        self.ensure_one()
        return dict(self._fields['report_type']._description_selection(self.env)).get(
            self.report_type, self.report_type)

    def get_report_markup(self):
        return markup_sections(self._report_sections())

    def action_print(self):
        if self.report_type == 'attendance':
            self.env['tarco.hr.attendance.day'].sync_range(self.date_from, self.date_to, self._employees())
        return self.env.ref('tarco_hris.action_report_period').report_action(self)

    def action_sync_attendance(self):
        self.env['tarco.hr.attendance.day'].sync_range(self.date_from, self.date_to, self._employees())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance'),
                'message': _('Fingerprint attendance was summarised for the selected period.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_export_xlsx(self):
        import base64
        import io

        try:
            import xlsxwriter
        except ImportError as error:
            from odoo.exceptions import UserError
            raise UserError(_('xlsxwriter is not installed.')) from error
        if self.report_type == 'attendance':
            self.action_sync_attendance()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'default_date_format': 'dd mmm yyyy',
        })
        styles = self._xlsx_styles(workbook)
        for title, headers, rows in self._report_sections():
            self._xlsx_write_sheet(workbook, styles, title, headers, rows)
        workbook.close()
        filename = 'Tarco-HRIS-%s.xlsx' % (self.get_report_title() or self.report_type)
        attachment = self.env['ir.attachment'].create({
            'name': filename.replace(' ', '-'),
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _xlsx_period_label(self):
        self.ensure_one()
        parts = [
            _('Period: %s — %s') % (self.date_from, self.date_to),
        ]
        if self.department_id:
            parts.append(_('Department: %s') % self.department_id.name)
        if self.employee_id:
            parts.append(_('Employee: %s') % self.employee_id.name)
        parts.append(self.company_id.name or '')
        return '   |   '.join(part for part in parts if part)

    def _xlsx_styles(self, workbook):
        navy = '#0F2C4C'
        teal = '#13A89E'
        line = '#C5CDD6'
        base = {
            'font_name': 'Calibri',
            'font_size': 10,
            'valign': 'vcenter',
            'border': 1,
            'border_color': line,
        }
        return {
            'band': workbook.add_format({
                'bold': True, 'font_name': 'Calibri', 'font_size': 16,
                'font_color': '#FFFFFF', 'bg_color': navy, 'valign': 'vcenter',
                'align': 'left',
            }),
            'subtitle': workbook.add_format({
                'font_name': 'Calibri', 'font_size': 10, 'font_color': '#334155',
                'bg_color': '#E8EEF4', 'valign': 'vcenter',
            }),
            'section': workbook.add_format({
                'bold': True, 'font_name': 'Calibri', 'font_size': 12,
                'font_color': teal, 'valign': 'vcenter',
            }),
            'header': workbook.add_format(dict(base, bold=True, font_color='#FFFFFF',
                                               bg_color=navy, align='center', text_wrap=True)),
            'text': workbook.add_format(dict(base, align='left')),
            'text_alt': workbook.add_format(dict(base, align='left', bg_color='#F4F7FA')),
            'num': workbook.add_format(dict(base, align='right', num_format='#,##0.00')),
            'num_alt': workbook.add_format(dict(base, align='right', num_format='#,##0.00', bg_color='#F4F7FA')),
            'int': workbook.add_format(dict(base, align='right', num_format='#,##0')),
            'int_alt': workbook.add_format(dict(base, align='right', num_format='#,##0', bg_color='#F4F7FA')),
            'date': workbook.add_format(dict(base, align='center', num_format='dd mmm yyyy')),
            'date_alt': workbook.add_format(dict(base, align='center', num_format='dd mmm yyyy', bg_color='#F4F7FA')),
            'total': workbook.add_format(dict(base, bold=True, bg_color='#E8EEF4')),
            'total_num': workbook.add_format(dict(base, bold=True, align='right',
                                                  num_format='#,##0.00', bg_color='#E8EEF4')),
        }

    def _xlsx_cell(self, value, numeric=False):
        if value in (None, False, '', '—'):
            return '', 'text'
        if isinstance(value, datetime):
            return value.date() if not getattr(value, 'hour', None) else value, 'date'
        if isinstance(value, date):
            return value, 'date'
        text = str(value).strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            try:
                return fields.Date.from_string(text), 'date'
            except Exception:
                return text, 'text'
        if numeric:
            try:
                number = float(text.replace(',', ''))
                return number, 'int' if number == int(number) else 'num'
            except (TypeError, ValueError):
                return text, 'text'
        return text, 'text'

    def _xlsx_write_sheet(self, workbook, styles, title, headers, rows):
        sheet = workbook.add_worksheet((title or _('Report'))[:31])
        last = max(len(headers) - 1, 0)
        sheet.hide_gridlines(2)
        sheet.set_default_row(18)
        sheet.set_row(0, 28)
        sheet.set_row(1, 20)

        def _banner(row, text, fmt):
            if last:
                sheet.merge_range(row, 0, row, last, text, fmt)
            else:
                sheet.write(row, 0, text, fmt)

        _banner(0, '%s  —  %s' % (
            self.company_id.name or _('Tarco HRIS'), self.get_report_title(),
        ), styles['band'])
        _banner(1, self._xlsx_period_label(), styles['subtitle'])
        _banner(2, title or '', styles['section'])
        sheet.set_row(3, 22)
        numeric = [_header_key(header) in _NUM_HEADERS for header in headers]
        for col, header in enumerate(headers):
            sheet.write(3, col, header, styles['header'])
        widths = [max(12, min(18, len(str(header)) + 4)) for header in headers]
        for row_index, row in enumerate(rows):
            excel_row = 4 + row_index
            is_total = any(str(value).strip().lower() == 'total' for value in row if value not in (None, False))
            alt = row_index % 2
            for col, value in enumerate(row):
                parsed, kind = self._xlsx_cell(value, numeric[col] if col < len(numeric) else False)
                if is_total:
                    fmt = styles['total_num'] if kind in ('num', 'int') else styles['total']
                else:
                    key = '%s_alt' % kind if alt and ('%s_alt' % kind) in styles else kind
                    fmt = styles.get(key, styles['text_alt'] if alt else styles['text'])
                sheet.write(excel_row, col, parsed, fmt)
                widths[col] = max(widths[col], min(42, len(str(parsed if parsed != '' else '—')) + 3))
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
        data_end = 3 + max(len(rows), 1)
        sheet.autofilter(3, 0, data_end, last)
        sheet.freeze_panes(4, 0)
        sheet.repeat_rows(0, 3)
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.fit_to_pages(1, 0)
        sheet.set_margins(0.5, 0.5, 0.6, 0.5)
        if not rows:
            sheet.write(4, 0, _('No records.'), styles['text'])

    def _employee_row_start(self, employee):
        return [
            employee.employee_code or '',
            employee.name or '',
            employee.department_id.name or '',
            employee.section_id.name or '',
        ]

    def _section_contract_renewal(self):
        rows = []
        employees = self._employees().filtered(
            lambda employee: employee.tarco_contract_date_end and self._in_period(employee.tarco_contract_date_end)
        )
        for employee in employees:
            rows.append(self._employee_row_start(employee) + [
                str(employee.tarco_hire_date or ''),
                str(employee.tarco_contract_date_end or ''),
                str(employee.tarco_trial_date_end or ''),
            ])
        return [(_('Contracts to renew'), ['Code', 'Name', 'Department', 'Section', 'Hire date', 'Contract end', 'Probation end'], rows)]

    def _section_service_duration(self):
        rows = []
        for employee in self._employees():
            rows.append(self._employee_row_start(employee) + [
                str(employee.tarco_hire_date or ''),
                employee.tarco_service_years,
                employee.tarco_service_months,
                employee.tarco_service_days,
                employee.tarco_service_display or '',
            ])
        return [(_('Length of service'), ['Code', 'Name', 'Department', 'Section', 'Hire date', 'Years', 'Months', 'Days', 'Service'], rows)]

    def _section_movement(self):
        hires, leaves = [], []
        for employee in self._employees():
            if self._in_period(employee.tarco_hire_date) or self._in_period(employee.tarco_rehire_date):
                hires.append(self._employee_row_start(employee) + [str(employee.tarco_hire_date or ''), str(employee.tarco_rehire_date or '')])
            if self._in_period(employee.tarco_resignation_date):
                leaves.append(self._employee_row_start(employee) + [str(employee.tarco_resignation_date or '')])
        headers = ['Code', 'Name', 'Department', 'Section', 'Hire date', 'Rehire date']
        return [
            (_('Hires'), headers, hires),
            (_('Resignations'), ['Code', 'Name', 'Department', 'Section', 'Resignation'], leaves),
        ]

    def _section_turnover(self):
        employees = self.env['hr.employee'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id),
        ])
        if self.department_id:
            employees = employees.filtered(lambda employee: employee.department_id == self.department_id)
        resigned = employees.filtered(lambda employee: self._in_period(employee.tarco_resignation_date))
        hired = employees.filtered(lambda employee: self._in_period(employee.tarco_hire_date))
        active_now = employees.filtered(lambda employee: employee.active and not employee.tarco_resignation_date)
        average = max(len(active_now), 1)
        rate = len(resigned) / average * 100.0
        rows = [[
            len(hired), len(resigned), len(active_now), money(rate),
        ]]
        return [(_('Turnover'), ['Hires', 'Resignations', 'Active headcount', 'Turnover %'], rows)]

    def _section_hire_cost(self):
        hire_rows, leave_rows = [], []
        for employee in self._employees():
            gross = money(employee.tarco_gross_wage)
            if self._in_period(employee.tarco_hire_date) or self._in_period(employee.tarco_rehire_date):
                hire_rows.append(self._employee_row_start(employee) + [gross])
            if self._in_period(employee.tarco_resignation_date):
                leave_rows.append(self._employee_row_start(employee) + [gross])
        headers = ['Code', 'Name', 'Department', 'Section', 'Monthly gross']
        return [
            (_('Hiring cost'), headers, hire_rows),
            (_('Resignation cost'), headers, leave_rows),
        ]

    def _section_attendance(self):
        days = self.env['tarco.hr.attendance.day'].search([
            ('employee_id', 'in', self._employees().ids),
            ('work_date', '>=', self.date_from),
            ('work_date', '<=', self.date_to),
        ], order='department_id, work_date, employee_id')
        detail = []
        Day = self.env['tarco.hr.attendance.day']
        status_labels = dict(Day._fields['status']._description_selection(self.env))
        for day in days:
            local_in = Day._as_local(day.employee_id, day.check_in)
            local_out = Day._as_local(day.employee_id, day.check_out)
            detail.append([
                day.work_date,
                day.employee_code or '',
                day.employee_id.name or '',
                day.department_id.name or '',
                fmt_time(local_in),
                fmt_time(local_out),
                status_labels.get(day.status, day.status),
                int(round(day.late_minutes or 0.0)),
                money(day.overtime_hours) if day.overtime_hours else '—',
                day.note or '',
            ])
        summary = {}
        for day in days:
            bucket = summary.setdefault(day.department_id.name or _('No department'), {
                'headcount': set(), 'present': 0, 'leave': 0, 'absent': 0, 'mission': 0,
            })
            bucket['headcount'].add(day.employee_id.id)
            if day.status in ('present', 'late'):
                bucket['present'] += 1
            elif day.status == 'leave':
                bucket['leave'] += 1
            elif day.status == 'absent':
                bucket['absent'] += 1
            elif day.status == 'mission':
                bucket['mission'] += 1
        summary_rows = [[
            name, len(values['headcount']), values['present'], values['leave'], values['absent'], values['mission'],
        ] for name, values in summary.items()]
        percent_rows = []
        for employee in self._employees():
            own = days.filtered(lambda day: day.employee_id == employee)
            working = own.filtered(lambda day: day.status not in ('rest', 'holiday'))
            present = own.filtered(lambda day: day.status in ('present', 'late', 'mission'))
            percent = (len(present) / len(working) * 100.0) if working else 0.0
            percent_rows.append(self._employee_row_start(employee) + [len(working), len(present), money(percent)])
        return [
            (_('Daily movement'), ['Date', 'Code', 'Name', 'Department', 'In', 'Out', 'Status', 'Late', 'OT', 'Note'], detail),
            (_('Department strength'), ['Department', 'Headcount', 'Present', 'Leave', 'Absent', 'Mission'], summary_rows),
            (_('Attendance percentage'), ['Code', 'Name', 'Department', 'Section', 'Working days', 'Attended', 'Percent'], percent_rows),
        ]

    def _leave_rows(self, kind=None):
        domain = [
            ('employee_id', 'in', self._employees().ids),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', self.date_to),
            ('request_date_to', '>=', self.date_from),
        ]
        if kind:
            domain.append(('holiday_status_id.tarco_kind', '=', kind))
        rows = []
        for leave in self.env['hr.leave'].search(domain):
            rows.append(self._employee_row_start(leave.employee_id) + [
                leave.holiday_status_id.name or '',
                str(leave.request_date_from or ''),
                str(leave.request_date_to or ''),
                money(leave.number_of_days),
                leave.tarco_deduction_mode or '',
            ])
        return rows

    def _section_leave_month(self):
        rows = self._leave_rows()
        days = self.env['tarco.hr.attendance.day'].search_count([
            ('employee_id', 'in', self._employees().ids),
            ('work_date', '>=', self.date_from),
            ('work_date', '<=', self.date_to),
            ('status', 'not in', ('rest', 'holiday')),
        ]) or 1
        leave_days = sum(float(row[7]) for row in rows) if rows else 0.0
        return [
            (_('Leave during the period'), ['Code', 'Name', 'Department', 'Section', 'Type', 'From', 'To', 'Days', 'Deduction'], rows),
            (_('Share of working days'), ['Leave days', 'Working-day records', 'Percent'], [[money(leave_days), days, money(leave_days / days * 100.0)]]),
        ]

    def _section_leave_official(self):
        holidays = self.env['tarco.hr.public.holiday'].search([
            ('company_id', '=', self.company_id.id),
            ('observed_date', '>=', self.date_from),
            ('observed_date', '<=', self.date_to),
        ])
        rows = [[holiday.name, str(holiday.holiday_date), str(holiday.moved_date or ''), str(holiday.observed_date)] for holiday in holidays]
        taken = self._leave_rows('official')
        return [
            (_('Official holidays'), ['Name', 'Original date', 'Moved to', 'Observed'], rows),
            (_('Official leave taken'), ['Code', 'Name', 'Department', 'Section', 'Type', 'From', 'To', 'Days', 'Deduction'], taken),
        ]

    def _section_leave_annual(self):
        rows = self._leave_rows('annual') + self._leave_rows('casual')
        return [(_('Annual and casual leave'), ['Code', 'Name', 'Department', 'Section', 'Type', 'From', 'To', 'Days', 'Deduction'], rows)]

    def _section_leave_sick(self):
        return [(_('Sick leave'), ['Code', 'Name', 'Department', 'Section', 'Type', 'From', 'To', 'Days', 'Deduction'], self._leave_rows('sick'))]

    def _section_leave_encashment(self):
        records = self.env['tarco.hr.leave.encashment'].search([
            ('employee_id', 'in', self._employees().ids),
            ('encash_date', '>=', self.date_from),
            ('encash_date', '<=', self.date_to),
            ('state', '=', 'confirmed'),
        ])
        rows = [self._employee_row_start(record.employee_id) + [money(record.days), money(record.amount)] for record in records]
        rows.append(['', '', '', _('Total'), '', money(sum(records.mapped('amount')))])
        return [(_('Paid leave sold'), ['Code', 'Name', 'Department', 'Section', 'Days', 'Amount'], rows)]

    def _section_mission(self):
        missions = self.env['tarco.hr.mission'].search([
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ('approved', 'done')),
            ('date_start', '<=', self.date_to),
            ('date_end', '>=', self.date_from),
        ])
        if self.employee_id:
            missions = missions.filtered(lambda mission: self.employee_id in mission.line_ids.employee_id)
        rows = []
        for mission in missions:
            names = ', '.join(
                '%s %s' % (line.employee_code or '', line.employee_id.name) for line in mission.line_ids
            )
            rows.append([
                mission.name, mission.place, str(mission.date_start), mission.number_of_days,
                money(mission.total_hours), mission.currency_id.name, money(mission.cost),
                money(mission.cost_company_currency), names,
            ])
        company_currency = self.company_id.currency_id.name
        by_place = {}
        for mission in missions:
            bucket = by_place.setdefault(mission.place, {'hours': 0.0, 'cost': 0.0, 'count': 0})
            bucket['hours'] += mission.total_hours
            bucket['cost'] += mission.cost_company_currency
            bucket['count'] += 1
        place_rows = [[place, values['count'], money(values['hours']), money(values['cost'])] for place, values in by_place.items()]
        return [
            (_('Missions'), ['Number', 'Place', 'Date', 'Days', 'Hours', 'Currency', 'Cost',
                             'Cost (%s)' % company_currency, 'Employees'], rows),
            (_('By place'), ['Place', 'Missions', 'Hours', 'Cost (%s)' % company_currency], place_rows),
        ]

    def _section_overtime(self):
        days = self.env['tarco.hr.attendance.day'].search([
            ('employee_id', 'in', self._employees().ids),
            ('work_date', '>=', self.date_from),
            ('work_date', '<=', self.date_to),
            ('overtime_hours', '>', 0),
        ])
        grouped = {}
        for day in days:
            bucket = grouped.setdefault(day.employee_id, {'hours': 0.0, 'amount': 0.0, 'h15': 0.0, 'h20': 0.0})
            bucket['hours'] += day.overtime_hours
            bucket['amount'] += day.overtime_amount
            if day.overtime_rate == 2:
                bucket['h20'] += day.overtime_hours
            else:
                bucket['h15'] += day.overtime_hours
        rows = []
        for employee, values in grouped.items():
            rows.append(self._employee_row_start(employee) + [
                money(values['h15']), money(values['h20']), money(values['hours']), money(values['amount']),
            ])
        rows.append(['', '', '', _('Total'), '', '', money(sum(days.mapped('overtime_hours'))), money(sum(days.mapped('overtime_amount')))])
        return [(_('Overtime'), ['Code', 'Name', 'Department', 'Section', 'Hours x 1.5', 'Hours x 2', 'Hours', 'Amount'], rows)]

    def _section_penalty(self):
        lines = self.env['tarco.hr.penalty.line'].search([
            ('employee_id', 'in', self._employees().ids),
            ('penalty_id.penalty_date', '>=', self.date_from),
            ('penalty_id.penalty_date', '<=', self.date_to),
            ('penalty_id.state', '=', 'confirmed'),
        ])
        rows = []
        reasons = {}
        for line in lines:
            rows.append(self._employee_row_start(line.employee_id) + [
                line.penalty_id.rule_id.name or '',
                str(line.penalty_id.penalty_date),
                money(line.amount),
                line.repeat_count,
            ])
            reasons[line.penalty_id.rule_id.name or _('Other')] = reasons.get(line.penalty_id.rule_id.name or _('Other'), 0) + 1
        total = sum(lines.mapped('amount'))
        reason_rows = []
        count = sum(reasons.values()) or 1
        for reason, times in reasons.items():
            reason_rows.append([reason, times, money(times / count * 100.0)])
        return [
            (_('Penalties'), ['Code', 'Name', 'Department', 'Section', 'Rule', 'Date', 'Amount', 'Repeat'], rows),
            (_('Deducted cost'), ['Amount'], [[money(total)]]),
            (_('Repeated reasons'), ['Reason', 'Count', 'Percent'], reason_rows),
        ]

    def _section_reward(self):
        rewards = self.env['tarco.hr.reward'].search([
            ('employee_id', 'in', self._employees().ids),
            ('reward_date', '>=', self.date_from),
            ('reward_date', '<=', self.date_to),
            ('state', '=', 'confirmed'),
        ])
        rows = [self._employee_row_start(reward.employee_id) + [reward.reason, money(reward.amount)] for reward in rewards]
        rows.append(['', '', '', _('Total'), '', money(sum(rewards.mapped('amount')))])
        return [(_('Rewards'), ['Code', 'Name', 'Department', 'Section', 'Reason', 'Amount'], rows)]

    def _advance_lines(self, state=None, paid=False):
        domain = [('employee_id', 'in', self._employees().ids)]
        if state:
            domain.append(('state', '=', state))
        if paid:
            domain.extend([('due_date', '>=', self.date_from), ('due_date', '<=', self.date_to), ('state', '=', 'paid')])
        else:
            domain.extend([('due_date', '>=', self.date_from), ('due_date', '<=', self.date_to)])
        return self.env['tarco.hr.advance.line'].search(domain)

    def _section_advance_due(self):
        lines = self._advance_lines('due')
        rows = [self._employee_row_start(line.employee_id) + [line.advance_id.name, line.advance_id.advance_type, str(line.due_date), money(line.amount)] for line in lines]
        return [(_('Advances due'), ['Code', 'Name', 'Department', 'Section', 'Advance', 'Type', 'Due', 'Amount'], rows)]

    def _section_advance_remaining(self):
        advances = self.env['tarco.hr.advance'].search([
            ('employee_id', 'in', self._employees().ids),
            ('state', '=', 'running'),
        ])
        rows = [self._employee_row_start(advance.employee_id) + [advance.name, money(advance.amount), money(advance.paid_amount), money(advance.remaining_amount)] for advance in advances]
        return [(_('Remaining advances'), ['Code', 'Name', 'Department', 'Section', 'Advance', 'Total', 'Paid', 'Remaining'], rows)]

    def _section_advance_year(self):
        lines = self._advance_lines(paid=True)
        rows = [self._employee_row_start(line.employee_id) + [line.advance_id.name, str(line.due_date), money(line.amount)] for line in lines]
        rows.append(['', '', '', _('Total'), '', '', money(sum(lines.mapped('amount')))])
        return [(_('Advances paid in the period'), ['Code', 'Name', 'Department', 'Section', 'Advance', 'Date', 'Amount'], rows)]

    def _section_recruitment(self):
        jobs = self.env['hr.job'].search([('company_id', '=', self.company_id.id)])
        open_jobs = jobs.filtered(lambda job: job.no_of_recruitment or job.tarco_vacancy)
        expected = sum((job.tarco_expected_wage or 0.0) * (job.no_of_recruitment or job.tarco_vacancy or 0) for job in open_jobs)
        applicants = self.env['hr.applicant'].search([
            ('job_id', 'in', jobs.ids),
            ('create_date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('create_date', '<', fields.Datetime.to_datetime(self.date_to + timedelta(days=1))),
        ])
        matched = applicants.filtered(lambda applicant: applicant.tarco_match_score >= 70)
        first = applicants.filtered(lambda applicant: applicant.tarco_interview_round in ('first', 'final') or applicant.tarco_interview_sent)
        final = applicants.filtered(lambda applicant: applicant.tarco_interview_round == 'final')
        rows = [[
            len(open_jobs), money(expected), len(applicants), len(matched), len(first), len(final),
        ]]
        return [(_('Recruitment'), [
            'Open jobs', 'Expected wages', 'Applicants', 'CVs matching 70%+', 'Contacted for first interview', 'Final interview',
        ], rows)]

    def _section_kpi(self):
        reviews = self.env['tarco.hr.kpi.review'].search([
            ('employee_id', 'in', self._employees().ids),
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
        ])
        rows = [self._employee_row_start(review.employee_id) + [
            money(review.hours_ratio), money(review.output_quality), money(review.score),
        ] for review in reviews]
        departments = {}
        for review in reviews:
            departments.setdefault(review.department_id.name or _('No department'), []).append(review.score)
        dept_rows = [[name, money(sum(scores) / len(scores) if scores else 0)] for name, scores in departments.items()]
        problems = []
        for review in reviews:
            for line in review.line_ids.filtered('is_problem'):
                problems.append(self._employee_row_start(review.employee_id) + [line.name, money(line.score), line.comment or ''])
        ranked = sorted(reviews, key=lambda review: review.score)
        low = ranked[:5]
        high = list(reversed(ranked[-5:]))
        rank_rows = [[_('Highest')] + self._employee_row_start(review.employee_id) + [money(review.score)] for review in high]
        rank_rows += [[_('Lowest')] + self._employee_row_start(review.employee_id) + [money(review.score)] for review in low]
        return [
            (_('Goal achievement'), ['Code', 'Name', 'Department', 'Section', 'Hours %', 'Quality %', 'Overall %'], rows),
            (_('Department average'), ['Department', 'Average %'], dept_rows),
            (_('Points to improve'), ['Code', 'Name', 'Department', 'Section', 'Question', 'Score', 'Comment'], problems),
            (_('Highest and lowest'), ['Rank', 'Code', 'Name', 'Department', 'Section', 'Score'], rank_rows),
        ]
