# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TarcoHrShift(models.Model):
    _name = 'tarco.hr.shift'
    _description = 'Work Shift'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    hour_from = fields.Float(string='Start', default=8.0, required=True)
    hour_to = fields.Float(string='End', default=16.0, required=True)
    overnight = fields.Boolean(string='Crosses midnight')
    grace_minutes = fields.Integer(string='Lateness starts after (minutes)', default=15)
    standard_hours = fields.Float(string='Paid day hours', default=8.0, required=True)
    ot_after = fields.Float(string='Overtime starts at', default=16.0, required=True)
    rest_monday = fields.Boolean()
    rest_tuesday = fields.Boolean()
    rest_wednesday = fields.Boolean()
    rest_thursday = fields.Boolean()
    rest_friday = fields.Boolean(string='Friday rest', default=True)
    rest_saturday = fields.Boolean()
    rest_sunday = fields.Boolean()
    department_ids = fields.Many2many('hr.department', string='Departments')
    job_ids = fields.Many2many('hr.job', string='Job positions')
    employee_ids = fields.Many2many('hr.employee', 'tarco_shift_employee_rel', string='Specific employees')
    exempt_employee_ids = fields.Many2many(
        'hr.employee', 'tarco_shift_exempt_rel', string='Exempt from lateness',
    )

    def is_rest(self, day):
        self.ensure_one()
        flags = [
            self.rest_monday, self.rest_tuesday, self.rest_wednesday, self.rest_thursday,
            self.rest_friday, self.rest_saturday, self.rest_sunday,
        ]
        return bool(flags[day.weekday()])

    @api.model
    def shift_for(self, employee):
        if employee.tarco_shift_id:
            return employee.tarco_shift_id
        shifts = self.search([('company_id', '=', employee.company_id.id), ('active', '=', True)])
        personal = shifts.filtered(lambda shift: employee in shift.employee_ids)
        if personal:
            return personal[0]
        grouped = shifts.filtered(
            lambda shift: employee.department_id in shift.department_ids or employee.job_id in shift.job_ids
        )
        if grouped:
            return grouped[0]
        generic = shifts.filtered(lambda shift: not shift.employee_ids and not shift.department_ids and not shift.job_ids)
        return generic[:1]
