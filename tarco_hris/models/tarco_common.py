# -*- coding: utf-8 -*-
import re
from datetime import date, datetime

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


def tarco_eos_gratuity(wage, years_float):
    """Sudan Labour Act 1997 Art. 53: 0.5 month/year for the first 5 years, 1 month/year after."""
    years = max(float(years_float or 0.0), 0.0)
    first = min(years, 5.0)
    extra = max(years - 5.0, 0.0)
    return (wage or 0.0) * (first * 0.5 + extra * 1.0)


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


_COL_WIDTH = {
    'date': 9, 'from': 9, 'to': 9, 'due': 8, 'observed': 9,
    'original date': 9, 'moved to': 8, 'hire date': 9, 'rehire date': 9,
    'contract end': 9, 'probation end': 9, 'resignation': 9,
    'code': 9, 'number': 8, 'rank': 7,
    'name': 14, 'department': 12, 'section': 10, 'job': 10,
    'check in': 7, 'check out': 7, 'in': 6, 'out': 6,
    'status': 8, 'type': 10, 'currency': 7,
    'late minutes': 7, 'late': 6, 'overtime': 7, 'ot': 6,
    'days': 6, 'hours': 6, 'years': 6, 'months': 6,
    'amount': 8, 'cost': 8, 'total': 8, 'paid': 8, 'remaining': 8,
    'percent': 7, 'score': 7, 'repeat': 6, 'count': 6,
    'headcount': 8, 'present': 7, 'leave': 7, 'absent': 7, 'mission': 8,
    'working days': 8, 'attended': 8, 'hires': 7, 'resignations': 9,
    'active headcount': 9, 'turnover %': 8, 'monthly gross': 9,
    'note': 14, 'reason': 14, 'comment': 14, 'employees': 16,
    'place': 11, 'advance': 9, 'rule': 12, 'question': 14,
    'hours %': 7, 'quality %': 8, 'overall %': 8, 'average %': 8,
    'hours x 1.5': 8, 'hours x 2': 8, 'deduction': 9, 'service': 10,
}

_NUM_HEADERS = {
    'days', 'hours', 'years', 'months', 'amount', 'cost', 'total', 'paid',
    'remaining', 'percent', 'score', 'repeat', 'count', 'late minutes', 'late',
    'overtime', 'ot', 'headcount', 'present', 'leave', 'absent', 'mission',
    'working days', 'attended', 'hires', 'resignations', 'active headcount',
    'turnover %', 'monthly gross', 'hours %', 'quality %', 'overall %',
    'average %', 'hours x 1.5', 'hours x 2',
}


def fmt_date(value):
    if value in (None, False, ''):
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%d %b %Y')
    if isinstance(value, date):
        return value.strftime('%d %b %Y')
    text = str(value).strip()
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', text)
    if match:
        try:
            return fields.Date.from_string(match.group(1)).strftime('%d %b %Y')
        except Exception:
            return text
    return text


def fmt_time(value):
    if not value:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime('%H:%M')
    text = str(value)
    match = re.search(r'(\d{2}:\d{2})', text)
    return match.group(1) if match else text


def _cell_text(value):
    if value in (None, False, ''):
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%d %b %Y %H:%M')
    if isinstance(value, date):
        return value.strftime('%d %b %Y')
    text = str(value).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return fmt_date(text)
    if re.match(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}', text):
        return '%s %s' % (fmt_date(text), fmt_time(text))
    return text


def _header_key(header):
    text = str(header or '')
    return text.split('(')[0].strip().lower()


def _col_widths(headers):
    raw = []
    for header in headers:
        key = _header_key(header)
        raw.append(_COL_WIDTH.get(key, 10))
    total = sum(raw) or 1
    return [max(5, round(width * 100.0 / total, 1)) for width in raw]


def html_table(headers, rows):
    widths = _col_widths(headers)
    colgroup = ''.join('<col style="width:%s%%"/>' % width for width in widths)
    head_cells = []
    num_flags = []
    for header in headers:
        numeric = _header_key(header) in _NUM_HEADERS
        num_flags.append(numeric)
        css = ' class="num"' if numeric else ''
        head_cells.append('<th%s>%s</th>' % (css, escape(header)))
    body = []
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            numeric = index < len(num_flags) and num_flags[index]
            css = ' class="num"' if numeric else ''
            cells.append('<td%s>%s</td>' % (css, escape(_cell_text(value))))
        body.append('<tr>%s</tr>' % ''.join(cells))
    return (
        '<table class="o_tarco_report_table">'
        '<colgroup>%s</colgroup>'
        '<thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
    ) % (colgroup, ''.join(head_cells), ''.join(body))


def markup_sections(sections):
    parts = []
    for title, headers, rows in sections:
        parts.append('<h3 class="o_tarco_section">%s</h3>' % escape(title))
        if not rows:
            parts.append('<p class="o_tarco_empty">%s</p>' % escape(_('No records.')))
        else:
            parts.append(html_table(headers, rows))
    return Markup(''.join(parts))


def money(amount):
    return '%.2f' % (amount or 0.0)


def format_clock(value):
    if value is None or value is False:
        return '-'
    total = int(round(float(value) * 60))
    hours, minutes = divmod(abs(total), 60)
    return '%02d:%02d' % (hours, minutes)


def tarco_hierarchy_read(model, domain, specification, parent_field, order=None):
    """Return every record in the domain plus ancestors and descendants.

    The standard hierarchy view only loads roots and one opened branch. Tarco
    HRIS needs the full pyramid on the first screen.
    """
    if parent_field not in specification:
        specification = dict(specification)
        specification[parent_field] = {'fields': {'display_name': {}}}
    records = model.search(domain, order=order)
    if not records:
        return []
    seen = set(records.ids)
    to_visit = records
    while to_visit:
        children = model.search([
            (parent_field, 'in', to_visit.ids),
            ('id', 'not in', list(seen)),
        ], order=order)
        records |= children
        seen.update(children.ids)
        to_visit = children
    ancestors = records.mapped(parent_field)
    while ancestors:
        new = ancestors.filtered(lambda rec: rec.id not in seen)
        if not new:
            break
        records |= new
        seen.update(new.ids)
        ancestors = new.mapped(parent_field)
    return records.web_read(specification)
