# -*- coding: utf-8 -*-
from odoo import _, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    def _tarco_ensure_rules(self):
        """Add earning and deduction rules on every payroll structure."""
        deduction = self.env.ref('hr_payroll.DED', raise_if_not_found=False)
        allowance = self.env.ref('hr_payroll.ALW', raise_if_not_found=False)
        if not deduction or not allowance:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Payroll'),
                    'message': _('Payroll categories were not found.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        specs = [
            ('TARCO_EARNING', _('Tarco Earning'), allowance, "result = inputs['TARCO_EARNING'].amount\nresult_name = inputs['TARCO_EARNING'].name"),
            ('TARCO_DEDUCTION', _('Tarco Deduction'), deduction, "result = -inputs['TARCO_DEDUCTION'].amount\nresult_name = inputs['TARCO_DEDUCTION'].name"),
        ]
        created = 0
        structures = self.env['hr.payroll.structure'].sudo().search([])
        for structure in structures:
            for code, name, category, python in specs:
                if self.sudo().search_count([('struct_id', '=', structure.id), ('code', '=', code)]):
                    continue
                self.sudo().create({
                    'name': name,
                    'code': code,
                    'sequence': 175,
                    'category_id': category.id,
                    'struct_id': structure.id,
                    'condition_select': 'python',
                    'condition_python': "result = '%s' in inputs" % code,
                    'amount_select': 'code',
                    'amount_python_compute': python,
                })
                created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payroll'),
                'message': _('Checked %s salary structures. Added %s Tarco rules.') % (len(structures), created),
                'type': 'success',
                'sticky': False,
            },
        }
