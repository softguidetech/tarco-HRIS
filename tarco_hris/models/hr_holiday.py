# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import api, fields, models


class TarcoHrPublicHoliday(models.Model):
    _name = 'tarco.hr.public.holiday'
    _description = 'Official Holiday'
    _order = 'holiday_date'

    name = fields.Char(required=True)
    holiday_date = fields.Date(required=True, string='Original date')
    moved_date = fields.Date(string='Moved to')
    observed_date = fields.Date(compute='_compute_observed_date', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    calendar_leave_id = fields.Many2one('resource.calendar.leaves', copy=False)
    note = fields.Char()

    @api.depends('holiday_date', 'moved_date')
    def _compute_observed_date(self):
        for holiday in self:
            holiday.observed_date = holiday.moved_date or holiday.holiday_date

    def action_publish(self):
        for holiday in self:
            observed = holiday.observed_date
            if not observed:
                continue
            vals = {
                'name': holiday.name,
                'company_id': holiday.company_id.id,
                'date_from': datetime.combine(observed, time.min),
                'date_to': datetime.combine(observed, time.max),
                'time_type': 'leave',
            }
            if holiday.calendar_leave_id:
                holiday.calendar_leave_id.write(vals)
            else:
                holiday.calendar_leave_id = self.env['resource.calendar.leaves'].create(vals)
        return True
