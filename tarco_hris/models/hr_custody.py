# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TarcoHrAssetType(models.Model):
    _name = 'tarco.hr.asset.type'
    _description = 'Employee Custody Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Selection([
        ('computer', 'Laptop / Computer'),
        ('mobile', 'Mobile phone'),
        ('uniform', 'Uniform'),
        ('badge', 'Badge / ID card'),
        ('other', 'Other'),
    ], required=True, default='other')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Char()


class TarcoHrRequirement(models.Model):
    _name = 'tarco.hr.requirement'
    _description = 'Work Requirement After Hiring'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, index=True, tracking=True, ondelete='cascade')
    employee_code = fields.Char(related='employee_id.employee_code', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    kind = fields.Selection([
        ('training', 'Induction training'),
        ('safety', 'Safety briefing'),
        ('computer', 'Laptop / Computer'),
        ('mobile', 'Mobile phone'),
        ('uniform', 'Uniform'),
        ('badge', 'Badge / ID card'),
        ('warehouse', 'Warehouse issue'),
        ('account', 'System accounts'),
        ('other', 'Other'),
    ], required=True, default='other', tracking=True)
    onboarding_id = fields.Many2one('tarco.hr.onboarding', ondelete='set null')
    asset_id = fields.Many2one('tarco.hr.asset', string='Custody', ondelete='set null')
    note = fields.Char()
    done_date = fields.Date()
    state = fields.Selection([
        ('todo', 'To do'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='todo', required=True, tracking=True)

    def action_done(self):
        self.write({'state': 'done', 'done_date': fields.Date.context_today(self)})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_todo(self):
        self.write({'state': 'todo', 'done_date': False})

    def action_issue_custody(self):
        Asset = self.env['tarco.hr.asset']
        for rec in self:
            if rec.kind not in ('computer', 'mobile', 'uniform', 'badge', 'warehouse', 'other'):
                raise UserError(_('This requirement is not an item that can be issued as custody.'))
            if rec.asset_id and rec.asset_id.state != 'cancel':
                rec.asset_id.action_issue()
            else:
                rec.asset_id = Asset.create({
                    'employee_id': rec.employee_id.id,
                    'type_id': Asset._type_for_kind(rec.kind).id,
                    'description': rec.name,
                    'requirement_id': rec.id,
                    'note': rec.note or '',
                })
                rec.asset_id.action_issue()
            rec.write({'state': 'done', 'done_date': fields.Date.context_today(rec)})
        return True


class TarcoHrAsset(models.Model):
    _name = 'tarco.hr.asset'
    _description = 'Employee Custody'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, id desc'

    name = fields.Char(default='/', copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, index=True, tracking=True, ondelete='cascade')
    employee_code = fields.Char(related='employee_id.employee_code', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    type_id = fields.Many2one('tarco.hr.asset.type', required=True, tracking=True)
    type_code = fields.Selection(related='type_id.code', store=True)
    description = fields.Char(string='Item', tracking=True)
    serial = fields.Char(string='Serial / tag', tracking=True)
    quantity = fields.Integer(default=1)
    currency_id = fields.Many2one(related='company_id.currency_id')
    value = fields.Monetary()
    issue_date = fields.Date(default=fields.Date.context_today, tracking=True)
    expected_return_date = fields.Date()
    return_date = fields.Date(tracking=True)
    condition_issue = fields.Char(string='Condition when issued')
    condition_return = fields.Char(string='Condition when returned')
    requirement_id = fields.Many2one('tarco.hr.requirement', ondelete='set null')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
        ('cancel', 'Cancelled'),
    ], default='issued', required=True, tracking=True)

    @api.depends('name', 'description', 'type_id', 'serial')
    def _compute_display_name(self):
        for asset in self:
            parts = [asset.name or '']
            if asset.description:
                parts.append(asset.description)
            elif asset.type_id:
                parts.append(asset.type_id.display_name)
            if asset.serial:
                parts.append(asset.serial)
            asset.display_name = ' — '.join(part for part in parts if part) or _('Custody')

    @api.model
    def _type_for_kind(self, kind):
        code = kind if kind in ('computer', 'mobile', 'uniform', 'badge') else 'other'
        asset_type = self.env['tarco.hr.asset.type'].search([('code', '=', code)], limit=1)
        if not asset_type:
            asset_type = self.env['tarco.hr.asset.type'].create({
                'name': dict(self.env['tarco.hr.asset.type']._fields['code'].selection).get(code, code),
                'code': code,
            })
        return asset_type

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarco.hr.asset') or '/'
            vals.setdefault('state', 'issued')
            if vals.get('state') == 'issued' and not vals.get('issue_date'):
                vals['issue_date'] = today
        return super().create(vals_list)

    def action_issue(self):
        for asset in self:
            if not asset.employee_id:
                raise UserError(_('Set the employee before issuing custody.'))
            asset.write({
                'state': 'issued',
                'issue_date': asset.issue_date or fields.Date.context_today(asset),
            })
        return True

    def action_return(self):
        today = fields.Date.context_today(self)
        issued = self.filtered(lambda asset: asset.state == 'issued')
        if not issued and self:
            raise UserError(_('%s is not issued, so it cannot be returned.') % self[0].display_name)
        issued.write({'state': 'returned', 'return_date': today})
        return True

    def action_release_on_exit(self, exit_date=None, reason=''):
        """Return every issued item in one step (resign or dismissal)."""
        today = exit_date or fields.Date.context_today(self)
        issued = self.filtered(lambda asset: asset.state == 'issued')
        note = _('Released automatically at end of service%s.') % (
            (' — %s' % reason) if reason else ''
        )
        for asset in issued:
            extra = ('\n' + note) if note not in (asset.note or '') else ''
            asset.write({
                'state': 'returned',
                'return_date': today,
                'note': ((asset.note or '') + extra).strip(),
            })
        return issued

    def action_lost(self):
        today = fields.Date.context_today(self)
        self.write({'state': 'lost', 'return_date': today})

    def action_cancel(self):
        if self.filtered(lambda asset: asset.state == 'issued'):
            raise UserError(_('Return issued custody before cancelling it.'))
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft', 'return_date': False})

    @api.constrains('quantity')
    def _check_quantity(self):
        for asset in self:
            if asset.quantity < 1:
                raise ValidationError(_('Quantity must be at least 1.'))


class TarcoHrIssueWizard(models.TransientModel):
    _name = 'tarco.hr.issue.wizard'
    _description = 'Give Custody to Employee'

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    give_computer = fields.Boolean(string='Laptop / Computer', default=True)
    computer_item = fields.Char(string='Laptop model', default='Laptop')
    computer_serial = fields.Char(string='Laptop serial')
    give_mobile = fields.Boolean(string='Mobile phone')
    mobile_item = fields.Char(string='Phone model', default='Mobile phone')
    mobile_serial = fields.Char(string='Phone serial / number')
    give_uniform = fields.Boolean(string='Uniform')
    uniform_qty = fields.Integer(string='Uniform pieces', default=1)
    give_badge = fields.Boolean(string='Badge / ID card')
    badge_serial = fields.Char(string='Badge number')
    note = fields.Char()

    def action_give(self):
        self.ensure_one()
        if not any((self.give_computer, self.give_mobile, self.give_uniform, self.give_badge)):
            raise UserError(_('Tick at least one item to give to the employee.'))
        Asset = self.env['tarco.hr.asset']
        created = Asset.browse()
        specs = [
            (self.give_computer, 'computer', self.computer_item or _('Laptop'), self.computer_serial, 1),
            (self.give_mobile, 'mobile', self.mobile_item or _('Mobile phone'), self.mobile_serial, 1),
            (self.give_uniform, 'uniform', _('Uniform'), False, self.uniform_qty or 1),
            (self.give_badge, 'badge', _('Badge / ID card'), self.badge_serial, 1),
        ]
        for give, kind, item, serial, qty in specs:
            if not give:
                continue
            created |= Asset.create({
                'employee_id': self.employee_id.id,
                'type_id': Asset._type_for_kind(kind).id,
                'description': item,
                'serial': serial or False,
                'quantity': max(qty, 1),
                'note': self.note or '',
                'state': 'issued',
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Given to %s: %s') % (
                    self.employee_id.name,
                    ', '.join(created.mapped('description')),
                ),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class TarcoHrExitWizard(models.TransientModel):
    _name = 'tarco.hr.exit.wizard'
    _description = 'End of Service / Return Custody'

    employee_id = fields.Many2one('hr.employee', required=True)
    employee_code = fields.Char(related='employee_id.employee_code')
    exit_kind = fields.Selection([
        ('resign', 'Resignation'),
        ('fired', 'Dismissal / Fired'),
    ], required=True, default='resign')
    resignation_date = fields.Date(string='Last working day', required=True, default=fields.Date.context_today)
    outstanding_count = fields.Integer(compute='_compute_lines')
    line_ids = fields.One2many('tarco.hr.exit.line', 'wizard_id')
    note = fields.Text()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        employee = self.env['hr.employee'].browse(values.get('employee_id') or self.env.context.get('active_id'))
        if employee:
            values['employee_id'] = employee.id
            values['line_ids'] = [
                (0, 0, {'asset_id': asset.id})
                for asset in employee.tarco_asset_ids.filtered(lambda rec: rec.state == 'issued')
            ]
        return values

    @api.depends('line_ids', 'employee_id')
    def _compute_lines(self):
        for wizard in self:
            wizard.outstanding_count = len(wizard.line_ids)

    def _departure_reason(self):
        Reason = self.env['hr.departure.reason']
        if self.exit_kind == 'fired':
            return (
                Reason.search([('name', 'ilike', 'fired')], limit=1)
                or Reason.search([('name', 'ilike', 'dismiss')], limit=1)
                or Reason.search([('name', 'ilike', 'terminat')], limit=1)
            )
        return Reason.search([('name', 'ilike', 'resign')], limit=1)

    def action_confirm(self):
        self.ensure_one()
        reason_label = dict(self._fields['exit_kind'].selection).get(self.exit_kind)
        issued = self.employee_id.tarco_asset_ids.filtered(lambda rec: rec.state == 'issued')
        released = issued.action_release_on_exit(self.resignation_date, reason_label)
        self.employee_id.tarco_requirement_ids.filtered(lambda rec: rec.state == 'todo').action_cancel()
        vals = {
            'tarco_resignation_date': self.resignation_date,
            'departure_date': self.resignation_date,
        }
        reason = self._departure_reason()
        if reason:
            vals['departure_reason_id'] = reason.id
        self.employee_id.with_context(tarco_skip_custody_release=True).write(vals)
        items = released.mapped('display_name') or [_('none')]
        body = _('End of service (%s). Custody released: %s.') % (reason_label, ', '.join(items))
        if self.note:
            body = '%s\n%s' % (body, self.note)
        self.employee_id.message_post(body=body)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('%s recorded. %s custody item(s) returned automatically.') % (
                    reason_label, len(released),
                ),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class TarcoHrExitLine(models.TransientModel):
    _name = 'tarco.hr.exit.line'
    _description = 'End of Service Custody Line'

    wizard_id = fields.Many2one('tarco.hr.exit.wizard', required=True, ondelete='cascade')
    asset_id = fields.Many2one('tarco.hr.asset', required=True)
    type_id = fields.Many2one(related='asset_id.type_id')
    description = fields.Char(related='asset_id.description')
    serial = fields.Char(related='asset_id.serial')
    action = fields.Selection([
        ('return', 'Returned automatically'),
        ('lost', 'Lost / not returned'),
    ], default='return')
    return_date = fields.Date(default=fields.Date.context_today)
    condition = fields.Char()
    note = fields.Char()
