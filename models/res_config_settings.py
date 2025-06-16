# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Lark API Configuration
    lark_api_id = fields.Many2one(
        'lark.api',
        string='Lark API Connection',
        help='Select a configured Lark API connection',
        default=lambda self: self.env.company.lark_api_id
    )
    
    lark_app_id = fields.Char(
        string='Lark App ID',
        config_parameter='xcd_lark_project_sync.lark_api_id',
        help='Your Lark App ID from the developer console',
        default=''
    )
    lark_api_secret = fields.Char(
        string='Lark App Secret',
        config_parameter='xcd_lark_project_sync.lark_api_secret',
        help='Your Lark App Secret from the developer console',
        default=''
    )
    lark_webhook_verify_token = fields.Char(
        string='Webhook Verify Token',
        config_parameter='xcd_lark_project_sync.webhook_verify_token',
        help='Verification token for Lark webhooks',
        default=''
    )
    lark_webhook_encrypt_key = fields.Char(
        string='Webhook Encrypt Key',
        config_parameter='xcd_lark_project_sync.webhook_encrypt_key',
        help='Encryption key for Lark webhooks',
        default=''
    )
    lark_sync_interval = fields.Integer(
        string='Sync Interval (minutes)',
        default=15,
        config_parameter='xcd_lark_project_sync.sync_interval',
        help='Interval in minutes for automatic synchronization with Lark'
    )
    lark_enable_sync = fields.Boolean(
        string='Enable Synchronization',
        default=True,
        config_parameter='xcd_lark_project_sync.enable_sync',
        help='Enable/disable automatic synchronization with Lark'
    )
    lark_debug_mode = fields.Boolean(
        string='Debug Mode',
        default=False,
        config_parameter='xcd_lark_project_sync.debug_mode',
        help='Enable debug logging for Lark integration'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        company = self.env.company
        
        res.update(
            lark_api_id=company.lark_api_id.id if company.lark_api_id else False,
            lark_app_id=get_param('xcd_lark_project_sync.lark_api_id', ''),
            lark_api_secret=get_param('xcd_lark_project_sync.lark_api_secret', ''),
            lark_webhook_verify_token=get_param('xcd_lark_project_sync.webhook_verify_token', ''),
            lark_webhook_encrypt_key=get_param('xcd_lark_project_sync.webhook_encrypt_key', ''),
            lark_sync_interval=int(get_param('xcd_lark_project_sync.sync_interval', '15')),
            lark_enable_sync=get_param('xcd_lark_project_sync.enable_sync', 'True').lower() == 'true',
            lark_debug_mode=get_param('xcd_lark_project_sync.debug_mode', 'False').lower() == 'true',
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        
        # Update company's Lark API connection
        self.env.company.sudo().write({
            'lark_api_id': self.lark_api_id.id if self.lark_api_id else False
        })
        
        # Update other parameters
        set_param('xcd_lark_project_sync.lark_api_id', self.lark_app_id or '')
        set_param('xcd_lark_project_sync.lark_api_secret', self.lark_api_secret or '')
        set_param('xcd_lark_project_sync.webhook_verify_token', self.lark_webhook_verify_token or '')
        set_param('xcd_lark_project_sync.webhook_encrypt_key', self.lark_webhook_encrypt_key or '')
        set_param('xcd_lark_project_sync.sync_interval', str(self.lark_sync_interval))
        set_param('xcd_lark_project_sync.enable_sync', str(self.lark_enable_sync))
        set_param('xcd_lark_project_sync.debug_mode', str(self.lark_debug_mode))