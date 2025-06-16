from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

class LarkLinkProjectWizard(models.TransientModel):
    _name = 'lark.link.project.wizard'
    _description = 'Lark Link Project Wizard'

    # Fields
    project_id = fields.Many2one(
        'project.project', 
        string='Odoo Project', 
        required=True, 
        readonly=True, 
        default=lambda self: self.env.context.get('active_id'),
        help="The Odoo project to link to a Lark tasklist"
    )
    
    lark_tasklist_id = fields.Many2one(
        'lark.tasklist', 
        string="Lark Tasklist", 
        required=True, 
        domain="[('id', 'in', available_tasklist_ids)]",
        help="Select a Lark tasklist to link to this project"
    )
    
    available_tasklist_ids = fields.Many2many(
        'lark.tasklist', 
        compute='_compute_available_tasklists', 
        string="Available Tasklists"
    )
    
    tasklist_domain = fields.Char(
        compute='_compute_available_tasklists', 
        readonly=True, 
        store=False
    )
    
    # Computed fields for display in the wizard
    tasklist_name = fields.Char(related='lark_tasklist_id.name', string='Tasklist Name', readonly=True)
    tasklist_guid = fields.Char(related='lark_tasklist_id.lark_guid', string='Lark GUID', readonly=True)
    tasklist_creator = fields.Char(related='lark_tasklist_id.creator_name', string='Created By', readonly=True)
    tasklist_created = fields.Datetime(related='lark_tasklist_id.created_at', string='Created On', readonly=True)
    tasklist_updated = fields.Datetime(related='lark_tasklist_id.updated_at', string='Last Updated', readonly=True)

    @api.depends('project_id')
    def _compute_available_tasklists(self):
        """Compute available tasklists that can be linked to the project."""
        for wizard in self:
            try:
                # Get all tasklists from the database
                all_tasklists = self.env['lark.tasklist'].search([], order='name')
                
                if not all_tasklists:
                    # If no tasklists found, try syncing from Lark
                    api = self.env['lark.api'].search([], limit=1, order='id desc')
                    if api:
                        api.sync_projects_from_lark()
                        all_tasklists = self.env['lark.tasklist'].search([], order='name')
                
                # Get IDs of already linked tasklists (excluding current project)
                linked_tasklist_guids = self.env['project.project'].search([
                    ('lark_id', '!=', False),
                    ('id', '!=', wizard.project_id.id or 0)  # Exclude current project
                ]).mapped('lark_id')
                
                # Filter out already linked tasklists
                available_tasklists = all_tasklists.filtered(
                    lambda t: t.lark_guid not in linked_tasklist_guids
                )
                
                wizard.available_tasklist_ids = available_tasklists
                wizard.tasklist_domain = str([('id', 'in', available_tasklists.ids)])
                
                # Auto-select if only one available
                if len(available_tasklists) == 1 and not wizard.lark_tasklist_id:
                    wizard.lark_tasklist_id = available_tasklists[0]
                
            except Exception as e:
                _logger.error("Error computing available tasklists: %s", str(e), exc_info=True)
                wizard.available_tasklist_ids = False
                wizard.tasklist_domain = str([('id', 'in', [])])
                raise UserError(_("Error fetching available tasklists. Please check the logs for details."))

    @api.constrains('lark_tasklist_id')
    def _check_lark_tasklist_id(self):
        """Ensure the selected tasklist is available for linking."""
        for wizard in self:
            if wizard.lark_tasklist_id and wizard.lark_tasklist_id not in wizard.available_tasklist_ids:
                raise ValidationError(_(
                    "The selected tasklist is not available for linking. "
                    "It may already be linked to another project."
                ))

    def action_link_project(self):
        """Links the selected Odoo project to the selected Lark tasklist."""
        self.ensure_one()
        if not self.lark_tasklist_id:
            raise UserError(_("Please select a tasklist to link."))
            
        try:
            # Update the project with the tasklist information
            self.project_id.write({
                'lark_id': self.lark_tasklist_id.lark_guid,
                'lark_tasklist_id': self.lark_tasklist_id.id,
                'name': self.lark_tasklist_id.name  # Optionally update the project name
            })
            
            # Return success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Project successfully linked to Lark tasklist: %s') % self.lark_tasklist_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error("Error linking project to tasklist: %s", str(e), exc_info=True)
            raise UserError(_("Failed to link project to tasklist: %s") % str(e))
        
        # To get the name for updating the project, we can refetch or parse the selection.
        # The selection list is available on the field itself.
        selection_list = self.fields_get(['lark_tasklist_id'])['lark_tasklist_id']['selection']
        tasklist_name = next((name for val, name in selection_list if val == self.lark_tasklist_id), "")

        _logger.info(f"Linking Odoo project '{self.project_id.name}' (ID: {self.project_id.id}) to Lark tasklist '{tasklist_name}' (ID: {self.lark_tasklist_id})")
        self.project_id.write({
            'lark_id': self.lark_tasklist_id,
        })
        
        return {'type': 'ir.actions.act_window_close'} 