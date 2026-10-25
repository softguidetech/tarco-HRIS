# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class TarcoJobApplyController(http.Controller):

    @http.route('/tarco/jobs/<int:job_id>/apply', type='http', auth='public', methods=['GET', 'POST'], csrf=True)
    def apply(self, job_id, **post):
        job = request.env['hr.job'].sudo().browse(job_id).exists()
        if not job:
            return request.not_found()
        error = False
        if request.httprequest.method == 'POST':
            name = (post.get('partner_name') or '').strip()
            email = (post.get('email_from') or '').strip()
            if not name or not email:
                error = 'Name and email are required.'
            else:
                answers = []
                for question in job.tarco_question_ids:
                    answers.append((0, 0, {
                        'question_id': question.id,
                        'answer': post.get('question_%s' % question.id) or '',
                    }))
                applicant = request.env['hr.applicant'].sudo().create({
                    'partner_name': name,
                    'email_from': email,
                    'partner_phone': post.get('partner_phone') or False,
                    'job_id': job.id,
                    'description': post.get('description') or False,
                    'tarco_years_experience': float(post.get('years') or 0.0),
                    'tarco_qualification': post.get('qualification') or False,
                    'tarco_track': 'maybe',
                    'tarco_answer_ids': answers,
                })
                upload = request.httprequest.files.get('cv')
                if upload and upload.filename:
                    payload = upload.read()
                    if len(payload) <= 8 * 1024 * 1024:
                        applicant.write({
                            'tarco_cv': base64.b64encode(payload),
                            'tarco_cv_name': upload.filename,
                        })
                return request.render('tarco_hris.tarco_job_apply_thanks', {'job': job})
        return request.render('tarco_hris.tarco_job_apply_form', {
            'job': job,
            'error': error,
            'qualifications': request.env['hr.employee'].sudo()._get_certificate_selection(),
        })
