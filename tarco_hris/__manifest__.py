# -*- coding: utf-8 -*-
{
    'name': 'Tarco HRIS',
    'version': '19.0.1.0.3',
    'category': 'Human Resources',
    'summary': 'Tarco Aviation HRIS: employee file, contracts, attendance, leave, missions, overtime, penalties, loans, recruitment and KPIs',
    'description': """
Tarco Aviation Services HRIS (TAS/HRM, 01 Jan 2024)
===================================================
One employee file keyed by employee code, employment contracts with a
89-day probation and renewal alerts, fingerprint attendance, leave balances
(21 or 30 days), missions, overtime, labor-law penalties, rewards, advances,
recruitment screening and administrative KPIs.
    """,
    'author': 'Tarco Aviation Services',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_holidays',
        'hr_recruitment',
        'hr_payroll',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/tarco_hris_security.xml',
        'data/tarco_hris_data.xml',
        'views/employee_views.xml',
        'views/operations_views.xml',
        'views/recruitment_kpi_views.xml',
        'views/wizard_views.xml',
        'report/reports.xml',
        'views/menus.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
