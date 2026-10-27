# -*- coding: utf-8 -*-
from odoo import fields, models


class TarcoHrDemoMixin(models.AbstractModel):
    _name = 'tarco.hr.demo.mixin'
    _description = 'Tarco HRIS Demo Marker'

    tarco_is_demo = fields.Boolean(index=True, copy=False, default=False)


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'tarco.hr.demo.mixin']


class HrDepartment(models.Model):
    _name = 'hr.department'
    _inherit = ['hr.department', 'tarco.hr.demo.mixin']


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'tarco.hr.demo.mixin']


class HrApplicant(models.Model):
    _name = 'hr.applicant'
    _inherit = ['hr.applicant', 'tarco.hr.demo.mixin']


class HrLeave(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'tarco.hr.demo.mixin']


class HrLeaveAllocation(models.Model):
    _name = 'hr.leave.allocation'
    _inherit = ['hr.leave.allocation', 'tarco.hr.demo.mixin']


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'tarco.hr.demo.mixin']


class HrSalaryAttachment(models.Model):
    _name = 'hr.salary.attachment'
    _inherit = ['hr.salary.attachment', 'tarco.hr.demo.mixin']


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'tarco.hr.demo.mixin']


class ResourceCalendarLeaves(models.Model):
    _name = 'resource.calendar.leaves'
    _inherit = ['resource.calendar.leaves', 'tarco.hr.demo.mixin']


class TarcoHrDocument(models.Model):
    _name = 'tarco.hr.document'
    _inherit = ['tarco.hr.document', 'tarco.hr.demo.mixin']


class TarcoHrOnboarding(models.Model):
    _name = 'tarco.hr.onboarding'
    _inherit = ['tarco.hr.onboarding', 'tarco.hr.demo.mixin']


class TarcoHrRequirement(models.Model):
    _name = 'tarco.hr.requirement'
    _inherit = ['tarco.hr.requirement', 'tarco.hr.demo.mixin']


class TarcoHrAsset(models.Model):
    _name = 'tarco.hr.asset'
    _inherit = ['tarco.hr.asset', 'tarco.hr.demo.mixin']


class TarcoHrEos(models.Model):
    _name = 'tarco.hr.eos'
    _inherit = ['tarco.hr.eos', 'tarco.hr.demo.mixin']


class TarcoHrPublicHoliday(models.Model):
    _name = 'tarco.hr.public.holiday'
    _inherit = ['tarco.hr.public.holiday', 'tarco.hr.demo.mixin']


class TarcoHrMission(models.Model):
    _name = 'tarco.hr.mission'
    _inherit = ['tarco.hr.mission', 'tarco.hr.demo.mixin']


class TarcoHrOvertime(models.Model):
    _name = 'tarco.hr.overtime'
    _inherit = ['tarco.hr.overtime', 'tarco.hr.demo.mixin']


class TarcoHrPenalty(models.Model):
    _name = 'tarco.hr.penalty'
    _inherit = ['tarco.hr.penalty', 'tarco.hr.demo.mixin']


class TarcoHrReward(models.Model):
    _name = 'tarco.hr.reward'
    _inherit = ['tarco.hr.reward', 'tarco.hr.demo.mixin']


class TarcoHrAdvance(models.Model):
    _name = 'tarco.hr.advance'
    _inherit = ['tarco.hr.advance', 'tarco.hr.demo.mixin']


class TarcoHrLeaveEncashment(models.Model):
    _name = 'tarco.hr.leave.encashment'
    _inherit = ['tarco.hr.leave.encashment', 'tarco.hr.demo.mixin']


class TarcoHrKpiTemplate(models.Model):
    _name = 'tarco.hr.kpi.template'
    _inherit = ['tarco.hr.kpi.template', 'tarco.hr.demo.mixin']


class TarcoHrKpiReview(models.Model):
    _name = 'tarco.hr.kpi.review'
    _inherit = ['tarco.hr.kpi.review', 'tarco.hr.demo.mixin']


class TarcoHrAttendanceDay(models.Model):
    _name = 'tarco.hr.attendance.day'
    _inherit = ['tarco.hr.attendance.day', 'tarco.hr.demo.mixin']
