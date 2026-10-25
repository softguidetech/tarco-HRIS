# -*- coding: utf-8 -*-
from odoo import fields, models


class TarcoHrDocument(models.Model):
    _name = 'tarco.hr.document'
    _description = 'Employee HR Document'
    _order = 'employee_id, group_type, kind'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    group_type = fields.Selection([
        ('hiring', 'Hiring document'),
        ('audit', 'Audit document'),
    ], required=True, default='hiring')
    kind = fields.Selection([
        ('birth_certificate', 'Birth certificate'),
        ('qualification', 'Qualification'),
        ('experience', 'Experience certificates'),
        ('photo', 'Photograph'),
        ('national_id', 'National ID'),
        ('application', 'Employment application'),
        ('contract', 'Employment contract'),
        ('job_description', 'Job description'),
        ('regulations', 'Acknowledgement of work regulations'),
        ('other', 'Other'),
    ], required=True, default='other')
    datas = fields.Binary(string='File', attachment=True)
    datas_fname = fields.Char(string='Filename')
    received = fields.Boolean(string='Received')
    document_date = fields.Date(default=fields.Date.context_today)
    note = fields.Char()
