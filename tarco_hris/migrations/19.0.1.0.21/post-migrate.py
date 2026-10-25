# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    missions = env['tarco.hr.mission'].search([('state', 'in', ('draft', 'approved', 'done'))])
    if missions:
        missions._tarco_sync_calendar()
        missions._tarco_sync_attendance()
