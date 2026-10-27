# -*- coding: utf-8 -*-
from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        res = super().action_payslip_done()
        self._tarco_apply_month_attachments()
        return res

    def action_payslip_paid(self):
        res = super().action_payslip_paid()
        self._tarco_apply_month_attachments()
        return res

    def write(self, vals):
        if vals.get('state') == 'paid':
            self = self.with_context(tarco_skip_attachment_payment=True)
        return super().write(vals)

    def _record_attachment_payment(self, attachments, slip_lines):
        if self.env.context.get('tarco_skip_attachment_payment'):
            return
        return super()._record_attachment_payment(attachments, slip_lines)

    def _tarco_apply_month_attachments(self):
        """Record this payslip against salary adjustments and close one-time items."""
        for slip in self.filtered(lambda rec: rec.state in ('validated', 'paid') and rec.employee_id):
            month_start = slip.date_from.replace(day=1)
            month_ones = self.env['hr.salary.attachment'].search([
                ('employee_ids', 'in', slip.employee_id.ids),
                ('company_id', '=', slip.company_id.id),
                ('state', '=', 'open'),
                ('duration_type', '=', 'one'),
                ('date_start', '>=', month_start),
                ('date_start', '<=', slip.date_to),
            ])
            attachments = (slip.salary_attachment_ids | month_ones).filtered(lambda rec: rec.state == 'open')
            if not attachments:
                continue
            for code, group in attachments.grouped(lambda rec: rec.other_input_type_id.code).items():
                salary_lines = slip.line_ids.filtered(lambda line: line.code == code)
                if group and salary_lines:
                    slip.with_context(tarco_skip_attachment_payment=False)._record_attachment_payment(
                        group, salary_lines,
                    )
            leftovers = attachments.filtered(lambda rec: rec.state == 'open' and rec.duration_type == 'one')
            for attachment in leftovers:
                vals = {
                    'state': 'close',
                    'date_end': slip.date_to,
                }
                if attachment.paid_amount < attachment.monthly_amount:
                    vals['paid_amount'] = attachment.monthly_amount
                attachment.write(vals)
        self.env['tarco.hr.advance']._cron_sync_paid()
        self.env['tarco.hr.eos']._sync_paid_from_attachments()
