# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import _, fields
from odoo.exceptions import UserError

QUALIFICATION_SELECTION = [
    ('basic', 'Basic / أساسي'),
    ('secondary', 'Secondary / ثانوي'),
    ('diploma', 'Diploma / دبلوم'),
    ('bachelor', 'Bachelor / بكالوريوس'),
    ('higher_diploma', 'Higher Diploma / دبلوم عالي'),
    ('master', 'Master / ماجستير'),
    ('doctor', 'Doctorate / دكتوراه'),
    ('graduate', 'Graduate'),
    ('other', 'Other'),
]

RELIGION_SELECTION = [
    ('muslim', 'Muslim'),
    ('christian', 'Christian'),
    ('other', 'Other'),
]


def tarco_gross(employee):
    return (
        (employee.tarco_basic_wage or 0.0)
        + (employee.tarco_cola or 0.0)
        + (employee.tarco_transport_allowance or 0.0)
        + (employee.tarco_housing_allowance or 0.0)
        + (employee.tarco_other_allowance or 0.0)
    ) or (employee.sudo().wage or 0.0)


def tarco_daily_wage(employee):
    gross = tarco_gross(employee)
    return gross / 30.0 if gross else 0.0


def tarco_hourly_wage(employee):
    return tarco_daily_wage(employee) / 8.0


def tarco_post_adjustment(env, employee, earning, amount, description, date_start,
                          duration_type='one', total_amount=None):
    """Create a payroll salary adjustment. Earnings are added, other amounts deducted."""
    amount = float(amount or 0.0)
    if amount <= 0 or not employee:
        return env['hr.salary.attachment']
    xmlid = 'tarco_hris.input_tarco_earning' if earning else 'tarco_hris.input_tarco_deduction'
    input_type = env.ref(xmlid, raise_if_not_found=False)
    if not input_type:
        raise UserError(_('Tarco payroll input types are missing. Update the Tarco HRIS module.'))
    vals = {
        'employee_ids': [(6, 0, employee.ids)],
        'company_id': employee.company_id.id,
        'other_input_type_id': input_type.id,
        'description': description,
        'monthly_amount': amount,
        'date_start': date_start or fields.Date.context_today(employee),
        'duration_type': duration_type,
    }
    if duration_type == 'limited':
        vals['total_amount'] = total_amount or amount
    return env['hr.salary.attachment'].sudo().create(vals)


def html_table(headers, rows):
    head = ''.join('<th>%s</th>' % escape(header) for header in headers)
    body = []
    for row in rows:
        cells = ''.join('<td>%s</td>' % escape('' if value is None else str(value)) for value in row)
        body.append('<tr>%s</tr>' % cells)
    return (
        '<table class="table table-sm table-bordered">'
        '<thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
    ) % (head, ''.join(body))


def markup_sections(sections):
    parts = []
    for title, headers, rows in sections:
        parts.append('<h3>%s</h3>' % escape(title))
        if not rows:
            parts.append('<p>%s</p>' % escape(_('No records.')))
        else:
            parts.append(html_table(headers, rows))
    return Markup(''.join(parts))


def money(amount):
    return '%.2f' % (amount or 0.0)
