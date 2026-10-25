# -*- coding: utf-8 -*-
from datetime import datetime, time

from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TarcoHrPublicHoliday(models.Model):
    _name = 'tarco.hr.public.holiday'
    _description = 'Official Holiday'
    _order = 'holiday_date'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    holiday_date = fields.Date(required=True, string='Original date', tracking=True)
    moved_date = fields.Date(string='Moved to', tracking=True)
    observed_date = fields.Date(compute='_compute_observed_date', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    calendar_leave_id = fields.Many2one('resource.calendar.leaves', copy=False, string='Calendar time off')
    note = fields.Char()
    state = fields.Selection(
        [('draft', 'Draft'), ('published', 'Published')],
        compute='_compute_state',
        store=True,
        default='draft',
        tracking=True,
    )

    @api.depends('holiday_date', 'moved_date')
    def _compute_observed_date(self):
        for holiday in self:
            holiday.observed_date = holiday.moved_date or holiday.holiday_date

    @api.depends('calendar_leave_id')
    def _compute_state(self):
        for holiday in self:
            holiday.state = 'published' if holiday.calendar_leave_id else 'draft'

    def _calendar_bounds(self, day):
        self.ensure_one()
        calendar = self.company_id.resource_calendar_id
        tz_name = (calendar.tz if calendar else None) or self.env.user.tz or 'Africa/Khartoum'
        zone = timezone(tz_name)
        start = zone.localize(datetime.combine(day, time.min)).astimezone(utc).replace(tzinfo=None)
        end = zone.localize(datetime.combine(day, time.max)).astimezone(utc).replace(tzinfo=None)
        return start, end

    def action_publish(self):
        Leaves = self.env['resource.calendar.leaves'].sudo()
        for holiday in self:
            observed = holiday.observed_date
            if not observed:
                raise UserError(_('Set the original date (or Moved to) before publishing %s.') % holiday.name)
            date_from, date_to = holiday._calendar_bounds(observed)
            vals = {
                'name': holiday.name,
                'date_from': date_from,
                'date_to': date_to,
                'time_type': 'leave',
                'calendar_id': False,
            }
            calendar = holiday.company_id.resource_calendar_id
            if calendar:
                vals['calendar_id'] = calendar.id
            try:
                if holiday.calendar_leave_id:
                    holiday.calendar_leave_id.sudo().write(vals)
                else:
                    holiday.calendar_leave_id = Leaves.create(vals)
            except Exception as error:
                raise UserError(_('Could not publish %s on the calendar: %s') % (holiday.name, error)) from error
            if not holiday.calendar_leave_id:
                raise UserError(_('Could not publish %s on the calendar.') % holiday.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Holiday published on the working calendar.'),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_unpublish(self):
        for holiday in self:
            leave = holiday.calendar_leave_id.sudo()
            holiday.calendar_leave_id = False
            if leave:
                leave.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Holiday removed from the working calendar.'),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
