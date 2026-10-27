# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape


class TarcoHrMission(models.Model):
    _name = 'tarco.hr.mission'
    _description = 'Business Mission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(default='/', copy=False)
    place = fields.Char(string='Place', required=True, tracking=True)
    purpose = fields.Text(required=True)
    date_start = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    date_end = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    number_of_days = fields.Integer(compute='_compute_number_of_days', store=True)
    hour_start = fields.Float(string='Departure time')
    hour_end = fields.Float(string='End time')
    per_diem = fields.Monetary(string='Cost per person per day', tracking=True)
    cost = fields.Monetary(compute='_compute_cost', store=True, string='Total cost')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mission currency', required=True, tracking=True,
        default=lambda self: self.env.company.currency_id,
        help='Every amount of the mission (daily cost, employee amounts, total) is in this currency.')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company currency')
    cost_company_currency = fields.Monetary(
        compute='_compute_cost_company_currency', store=True, currency_field='company_currency_id',
        string='Total cost in company currency',
        help='Total cost converted at the rate of the mission start date. Used to add up missions in reports.')
    line_ids = fields.One2many('tarco.hr.mission.line', 'mission_id', string='Employee lines')
    employee_ids = fields.Many2many(
        'hr.employee', compute='_compute_employee_ids', search='_search_employee_ids',
        string='Employees')
    employee_count = fields.Integer(compute='_compute_cost', store=True)
    total_hours = fields.Float(compute='_compute_cost', store=True, string='Total hours')
    calendar_event_count = fields.Integer(compute='_compute_calendar_event_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.depends('date_start', 'date_end')
    def _compute_number_of_days(self):
        for mission in self:
            if mission.date_start and mission.date_end and mission.date_end >= mission.date_start:
                mission.number_of_days = (mission.date_end - mission.date_start).days + 1
            else:
                mission.number_of_days = 0

    @api.depends('line_ids.employee_id')
    def _compute_employee_ids(self):
        for mission in self:
            mission.employee_ids = mission.line_ids.employee_id

    def _search_employee_ids(self, operator, value):
        return [('line_ids.employee_id', operator, value)]

    @api.depends('line_ids.calendar_event_id')
    def _compute_calendar_event_count(self):
        for mission in self:
            mission.calendar_event_count = len(mission.line_ids.calendar_event_id)

    @api.depends('per_diem', 'number_of_days', 'line_ids', 'hour_start', 'hour_end')
    def _compute_cost(self):
        for mission in self:
            count = len(mission.line_ids)
            mission.employee_count = count
            hours = (mission.hour_end or 0.0) - (mission.hour_start or 0.0)
            if hours < 0:
                hours += 24
            mission.total_hours = hours * (mission.number_of_days or 0) * count
            mission.cost = (mission.per_diem or 0.0) * (mission.number_of_days or 0) * count

    @api.depends('cost', 'currency_id', 'company_id', 'date_start')
    def _compute_cost_company_currency(self):
        for mission in self:
            company_currency = mission.company_id.currency_id
            if not mission.currency_id or mission.currency_id == company_currency:
                mission.cost_company_currency = mission.cost
            else:
                mission.cost_company_currency = mission.currency_id._convert(
                    mission.cost, company_currency, mission.company_id,
                    mission.date_start or fields.Date.context_today(mission))

    def action_print(self):
        return self.env.ref('tarco_hris.action_report_mission').report_action(self)

    def action_open_calendar(self):
        self._tarco_sync_calendar()
        events = self.mapped('line_ids.calendar_event_id')
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Mission calendar'),
            'res_model': 'calendar.event',
            'view_mode': 'calendar,list,form',
            'domain': [('id', 'in', events.ids)],
            'context': {'default_mode': 'month'},
        }
        if len(events) == 1:
            action.update(res_id=events.id, view_mode='form,calendar,list')
        return action

    @api.constrains('hour_start', 'hour_end')
    def _check_hours(self):
        for mission in self:
            for label, value in (('departure', mission.hour_start), ('end', mission.hour_end)):
                if value and not 0 <= value < 24:
                    raise ValidationError(_('Mission %s time must be inside 24 hours.') % label)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.mission') or '/'
        missions = super().create(vals_list)
        missions._tarco_sync_calendar()
        missions._tarco_sync_attendance()
        return missions

    def write(self, vals):
        track = {'date_start', 'date_end', 'hour_start', 'hour_end', 'place', 'purpose', 'state', 'line_ids'}
        old_ranges = []
        if set(vals) & {'date_start', 'date_end', 'line_ids', 'state'}:
            old_ranges = [
                (mission.date_start, mission.date_end, mission.line_ids.employee_id)
                for mission in self
            ]
        result = super().write(vals)
        if set(vals) & track:
            self._tarco_sync_calendar()
            self._tarco_sync_attendance(old_ranges)
        return result

    def unlink(self):
        ranges = [
            (mission.date_start, mission.date_end, mission.line_ids.employee_id)
            for mission in self
        ]
        events = self.mapped('line_ids.calendar_event_id')
        result = super().unlink()
        events.sudo().exists().unlink()
        self._tarco_resync_ranges(ranges)
        return result

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def _float_time(self, value):
        hours = int(value or 0)
        minutes = int(round(((value or 0) - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes = 0
        return time(min(max(hours, 0), 23), min(max(minutes, 0), 59))

    def _event_bounds(self):
        self.ensure_one()
        tz_name = (
            self.env.user.tz
            or (self.company_id.resource_calendar_id.tz if self.company_id.resource_calendar_id else None)
            or 'Africa/Khartoum'
        )
        zone = timezone(tz_name)
        if self.hour_start or self.hour_end:
            start_local = datetime.combine(self.date_start, self._float_time(self.hour_start or 8.0))
            end_local = datetime.combine(self.date_end, self._float_time(self.hour_end or 16.0))
            if end_local <= start_local:
                end_local += timedelta(days=1)
            allday = False
        else:
            start_local = datetime.combine(self.date_start, time.min)
            end_local = datetime.combine(self.date_end, time.max)
            allday = True
        start = zone.localize(start_local).astimezone(utc).replace(tzinfo=None)
        stop = zone.localize(end_local).astimezone(utc).replace(tzinfo=None)
        return start, stop, allday

    def _tarco_sync_calendar(self):
        for mission in self:
            if mission.state == 'cancel' or not mission.date_start or not mission.date_end:
                mission.line_ids._tarco_unlink_calendar()
            else:
                mission.line_ids._tarco_sync_calendar()

    def _tarco_sync_attendance(self, old_ranges=None):
        ranges = [
            (mission.date_start, mission.date_end, mission.line_ids.employee_id)
            for mission in self
        ]
        if old_ranges:
            ranges.extend(old_ranges)
        self._tarco_resync_ranges(ranges)

    @api.model
    def _tarco_resync_ranges(self, ranges):
        Day = self.env['tarco.hr.attendance.day']
        seen = set()
        for date_from, date_to, employees in ranges:
            if not date_from or not date_to or not employees:
                continue
            key = (date_from, date_to, tuple(employees.ids))
            if key in seen:
                continue
            seen.add(key)
            Day.sync_range(date_from, date_to, employees)


class TarcoHrMissionLine(models.Model):
    _name = 'tarco.hr.mission.line'
    _description = 'Mission Employee'

    mission_id = fields.Many2one('tarco.hr.mission', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='mission_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id')
    job_id = fields.Many2one(related='employee_id.job_id')
    currency_id = fields.Many2one(related='mission_id.currency_id')
    amount = fields.Monetary(compute='_compute_amount', string='Amount')
    date_start = fields.Date(related='mission_id.date_start', store=True)
    date_end = fields.Date(related='mission_id.date_end', store=True)
    place = fields.Char(related='mission_id.place')
    state = fields.Selection(related='mission_id.state', store=True)
    calendar_event_id = fields.Many2one(
        'calendar.event', string='Calendar', copy=False, ondelete='set null')

    @api.depends('mission_id.per_diem', 'mission_id.number_of_days')
    def _compute_amount(self):
        for line in self:
            line.amount = (line.mission_id.per_diem or 0.0) * (line.mission_id.number_of_days or 0)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get('tarco_syncing_mission'):
            lines._tarco_sync_calendar()
            lines.mapped('mission_id')._tarco_sync_attendance()
        return lines

    def write(self, vals):
        old_employees = self.mapped('employee_id') if 'employee_id' in vals else self.env['hr.employee']
        result = super().write(vals)
        if set(vals) - {'calendar_event_id'} and not self.env.context.get('tarco_syncing_mission'):
            if 'employee_id' in vals:
                self._tarco_unlink_calendar()
            self._tarco_sync_calendar()
            self.mapped('mission_id')._tarco_sync_attendance([
                (line.mission_id.date_start, line.mission_id.date_end, old_employees)
                for line in self
                if old_employees
            ])
        return result

    def unlink(self):
        events = self.mapped('calendar_event_id')
        ranges = [
            (line.mission_id.date_start, line.mission_id.date_end, line.employee_id)
            for line in self
        ]
        result = super().unlink()
        events.sudo().exists().unlink()
        if not self.env.context.get('tarco_syncing_mission'):
            self.env['tarco.hr.mission']._tarco_resync_ranges(ranges)
        return result

    def _calendar_partner(self):
        self.ensure_one()
        employee = self.employee_id
        partner = self.env['res.partner']
        if 'work_contact_id' in employee._fields:
            partner = employee.work_contact_id
        if not partner and 'user_partner_id' in employee._fields:
            partner = employee.user_partner_id
        if not partner:
            partner = employee.user_id.partner_id
        return partner

    def _tarco_event_name(self):
        self.ensure_one()
        mission = self.mission_id
        title = _('Mission: %s — %s') % (mission.place or mission.name, self.employee_id.name)
        if mission.state == 'draft':
            title = _('Draft mission: %s — %s') % (mission.place or mission.name, self.employee_id.name)
        return title

    def _tarco_sync_calendar(self):
        Event = self.env['calendar.event'].sudo().with_context(
            no_mail_to_attendees=True,
            dont_notify=True,
            mail_create_nolog=True,
        )
        for line in self:
            mission = line.mission_id
            if (
                not mission
                or mission.state == 'cancel'
                or not mission.date_start
                or not mission.date_end
                or not line.employee_id
            ):
                line._tarco_unlink_calendar()
                continue
            start, stop, allday = mission._event_bounds()
            partner = line._calendar_partner()
            partners = partner | self.env.user.partner_id
            vals = {
                'name': line._tarco_event_name(),
                'start': start,
                'stop': stop,
                'allday': allday,
                'location': mission.place or '',
                'description': '<p>%s</p>' % html_escape(mission.purpose or ''),
                'user_id': (line.employee_id.user_id or self.env.user).id,
                'partner_ids': [Command.set(partners.ids)],
                'res_model_id': self.env['ir.model']._get_id(mission._name),
                'res_id': mission.id,
                'privacy': 'public',
                'show_as': 'busy' if mission.state in ('approved', 'done') else 'free',
            }
            if getattr(mission, 'tarco_is_demo', False):
                vals['tarco_is_demo'] = True
            try:
                if line.calendar_event_id:
                    line.calendar_event_id.with_context(
                        no_mail_to_attendees=True, dont_notify=True,
                    ).write(vals)
                else:
                    line.with_context(tarco_syncing_mission=True).calendar_event_id = Event.create(vals)
            except UserError:
                raise
            except Exception as error:
                raise UserError(
                    _('Could not book %(employee)s on the calendar: %(error)s') % {
                        'employee': line.employee_id.name,
                        'error': error,
                    }
                ) from error

    def _tarco_unlink_calendar(self):
        events = self.mapped('calendar_event_id')
        self.with_context(tarco_syncing_mission=True).write({'calendar_event_id': False})
        events.sudo().exists().unlink()

    _mission_employee_unique = models.Constraint(
        'unique(mission_id, employee_id)',
        'An employee can be added to a mission only once.',
    )
