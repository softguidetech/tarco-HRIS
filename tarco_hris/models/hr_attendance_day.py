# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models

from .tarco_common import format_clock, tarco_hourly_wage


class TarcoHrAttendanceDay(models.Model):
    _name = 'tarco.hr.attendance.day'
    _description = 'Daily Attendance Summary'
    _order = 'work_date desc, employee_id'
    _rec_name = 'employee_id'

    _employee_day_unique = models.Constraint(
        'unique(employee_id, work_date)',
        'This employee already has a summary for that day.',
    )

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    employee_code = fields.Char(related='employee_id.employee_code', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    work_date = fields.Date(required=True, index=True)
    shift_id = fields.Many2one('tarco.hr.shift')
    check_in = fields.Datetime(string='Check in')
    check_out = fields.Datetime(string='Check out')
    late_minutes = fields.Float(string='Late minutes')
    regular_hours = fields.Float(string='Regular hours')
    overtime_hours = fields.Float(string='Overtime hours')
    overtime_rate = fields.Float(string='Overtime rate')
    overtime_amount = fields.Monetary()
    currency_id = fields.Many2one(related='company_id.currency_id')
    status = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        ('mission', 'Mission'),
        ('holiday', 'Public holiday'),
        ('rest', 'Rest day'),
        ('incomplete', 'Missing checkout'),
    ], required=True, default='absent')
    leave_id = fields.Many2one('hr.leave')
    mission_id = fields.Many2one('tarco.hr.mission')
    holiday_id = fields.Many2one('tarco.hr.public.holiday')
    overtime_line_id = fields.Many2one('tarco.hr.overtime.line', copy=False)
    note = fields.Char()

    @api.model
    def _employee_tz(self, employee):
        name = employee.tz or employee.resource_calendar_id.tz or 'Africa/Khartoum'
        try:
            return pytz.timezone(name)
        except pytz.UnknownTimeZoneError:
            return pytz.timezone('Africa/Khartoum')

    @api.model
    def _as_local(self, employee, moment):
        if not moment:
            return False
        zone = self._employee_tz(employee)
        if moment.tzinfo:
            return moment.astimezone(zone)
        return pytz.utc.localize(moment).astimezone(zone)

    @api.model
    def sync_range(self, date_from, date_to, employees=None):
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        if employees is None:
            employees = self.env['hr.employee'].search([('active', '=', True)])
        if not employees:
            return True
        punches = self.env['hr.attendance'].search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', datetime.combine(date_from, time.min) - timedelta(days=1)),
            ('check_in', '<=', datetime.combine(date_to, time.max) + timedelta(days=1)),
        ])
        punches_by_emp = {}
        for punch in punches:
            punches_by_emp.setdefault(punch.employee_id.id, []).append(punch)
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', date_to),
            ('request_date_to', '>=', date_from),
        ])
        missions = self.env['tarco.hr.mission'].search([
            ('state', 'in', ('draft', 'approved', 'done')),
            ('date_start', '<=', date_to),
            ('date_end', '>=', date_from),
            ('line_ids.employee_id', 'in', employees.ids),
        ])
        holidays = self.env['tarco.hr.public.holiday'].search([
            ('company_id', 'in', employees.company_id.ids),
            ('active', '=', True),
        ])
        existing = {
            (row.employee_id.id, row.work_date): row
            for row in self.search([
                ('employee_id', 'in', employees.ids),
                ('work_date', '>=', date_from),
                ('work_date', '<=', date_to),
            ])
        }
        day = date_from
        while day <= date_to:
            for employee in employees:
                if employee.tarco_hire_date and day < employee.tarco_hire_date:
                    continue
                if employee.tarco_resignation_date and day > employee.tarco_resignation_date:
                    continue
                vals = self._vals_for_day(
                    employee, day, punches_by_emp.get(employee.id, []), leaves, missions, holidays,
                )
                current = existing.get((employee.id, day))
                if current:
                    if not current.overtime_line_id:
                        current.write(vals)
                else:
                    existing[(employee.id, day)] = self.create(dict(vals, employee_id=employee.id, work_date=day))
            day += timedelta(days=1)
        return True

    def _vals_for_day(self, employee, day, punches, leaves, missions, holidays):
        shift = self.env['tarco.hr.shift'].shift_for(employee)
        holiday = holidays.filtered(
            lambda item: item.company_id == employee.company_id and item.observed_date == day
        )[:1]
        leave = leaves.filtered(
            lambda item: item.employee_id == employee and item.request_date_from <= day <= (item.request_date_to or item.request_date_from)
        )[:1]
        mission = missions.filtered(
            lambda item: employee in item.line_ids.employee_id and item.date_start <= day <= item.date_end
        )[:1]
        day_punches = []
        for punch in punches:
            local_in = self._as_local(employee, punch.check_in)
            if local_in and local_in.date() == day:
                day_punches.append(punch)
        check_in = min((punch.check_in for punch in day_punches), default=False)
        check_out = max((punch.check_out for punch in day_punches if punch.check_out), default=False)
        status = 'absent'
        if leave:
            status = 'leave'
        elif mission and not check_in:
            status = 'mission'
        elif holiday and not check_in:
            status = 'holiday'
        elif shift and shift.is_rest(day) and not check_in:
            status = 'rest'
        late_minutes = 0.0
        regular = 0.0
        overtime = 0.0
        rate = 0.0
        amount = 0.0
        if check_in:
            local_in = self._as_local(employee, check_in)
            in_hour = local_in.hour + local_in.minute / 60.0
            out_hour = False
            if check_out:
                local_out = self._as_local(employee, check_out)
                out_hour = local_out.hour + local_out.minute / 60.0
                out_hour += 24 * (local_out.date() - local_in.date()).days
            exempt = employee.tarco_exempt_late or (shift and employee in shift.exempt_employee_ids)
            start = shift.hour_from if shift else 8.0
            grace = (shift.grace_minutes if shift else 15) / 60.0
            end = shift.hour_to if shift else 16.0
            if shift and shift.overnight and end <= start:
                end += 24
            standard = shift.standard_hours if shift else 8.0
            ot_after = shift.ot_after if shift else 16.0
            if shift and shift.overnight and ot_after < start:
                ot_after += 24
            if not exempt and in_hour > start + grace:
                late_minutes = (in_hour - (start + grace)) * 60.0
            if not check_out:
                status = 'incomplete'
            else:
                regular = standard if out_hour >= end - 0.02 else min(standard, max(0.0, out_hour - max(in_hour, start)))
                if out_hour > ot_after:
                    overtime = out_hour - ot_after
                status = 'late' if late_minutes else 'present'
                if mission:
                    status = 'mission'
                if leave:
                    status = 'leave'
            rate = 2.0 if day.weekday() == 4 or holiday else 1.5
            if employee.tarco_overtime_mode != 'none' and overtime:
                amount = overtime * rate * tarco_hourly_wage(employee)
            elif employee.tarco_overtime_mode == 'none':
                amount = 0.0
        note = False
        if leave:
            note = leave.holiday_status_id.name
        elif mission:
            note = mission.place
        elif holiday:
            note = holiday.name
        return {
            'shift_id': shift.id if shift else False,
            'check_in': check_in,
            'check_out': check_out,
            'late_minutes': late_minutes,
            'regular_hours': regular,
            'overtime_hours': overtime,
            'overtime_rate': rate if overtime else 0.0,
            'overtime_amount': amount,
            'status': status,
            'leave_id': leave.id if leave else False,
            'mission_id': mission.id if mission else False,
            'holiday_id': holiday.id if holiday else False,
            'note': note,
        }

    def attendance_penalty_reason(self, kind):
        """Plain-language reason so HR can check the penalty against attendance."""
        self.ensure_one()
        employee = self.employee_id
        shift = self.shift_id
        start = shift.hour_from if shift else 8.0
        end = shift.hour_to if shift else 16.0
        grace = shift.grace_minutes if shift else 15
        late_after = start + (grace / 60.0)
        check_in = self._as_local(employee, self.check_in)
        check_out = self._as_local(employee, self.check_out)
        facts = {
            'kind': _('LATENESS') if kind == 'late' else _('ABSENCE'),
            'date': self.work_date.strftime('%A %d %b %Y') if self.work_date else '-',
            'emp': employee.name or '-',
            'code': employee.employee_code or '-',
            'dept': employee.department_id.name or _('no department'),
            'shift': (
                _('%(name)s, %(start)s–%(end)s') % {
                    'name': shift.name,
                    'start': format_clock(start),
                    'end': format_clock(end),
                }
                if shift else _('no shift assigned — treated as working day 08:00–16:00')
            ),
            'grace': grace,
            'late_after': format_clock(late_after),
            'cin': check_in.strftime('%H:%M') if check_in else _('none'),
            'cout': check_out.strftime('%H:%M') if check_out else _('none'),
            'late': int(round(self.late_minutes or 0.0)),
            'status': dict(self._fields['status']._description_selection(self.env)).get(self.status, self.status),
            'leave': self.leave_id.holiday_status_id.name if self.leave_id else _('no'),
            'mission': self.mission_id.place if self.mission_id else _('no'),
            'holiday': self.holiday_id.name if self.holiday_id else _('no'),
            'rest': _('yes') if shift and self.work_date and shift.is_rest(self.work_date) else _('no'),
        }
        if kind == 'late':
            return _(
                '%(kind)s on %(date)s — %(emp)s [%(code)s] checked in at %(cin)s, '
                '%(late)s minutes after the %(late_after)s grace limit.\n'
                'Department: %(dept)s.\n'
                'Shift: %(shift)s. Grace: %(grace)s minutes (late after %(late_after)s).\n'
                'Check-in: %(cin)s. Check-out: %(cout)s.\n'
                'Leave: %(leave)s. Mission: %(mission)s. Public holiday: %(holiday)s. Rest day: %(rest)s.\n'
                'Attendance day status: %(status)s. Late minutes on that day: %(late)s.\n'
                'Check Employees > Tarco HRIS > Attendance days for this employee and date.'
            ) % facts
        return _(
            '%(kind)s on %(date)s — %(emp)s [%(code)s] has no check-in on a working day.\n'
            'Department: %(dept)s.\n'
            'Shift: %(shift)s.\n'
            'Check-in: %(cin)s. Check-out: %(cout)s.\n'
            'Leave: %(leave)s. Mission: %(mission)s. Public holiday: %(holiday)s. Rest day: %(rest)s.\n'
            'Attendance day status: %(status)s. A working day with no punch is treated as absence.\n'
            'Check Employees > Tarco HRIS > Attendance days for this employee and date.'
        ) % facts

    @api.model
    def _cron_tarco_daily(self):
        today = fields.Date.context_today(self)
        self.sync_range(today - timedelta(days=2), today)
        self.env['hr.employee']._cron_tarco_contract_alerts()
        self.env['hr.employee']._cron_tarco_auto_statutory()
        self.env['hr.salary.rule']._tarco_ensure_rules()
        self.env['tarco.hr.advance']._cron_sync_paid()
