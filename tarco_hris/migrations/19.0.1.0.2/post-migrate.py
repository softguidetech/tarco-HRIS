# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref('tarco_hris.mail_template_tarco_interview', raise_if_not_found=False)
    if template:
        template.reset_template()
