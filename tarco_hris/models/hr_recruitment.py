# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_datetime

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
    tarco_meeting_id = fields.Many2one('calendar.event', string='Interview meeting', copy=False,
                                       ondelete='set null', readonly=True)
    tarco_meeting_display = fields.Char(compute='_compute_tarco_meeting_display')

    @api.depends('meeting_ids', 'meeting_ids.start')
    @api.depends_context('tz')
    def _compute_tarco_meeting_display(self):
        now = fields.Datetime.now()
        for applicant in self:
            starts = applicant.meeting_ids.mapped('start')
            if not starts:
                applicant.tarco_meeting_display = False
                continue
            upcoming = [start for start in starts if start >= now]
            start = min(upcoming) if upcoming else max(starts)
            applicant.tarco_meeting_display = format_datetime(
                self.env, start, tz=self.env.user.tz, dt_format='d MMM yyyy, h:mm a')

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

    def write(self, vals):
        result = super().write(vals)
        if {'tarco_interview_datetime', 'tarco_interview_round'} & set(vals):
            self.filtered('tarco_meeting_id')._tarco_sync_meeting()
        return result

    def _tarco_meeting_partners(self):
        self.ensure_one()
        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('Enter the applicant name before scheduling the interview.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
                'phone': self.partner_phone,
            })
        return (self.partner_id | self.interviewer_ids.partner_id | self.user_id.partner_id
                | self.department_id.manager_id.user_id.partner_id | self.env.user.partner_id)

    def _tarco_sync_meeting(self):
        for applicant in self:
            if not applicant.tarco_interview_datetime:
                continue
            round_label = dict(applicant._fields['tarco_interview_round'].selection).get(
                applicant.tarco_interview_round if applicant.tarco_interview_round != 'none' else 'first')
            start = applicant.tarco_interview_datetime
            vals = {
                'name': '%s - %s' % (round_label, applicant.partner_name or applicant.display_name),
                'start': start,
                'stop': start + timedelta(hours=1),
                'duration': 1.0,
                'allday': False,
                'applicant_id': applicant.id,
                'res_model_id': self.env['ir.model']._get_id('hr.applicant'),
                'res_id': applicant.id,
                'user_id': (applicant.user_id or self.env.user).id,
                'partner_ids': [Command.set(applicant._tarco_meeting_partners().ids)],
                'description': applicant.job_id and _('Interview for the position %s', applicant.job_id.name) or False,
            }
            if applicant.tarco_meeting_id:
                applicant.tarco_meeting_id.with_context(no_mail_to_attendees=True).write(vals)
            else:
                applicant.tarco_meeting_id = self.env['calendar.event'].with_context(
                    no_mail_to_attendees=True).create(vals)

    def action_send_interview(self):
        template = self.env.ref('tarco_hris.mail_template_tarco_interview', raise_if_not_found=False)
        for applicant in self:
            if not applicant.tarco_interview_datetime:
                raise UserError(_('Set the interview date and time first.'))
            applicant.write({
                'tarco_interview_round': applicant.tarco_interview_round if applicant.tarco_interview_round != 'none' else 'first',
            })
            applicant._tarco_sync_meeting()
            if template:
                template.send_mail(applicant.id, force_send=True)
            applicant.tarco_interview_sent = True


class TarcoHrApplicantAnswer(models.Model):
    _name = 'tarco.hr.applicant.answer'
    _description = 'Applicant Screening Answer'

    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade')
    question_id = fields.Many2one('tarco.hr.job.question', required=True)
    answer = fields.Char()
