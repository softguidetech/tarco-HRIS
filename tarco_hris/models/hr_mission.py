# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TarcoHrMission(models.Model):
    _name = 'tarco.hr.mission'
    _description = 'Business Mission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(default='/', copy=False)
    place = fields.Char(string='Place', required=True, tracking=True)
    purpose = fields.Text(required=True)
    date_start = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    date_end = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    number_of_days = fields.Integer(compute='_compute_number_of_days', store=True)
    hour_start = fields.Float(string='Departure time')
    hour_end = fields.Float(string='End time')
    per_diem = fields.Monetary(string='Cost per person per day', tracking=True)
    cost = fields.Monetary(compute='_compute_cost', store=True, string='Total cost')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Mission currency', required=True, tracking=True,
        default=lambda self: self.env.company.currency_id,
        help='Every amount of the mission (daily cost, employee amounts, total) is in this currency.')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company currency')
    cost_company_currency = fields.Monetary(
        compute='_compute_cost_company_currency', store=True, currency_field='company_currency_id',
        string='Total cost in company currency',
        help='Total cost converted at the rate of the mission start date. Used to add up missions in reports.')
    line_ids = fields.One2many('tarco.hr.mission.line', 'mission_id', string='Employees')
    employee_count = fields.Integer(compute='_compute_cost', store=True)
    total_hours = fields.Float(compute='_compute_cost', store=True, string='Total hours')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.depends('date_start', 'date_end')
    def _compute_number_of_days(self):
        for mission in self:
            if mission.date_start and mission.date_end and mission.date_end >= mission.date_start:
                mission.number_of_days = (mission.date_end - mission.date_start).days + 1
            else:
                mission.number_of_days = 0

    @api.depends('per_diem', 'number_of_days', 'line_ids', 'hour_start', 'hour_end')
    def _compute_cost(self):
        for mission in self:
            count = len(mission.line_ids)
            mission.employee_count = count
            hours = (mission.hour_end or 0.0) - (mission.hour_start or 0.0)
            if hours < 0:
                hours += 24
            mission.total_hours = hours * (mission.number_of_days or 0) * count
            mission.cost = (mission.per_diem or 0.0) * (mission.number_of_days or 0) * count

    @api.depends('cost', 'currency_id', 'company_id', 'date_start')
    def _compute_cost_company_currency(self):
        for mission in self:
            company_currency = mission.company_id.currency_id
            if not mission.currency_id or mission.currency_id == company_currency:
                mission.cost_company_currency = mission.cost
            else:
                mission.cost_company_currency = mission.currency_id._convert(
                    mission.cost, company_currency, mission.company_id,
                    mission.date_start or fields.Date.context_today(mission))

    def action_print(self):
        return self.env.ref('tarco_hris.action_report_mission').report_action(self)

    @api.constrains('hour_start', 'hour_end')
    def _check_hours(self):
        for mission in self:
            for label, value in (('departure', mission.hour_start), ('end', mission.hour_end)):
                if value and not 0 <= value < 24:
                    raise ValidationError(_('Mission %s time must be inside 24 hours.') % label)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.mission') or '/'
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})


class TarcoHrMissionLine(models.Model):
    _name = 'tarco.hr.mission.line'
    _description = 'Mission Employee'

    mission_id = fields.Many2one('tarco.hr.mission', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='mission_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id')
    job_id = fields.Many2one(related='employee_id.job_id')
    currency_id = fields.Many2one(related='mission_id.currency_id')
    amount = fields.Monetary(compute='_compute_amount', string='Amount')

    @api.depends('mission_id.per_diem', 'mission_id.number_of_days')
    def _compute_amount(self):
        for line in self:
            line.amount = (line.mission_id.per_diem or 0.0) * (line.mission_id.number_of_days or 0)

    _mission_employee_unique = models.Constraint(
        'unique(mission_id, employee_id)',
        'An employee can be added to a mission only once.',
    )
