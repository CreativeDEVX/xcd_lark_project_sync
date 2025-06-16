from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import json

class LarkTasklist(models.Model):
    _name = 'lark.tasklist'
    _description = 'Lark Tasklist'
    _order = 'name'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(string="Tasklist Name", required=True, index=True)
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    lark_guid = fields.Char(string="Lark GUID", required=True, index=True, copy=False)
    url = fields.Char(string="Lark URL")
    
    # Creator/Owner Information
    creator_id = fields.Char(string="Creator ID", index=True)
    creator_name = fields.Char(compute='_compute_creator_name', store=True, string="Creator")
    owner_id = fields.Char(string="Owner ID", index=True)
    
    # Timestamps
    created_at = fields.Datetime(string="Created At", index=True)
    updated_at = fields.Datetime(string="Updated At", index=True)
    
    # Additional Data
    member_count = fields.Integer(string="Members", compute='_compute_member_count')
    is_linked = fields.Boolean(string="Is Linked", compute='_compute_is_linked', search='_search_is_linked')
    
    # Raw Data
    json_data = fields.Text(string="Raw JSON Data")
    
    # Relationships
    project_ids = fields.One2many('project.project', 'lark_tasklist_id', string="Linked Projects")
    has_projects = fields.Boolean(string="Has Projects", compute='_compute_has_projects', store=True, index=True)
    
    _sql_constraints = [
        ('lark_guid_unique', 'UNIQUE(lark_guid)', 'Lark GUID must be unique!'),
    ]
    
    @api.depends('name', 'lark_guid')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.lark_guid[:8]}...)" if record.lark_guid else record.name
    
    @api.depends('json_data')
    def _compute_creator_name(self):
        for record in self:
            if record.json_data:
                try:
                    data = json.loads(record.json_data)
                    creator = data.get('creator', {})
                    if creator.get('type') == 'user':
                        # In a real implementation, you might want to look up the user's name
                        record.creator_name = f"User ({creator.get('id', '')})"
                    else:
                        record.creator_name = "System"
                except Exception:
                    record.creator_name = "Unknown"
            else:
                record.creator_name = "Unknown"
    
    def _compute_member_count(self):
        for record in self:
            if record.json_data:
                try:
                    data = json.loads(record.json_data)
                    members = data.get('members', [])
                    record.member_count = len(members)
                except Exception:
                    record.member_count = 0
            else:
                record.member_count = 0
    
    @api.depends('project_ids')
    def _compute_has_projects(self):
        for record in self:
            record.has_projects = bool(record.project_ids)
    
    @api.depends('has_projects')
    def _compute_is_linked(self):
        for record in self:
            record.is_linked = record.has_projects
    
    def _search_is_linked(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise ValueError('Invalid operator: %s' % (operator,))
            
        query = """
            SELECT id FROM lark_tasklist lt
            WHERE EXISTS (
                SELECT 1 FROM project_project pp
                WHERE pp.lark_tasklist_id = lt.id
            )
        """
        self._cr.execute(query)
        linked_ids = [r[0] for r in self._cr.fetchall()]
        
        if operator in ('=', '!=') and value or operator == '<>':
            return [('id', 'in', linked_ids)]
        return [('id', 'not in', linked_ids)]
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.lark_guid[:8]}...)" if record.lark_guid else record.name
            result.append((record.id, name))
        return result
        
    def action_open_in_lark(self):
        """Open the tasklist in Lark's web interface."""
        self.ensure_one()
        if not self.url:
            raise UserError(_("No URL is available for this tasklist."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }
        
    def action_open_linked_project(self):
        """Open the linked project in a form view."""
        self.ensure_one()
        if not self.project_ids:
            raise UserError(_("No project is linked to this tasklist."))
            
        return {
            'name': _("Linked Project"),
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self.project_ids[0].id,
            'view_mode': 'form',
            'target': 'current',
        }
