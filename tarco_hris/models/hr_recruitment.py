# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .tarco_common import QUALIFICATION_SELECTION


class HrJob(models.Model):
    _inherit = 'hr.job'

    tarco_approved_headcount = fields.Integer(string='Approved headcount')
    tarco_vacancy = fields.Integer(compute='_compute_tarco_vacancy', string='Vacant posts')
    tarco_objective = fields.Text(string='General objective')
    tarco_years_experience = fields.Float(string='Required experience (years)')
    tarco_qualification = fields.Selection(QUALIFICATION_SELECTION, string='Required qualification')
    tarco_skills = fields.Text(string='Required skills')
    tarco_previous_experience = fields.Text(string='Previous experience')
    tarco_training = fields.Text(string='Training')
    tarco_expected_wage = fields.Monetary(string='Expected wage')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    tarco_question_ids = fields.One2many('tarco.hr.job.question', 'job_id', string='Screening questions')
    tarco_apply_url = fields.Char(compute='_compute_tarco_apply_url', string='Application link')

    @api.depends('tarco_approved_headcount', 'no_of_employee')
    def _compute_tarco_vacancy(self):
        for job in self:
            job.tarco_vacancy = max((job.tarco_approved_headcount or 0) - (job.no_of_employee or 0), 0)

    def _compute_tarco_apply_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for job in self:
            job.tarco_apply_url = '%s/tarco/jobs/%s/apply' % (base, job.id) if job.id else False

    def action_open_vacancies(self):
        for job in self:
            job.no_of_recruitment = job.tarco_vacancy


class TarcoHrJobQuestion(models.Model):
    _name = 'tarco.hr.job.question'
    _description = 'Job Screening Question'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string='Question')
    expected_answer = fields.Char(help='Leave empty to accept any answer. Matching is not case sensitive.')
    required = fields.Boolean(default=True)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'
    _order = 'tarco_match_score desc, priority desc, sequence, id desc'

    tarco_years_experience = fields.Float(string='Years of experience')
    tarco_qualification = fields.Selection(QUALIFICATION_SELECTION, string='Qualification')
    tarco_cv = fields.Binary(string='CV', attachment=True)
    tarco_cv_name = fields.Char(string='CV filename')
    tarco_answer_ids = fields.One2many('tarco.hr.applicant.answer', 'applicant_id')
    tarco_match_score = fields.Float(string='Match %', compute='_compute_tarco_match_score', store=True)
    tarco_track = fields.Selection([
        ('shortlisted', 'Shortlisted'),
        ('maybe', 'Maybe'),
        ('rejected', 'Rejected'),
    ], string='Screening track', default='maybe', tracking=True)
    tarco_interview_datetime = fields.Datetime(string='Interview')
    tarco_interview_round = fields.Selection([
        ('none', 'Not contacted'),
        ('first', 'First interview'),
        ('final', 'Final interview'),
    ], default='none', tracking=True)
    tarco_interview_sent = fields.Boolean(copy=False)

    @api.depends(
        'job_id', 'tarco_answer_ids.answer', 'tarco_cv', 'email_from', 'partner_phone',
        'tarco_years_experience', 'tarco_qualification',
    )
    def _compute_tarco_match_score(self):
        for applicant in self:
            questions = applicant.job_id.tarco_question_ids
            score = 0.0
            if questions:
                matched = 0.0
                for question in questions:
                    answer = applicant.tarco_answer_ids.filtered(lambda item: item.question_id == question)[:1]
                    text = (answer.answer or '').strip().lower()
                    expected = (question.expected_answer or '').strip().lower()
                    if expected and text == expected:
                        matched += 1
                    elif not expected and text:
                        matched += 1
                score = matched / len(questions) * 80.0
            completeness = 0
            if applicant.partner_name:
                completeness += 1
            if applicant.email_from:
                completeness += 1
            if applicant.partner_phone:
                completeness += 1
            if applicant.tarco_cv:
                completeness += 1
            if applicant.tarco_qualification:
                completeness += 1
            applicant.tarco_match_score = min(score + completeness * 4.0, 100.0)

    def action_send_interview(self):
        template = self.env.ref('tarco_hris.mail_template_tarco_interview', raise_if_not_found=False)
        for applicant in self:
            if not applicant.tarco_interview_datetime:
                continue
            if template:
                template.send_mail(applicant.id, force_send=True)
            applicant.write({
                'tarco_interview_sent': True,
                'tarco_interview_round': applicant.tarco_interview_round if applicant.tarco_interview_round != 'none' else 'first',
            })


class TarcoHrApplicantAnswer(models.Model):
    _name = 'tarco.hr.applicant.answer'
    _description = 'Applicant Screening Answer'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade')
    question_id = fields.Many2one('tarco.hr.job.question', required=True)
    answer = fields.Char()
