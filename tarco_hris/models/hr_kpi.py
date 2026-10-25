# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class TarcoHrKpiTemplate(models.Model):
    _name = 'tarco.hr.kpi.template'
    _description = 'KPI Question Template'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    line_ids = fields.One2many('tarco.hr.kpi.template.line', 'template_id')


class TarcoHrKpiTemplateLine(models.Model):
    _name = 'tarco.hr.kpi.template.line'
    _description = 'KPI Question'
    _order = 'sequence, id'

    template_id = fields.Many2one('tarco.hr.kpi.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    weight = fields.Float(default=1.0)
    max_score = fields.Float(default=5.0)


class TarcoHrKpiReview(models.Model):
    _name = 'tarco.hr.kpi.review'
    _description = 'Employee KPI Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    reviewer_user_id = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    template_id = fields.Many2one('tarco.hr.kpi.template')
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    actual_hours = fields.Float(compute='_compute_hours', store=True)
    scheduled_hours = fields.Float(compute='_compute_hours', store=True)
    hours_ratio = fields.Float(string='Hours achievement %', compute='_compute_hours', store=True)
    output_quality = fields.Float(string='Output quality %')
    line_ids = fields.One2many('tarco.hr.kpi.review.line', 'review_id')
    output_ids = fields.One2many('tarco.hr.kpi.output', 'review_id', string='Daily outputs')
    score = fields.Float(string='Overall %', compute='_compute_score', store=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.kpi.review') or '/'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group('hr.group_hr_user'):
            for review in self:
                manager = review.employee_id.parent_id.user_id
                if self.env.user not in (manager, review.reviewer_user_id):
                    raise AccessError(_('Only the manager or HR can update this review.'))
        return super().write(vals)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return
        self.line_ids = [(5, 0, 0)] + [
            (0, 0, {
                'name': line.name,
                'weight': line.weight,
                'max_score': line.max_score,
            }) for line in self.template_id.line_ids
        ]

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_hours(self):
        for review in self:
            review.actual_hours = 0.0
            review.scheduled_hours = 0.0
            review.hours_ratio = 0.0
            if not review.employee_id or not review.date_from or not review.date_to:
                continue
            days = self.env['tarco.hr.attendance.day'].search([
                ('employee_id', '=', review.employee_id.id),
                ('work_date', '>=', review.date_from),
                ('work_date', '<=', review.date_to),
            ])
            actual = sum(days.mapped('regular_hours')) + sum(days.mapped('overtime_hours'))
            scheduled = sum(days.filtered(lambda day: day.status not in ('rest', 'holiday')).mapped(
                lambda day: day.shift_id.standard_hours or 8.0
            ))
            if not scheduled:
                working = len(days.filtered(lambda day: day.status not in ('rest', 'holiday')))
                scheduled = working * 8.0
            review.actual_hours = actual
            review.scheduled_hours = scheduled
            review.hours_ratio = (actual / scheduled * 100.0) if scheduled else 0.0

    @api.depends('line_ids.score', 'line_ids.weight', 'line_ids.max_score', 'hours_ratio', 'output_quality', 'output_ids.quality')
    def _compute_score(self):
        for review in self:
            weighted = 0.0
            weights = 0.0
            for line in review.line_ids:
                maximum = line.max_score or 1.0
                weight = line.weight or 1.0
                weighted += (line.score or 0.0) / maximum * 100.0 * weight
                weights += weight
            question_score = weighted / weights if weights else 0.0
            quality = review.output_quality or 0.0
            if review.output_ids:
                quality = sum(review.output_ids.mapped('quality')) / len(review.output_ids) * 20.0
            parts = [value for value in (question_score, review.hours_ratio, quality) if value]
            review.score = sum(parts) / len(parts) if parts else 0.0

    def action_load_template(self):
        for review in self:
            if not review.template_id:
                continue
            review.line_ids.unlink()
            review.write({'line_ids': [
                (0, 0, {
                    'name': line.name,
                    'weight': line.weight,
                    'max_score': line.max_score,
                }) for line in review.template_id.line_ids
            ]})

    def action_done(self):
        self.write({'state': 'done'})


class TarcoHrKpiReviewLine(models.Model):
    _name = 'tarco.hr.kpi.review.line'
    _description = 'KPI Review Answer'
    _order = 'id'

    review_id = fields.Many2one('tarco.hr.kpi.review', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    weight = fields.Float(default=1.0)
    max_score = fields.Float(default=5.0)
    score = fields.Float()
    comment = fields.Char()
    is_problem = fields.Boolean(compute='_compute_is_problem', store=True)

    @api.depends('score', 'max_score')
    def _compute_is_problem(self):
        for line in self:
            maximum = line.max_score or 1.0
            line.is_problem = (line.score or 0.0) / maximum < 0.6


class TarcoHrKpiOutput(models.Model):
    _name = 'tarco.hr.kpi.output'
    _description = 'Daily Work Output'
    _order = 'output_date'

    review_id = fields.Many2one('tarco.hr.kpi.review', required=True, ondelete='cascade')
    output_date = fields.Date(required=True, default=fields.Date.context_today)
    description = fields.Char(required=True)
    quality = fields.Float(string='Quality (1-5)', default=3.0)
