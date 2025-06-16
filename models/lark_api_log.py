from odoo import models, fields

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
