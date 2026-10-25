# -*- coding: utf-8 -*-
from odoo import fields, models


class TarcoHrAdvanceLine(models.Model):
    _name = 'tarco.hr.advance.line'
    _description = 'Advance Installment'
    _order = 'due_date, sequence'

    advance_id = fields.Many2one('tarco.hr.advance', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='advance_id.employee_id', store=True)
    company_id = fields.Many2one(related='advance_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    sequence = fields.Integer()
    due_date = fields.Date(required=True)
    amount = fields.Monetary(required=True)
    state = fields.Selection([('due', 'Due'), ('paid', 'Paid')], default='due')
