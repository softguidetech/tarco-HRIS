# -*- coding: utf-8 -*-
from odoo import fields, models


class TarcoHrEmployeeReportWizard(models.TransientModel):
    _name = 'tarco.hr.employee.report.wizard'
    _description = 'Employee File Report'

    employee_id = fields.Many2one('hr.employee', required=True)
    show_personal = fields.Boolean(default=True, string='Personal data')
    show_job = fields.Boolean(default=True, string='Job')
    show_salary = fields.Boolean(default=True, string='Salary')
    show_documents = fields.Boolean(default=True, string='Documents')
    show_custody = fields.Boolean(default=True, string='Custody and work requirements')
    show_contract = fields.Boolean(default=True, string='Contract')
    show_leave = fields.Boolean(default=True, string='Leave')
    show_attendance = fields.Boolean(default=False, string='Attendance')
    show_penalty = fields.Boolean(default=False, string='Penalties')
    show_reward = fields.Boolean(default=False, string='Rewards')
    show_advance = fields.Boolean(default=False, string='Advances')
    show_kpi = fields.Boolean(default=False, string='KPIs')

    def action_print(self):
        return self.env.ref('tarco_hris.action_report_employee_file').report_action(self)
