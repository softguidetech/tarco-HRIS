# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .tarco_common import tarco_daily_wage, tarco_post_adjustment


class TarcoHrReward(models.Model):
    _name = 'tarco.hr.reward'
    _description = 'Employee Reward'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reward_date desc, id desc'

    name = fields.Char(default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    section_id = fields.Many2one(related='employee_id.section_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    basic_wage = fields.Monetary(related='employee_id.tarco_basic_wage')
    cola = fields.Monetary(related='employee_id.tarco_cola')
    transport_allowance = fields.Monetary(related='employee_id.tarco_transport_allowance')
    housing_allowance = fields.Monetary(related='employee_id.tarco_housing_allowance')
    other_allowance = fields.Monetary(related='employee_id.tarco_other_allowance')
    gross_wage = fields.Monetary(related='employee_id.tarco_gross_wage')
    reason = fields.Char(required=True, tracking=True)
    mode = fields.Selection([('amount', 'Amount'), ('days', 'Days of wage')], default='amount', required=True)
    days = fields.Float()
    amount = fields.Monetary(compute='_compute_amount', store=True, readonly=False)
    reward_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=True)
    salary_attachment_id = fields.Many2one('hr.salary.attachment', copy=False)

    @api.depends('mode', 'days', 'employee_id')
    def _compute_amount(self):
        for reward in self:
            if reward.mode == 'days':
                reward.amount = (reward.days or 0.0) * tarco_daily_wage(reward.employee_id)
            else:
                reward.amount = reward.amount or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.reward') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for reward in self:
            if not reward.salary_attachment_id and reward.amount > 0:
                reward.salary_attachment_id = tarco_post_adjustment(
                    self.env, reward.employee_id, True, reward.amount,
                    _('Reward %s') % reward.reason, reward.reward_date,
                )
            reward.state = 'confirmed'
