# -*- coding: utf-8 -*-
from odoo import fields, models


class TarcoHrDemoMixin(models.AbstractModel):
    _name = 'tarco.hr.demo.mixin'
    _description = 'Tarco HRIS Demo Marker'

    tarco_is_demo = fields.Boolean(index=True, copy=False, default=False)


class HrEmployee(models.Model):
    _inherit = ['hr.employee', 'tarco.hr.demo.mixin']


class HrDepartment(models.Model):
    _inherit = ['hr.department', 'tarco.hr.demo.mixin']


class HrJob(models.Model):
    _inherit = ['hr.job', 'tarco.hr.demo.mixin']


class HrApplicant(models.Model):
    _inherit = ['hr.applicant', 'tarco.hr.demo.mixin']


class HrLeave(models.Model):
    _inherit = ['hr.leave', 'tarco.hr.demo.mixin']


class HrLeaveAllocation(models.Model):
    _inherit = ['hr.leave.allocation', 'tarco.hr.demo.mixin']


class HrAttendance(models.Model):
    _inherit = ['hr.attendance', 'tarco.hr.demo.mixin']


class HrSalaryAttachment(models.Model):
    _inherit = ['hr.salary.attachment', 'tarco.hr.demo.mixin']


class CalendarEvent(models.Model):
    _inherit = ['calendar.event', 'tarco.hr.demo.mixin']


class ResourceCalendarLeaves(models.Model):
    _inherit = ['resource.calendar.leaves', 'tarco.hr.demo.mixin']


class TarcoHrDocument(models.Model):
    _inherit = ['tarco.hr.document', 'tarco.hr.demo.mixin']


class TarcoHrOnboarding(models.Model):
    _inherit = ['tarco.hr.onboarding', 'tarco.hr.demo.mixin']


class TarcoHrPublicHoliday(models.Model):
    _inherit = ['tarco.hr.public.holiday', 'tarco.hr.demo.mixin']


class TarcoHrMission(models.Model):
    _inherit = ['tarco.hr.mission', 'tarco.hr.demo.mixin']


class TarcoHrOvertime(models.Model):
    _inherit = ['tarco.hr.overtime', 'tarco.hr.demo.mixin']


class TarcoHrPenalty(models.Model):
    _inherit = ['tarco.hr.penalty', 'tarco.hr.demo.mixin']


class TarcoHrReward(models.Model):
    _inherit = ['tarco.hr.reward', 'tarco.hr.demo.mixin']


class TarcoHrAdvance(models.Model):
    _inherit = ['tarco.hr.advance', 'tarco.hr.demo.mixin']


class TarcoHrLeaveEncashment(models.Model):
    _inherit = ['tarco.hr.leave.encashment', 'tarco.hr.demo.mixin']


class TarcoHrKpiTemplate(models.Model):
    _inherit = ['tarco.hr.kpi.template', 'tarco.hr.demo.mixin']


class TarcoHrKpiReview(models.Model):
    _inherit = ['tarco.hr.kpi.review', 'tarco.hr.demo.mixin']


class TarcoHrAttendanceDay(models.Model):
    _inherit = ['tarco.hr.attendance.day', 'tarco.hr.demo.mixin']
