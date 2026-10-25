# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    slips = env['hr.payslip'].search([('state', 'in', ('validated', 'paid'))])
    if slips:
        slips._tarco_apply_month_attachments()
