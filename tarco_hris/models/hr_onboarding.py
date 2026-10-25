# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.tools import format_date


def plaintext2html_inline(text):
    return Markup('<br/>').join(text.splitlines())


class TarcoHrOnboarding(models.Model):
    _name = 'tarco.hr.onboarding'
    _description = 'Hiring Onboarding Notice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    need_training = fields.Boolean(string='Induction training')
    need_safety = fields.Boolean(string='Safety briefing')
    need_computer = fields.Boolean(string='Computer')
    need_library = fields.Boolean(string='Library tools')
    need_uniform = fields.Boolean(string='Uniform')
    need_warehouse = fields.Boolean(string='Warehouse issue')
    note = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('sent', 'Sent')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.onboarding') or '/'
        return super().create(vals_list)

    def _tasks(self):
        self.ensure_one()
        labels = []
        for field_name, label in [
            ('need_training', _('Induction training')),
            ('need_safety', _('Safety briefing')),
            ('need_computer', _('Prepare a computer')),
            ('need_library', _('Library tools')),
            ('need_uniform', _('Uniform')),
            ('need_warehouse', _('Issue supplies from the warehouse')),
        ]:
            if self[field_name]:
                labels.append(label)
        return labels

    def _message_body(self):
        self.ensure_one()
        employee = self.employee_id.sudo()
        details = [
            (_('Job position'), employee.job_id.name),
            (_('Department'), employee.department_id.name),
            (_('Start date'), employee.tarco_hire_date and format_date(self.env, employee.tarco_hire_date)),
            (_('Manager'), employee.parent_id.name),
        ]
        body = Markup('<p>%s</p><p>%s</p>') % (
            _('Hello,'),
            _('We are happy to welcome %s to the team. Please prepare the following before the first working day:')
            % employee.name,
        )
        body += Markup('<ul>%s</ul>') % Markup().join(
            Markup('<li>%s</li>') % task for task in (self._tasks() or [_('General onboarding')]))
        lines = [Markup('%s: <b>%s</b>') % (label, value) for label, value in details if value]
        if lines:
            body += Markup('<p>%s</p>') % Markup('<br/>').join(lines)
        if self.note:
            body += Markup('<p>%s<br/>%s</p>') % (_('Additional notes:'), plaintext2html_inline(self.note))
        body += Markup('<p>%s<br/>%s</p>') % (_('Thank you,'), _('Human Resources'))
        return body

    def action_send(self):
        for notice in self:
            body = notice._message_body()
            notice.message_post(body=body, subtype_xmlid='mail.mt_comment')
            manager = notice.employee_id.parent_id
            user = manager.user_id or notice.employee_id.version_id.hr_responsible_id
            if user:
                notice.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Onboarding for %s') % notice.employee_id.name,
                    note=body,
                    user_id=user.id,
                )
            emails = {address for address in (manager.work_email, notice.employee_id.work_email) if address}
            if emails:
                self.env['mail.mail'].sudo().create({
                    'subject': _('Welcome %s - onboarding arrangements') % notice.employee_id.name,
                    'email_to': ','.join(emails),
                    'body_html': body,
                }).send()
            notice.state = 'sent'
