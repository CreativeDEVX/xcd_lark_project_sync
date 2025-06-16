import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_logger.info("Loading project_extension.py")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lark_api_id = fields.Many2one(
        comodel_name='lark.api',
        string='Lark API Config',
        config_parameter='lark_project_sync.lark_api_id',
        help="Default Lark API configuration to use for project synchronization"
    )
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            lark_api_id=int(self.env['ir.config_parameter'].sudo().get_param('lark_project_sync.lark_api_id', 0)) or False,
        )
        return res
        
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('lark_project_sync.lark_api_id', self.lark_api_id.id)

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    lark_id = fields.Char(string="Lark Tasklist ID", readonly=True, index=True)
    lark_tasklist_id = fields.Many2one(
        'lark.tasklist', 
        string="Lark Tasklist", 
        ondelete='set null',
        tracking=True,
        help="Linked Lark Tasklist"
    )
    lark_parent_tasklist_guid = fields.Char(string="Lark Parent Tasklist GUID", readonly=True)
    lark_task_ids = fields.One2many(
        'lark.task', 
        'project_id', 
        string='Lark Tasks',
        copy=False
    )
    lark_task_count = fields.Integer(
        compute='_compute_lark_task_count', 
        string='Lark Tasks Count',
        store=True
    )
    
    @api.constrains('lark_tasklist_id')
    def _check_lark_tasklist_id(self):
        for project in self:
            if project.lark_tasklist_id and project.lark_tasklist_id.project_id and project.lark_tasklist_id.project_id != project:
                raise ValidationError(_("This tasklist is already linked to another project."))
    
    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project in projects:
            if 'lark_tasklist_id' in self.env.context.get('default_lark_tasklist_id', {}):
                project.lark_tasklist_id = self.env.context['default_lark_tasklist_id']
        return projects
    
    def write(self, vals):
        res = super().write(vals)
        if 'lark_tasklist_id' in vals:
            for project in self:
                if project.lark_tasklist_id and project.lark_tasklist_id.project_id != project:
                    project.lark_tasklist_id.write({'project_id': project.id})
        return res
    
    def create_in_lark(self):
        """Create this project in Lark"""
        self.ensure_one()
        if not self.lark_tasklist_id:
            raise UserError(_("No Lark tasklist is linked to this project."))
        return self.lark_tasklist_id.create_in_lark()
    
    def action_open_linked_tasklist(self):
        """Open the linked Lark tasklist in a form view."""
        self.ensure_one()
        if not self.lark_tasklist_id:
            raise UserError(_("No Lark tasklist is linked to this project."))
        return {
            'name': _('Lark Tasklist'),
            'type': 'ir.actions.act_window',
            'res_model': 'lark.tasklist',
            'view_mode': 'form',
            'res_id': self.lark_tasklist_id.id,
            'target': 'current',
        }
        
    @api.depends('lark_task_ids')
    def _compute_lark_task_count(self):
        for project in self:
            project.lark_task_count = len(project.lark_task_ids)

    def action_view_lark_tasks(self):
        """Action to view Lark tasks for this project"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('lark_project_sync.action_lark_task')
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
            'form_view_initial_mode': 'edit',
        }
        
        if self.lark_task_count == 1:
            action['views'] = [(self.env.ref('lark_project_sync.view_lark_task_form').id, 'form')]
            action['res_id'] = self.lark_task_ids.id
            
        return action
        
    def action_sync_lark_tasks(self):
        """Sync all Lark tasks for this project"""
        self.ensure_one()
        if not self.lark_tasklist_id:
            raise UserError(_("No Lark tasklist is linked to this project."))
        return self.lark_tasklist_id.sync_tasks()

class ProjectTaskExtension(models.Model):
    _inherit = 'project.task'
    
    lark_id = fields.Char(string="Lark Task ID", readonly=True, index=True, copy=False)
    lark_guid = fields.Char(string="Lark GUID", readonly=True, copy=False)
    lark_etag = fields.Char(string="Lark ETag", readonly=True, copy=False)
    lark_updated = fields.Datetime(string="Last Updated in Lark", readonly=True, copy=False)
    
    def create_in_lark(self):
        """Create this task in Lark"""
        self.ensure_one()
        if not self.project_id.lark_id:
            raise UserError(_("This project is not linked to a Lark tasklist. Please link it first."))
            
        lark_api = self.env['lark.api'].search([], limit=1, order='id desc')
        if not lark_api:
            raise UserError(_("No Lark API configuration found. Please configure Lark integration first."))
            
        try:
            task_data = {
                'summary': self.name,
                'description': self.description or '',
                'due': {'date': self.date_deadline.isoformat() + 'Z'} if self.date_deadline else None,
                'assignee_id': self.user_id.lark_user_id if hasattr(self.user_id, 'lark_user_id') else None,
            }
            
            # Create task in Lark
            response = lark_api._lark_request(
                'POST',
                f'/open-apis/task/v2/tasklists/{self.project_id.lark_id}/tasks',
                json=task_data
            )
            
            # Update task with Lark data
            self.write({
                'lark_id': response.get('id'),
                'lark_guid': response.get('guid'),
                'lark_etag': response.get('etag'),
                'lark_updated': fields.Datetime.now(),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Task created in Lark successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error("Failed to create task in Lark: %s", str(e), exc_info=True)
            raise UserError(_("Failed to create task in Lark: %s") % str(e))

class ProjectProject(models.Model):
    _inherit = 'project.project'

    lark_task_ids = fields.One2many(
        'lark.task', 
        'project_id', 
        string='Lark Tasks',
        copy=False
    )
    lark_task_count = fields.Integer(
        compute='_compute_lark_task_count', 
        string='Lark Tasks Count',
        store=True
    )

    @api.depends('lark_task_ids')
    def _compute_lark_task_count(self):
        for project in self:
            project.lark_task_count = len(project.lark_task_ids)

    def action_view_lark_tasks(self):
        """Action to view Lark tasks for this project"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('lark_project_sync.action_lark_task')
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
            'form_view_initial_mode': 'edit',
        }
        
        if self.lark_task_count == 1:
            action['views'] = [(self.env.ref('lark_project_sync.view_lark_task_form').id, 'form')]
            action['res_id'] = self.lark_task_ids.id
            
        return action
        
    def action_sync_lark_tasks(self):
        """Sync all Lark tasks for this project"""
        self.ensure_one()
        try:
            # TODO: Implement actual sync with Lark API
            _logger.info(f"Syncing all Lark tasks for project {self.name}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Lark tasks sync started for project %s', self.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error syncing Lark tasks: {str(e)}")
            raise UserError(_('Error syncing Lark tasks: %s') % str(e))