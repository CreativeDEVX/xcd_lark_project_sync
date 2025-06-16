from odoo import models, fields, api

class LarkAPILog(models.Model):
    _name = 'lark.api.log'
    _description = 'Lark API Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Lark Log", required=True, readonly=True)
    api_link = fields.Char(string="API Link", readonly=True)
    related_model = fields.Char(string="Related Model", readonly=True)
    create_date = fields.Datetime(string="Sync Date", readonly=True)
    response_type = fields.Selection([
        ('success', 'Success'),
        ('fail', 'Fail')
    ], string="Status", readonly=True, tracking=True)
    request_method = fields.Char(string="Request Method", readonly=True)
    request_param = fields.Text(string="Request Param", readonly=True)
    response_data = fields.Text(string="Response Data", readonly=True)
    
    # Parent-Child relationship for hierarchical logging
    parent_id = fields.Many2one('lark.api.log', string='Parent Log', readonly=True, ondelete='cascade')
    child_ids = fields.One2many('lark.api.log', 'parent_id', string='Child Logs', readonly=True)
    has_children = fields.Boolean(compute='_compute_has_children', store=True)
    
    @api.depends('child_ids')
    def _compute_has_children(self):
        for log in self:
            log.has_children = bool(log.child_ids)
            
    def action_view_logs(self):
        """Action to view all logs"""
        self.ensure_one()
        return {
            'name': 'API Logs',
            'type': 'ir.actions.act_window',
            'res_model': 'lark.api.log',
            'view_mode': 'list,form',
            'domain': [],
        }
