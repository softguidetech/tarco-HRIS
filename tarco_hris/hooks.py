# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta


def post_init_hook(env):
    """Copy existing hire dates and make sure payroll structures know Tarco inputs."""
    env['hr.salary.rule'].sudo()._tarco_ensure_rules()
    employees = env['hr.employee'].sudo().search([])
    for employee in employees:
        hire = employee.contract_date_start
        if hire and not employee.tarco_hire_date:
            employee.write({
                'tarco_hire_date': hire,
                'tarco_trial_date_end': hire + timedelta(days=89),
                'tarco_renewal_date': hire + relativedelta(years=1),
            })
            employee._tarco_push_contract()
