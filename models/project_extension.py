from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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

class ProjectProjectExtension(models.Model):
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
    
    @api.constrains('lark_tasklist_id')
    def _check_lark_tasklist_id(self):
        for project in self:
            if project.lark_tasklist_id and project.lark_id and project.lark_id != project.lark_tasklist_id.lark_guid:
                raise ValidationError(_(
                    "The selected tasklist's GUID does not match the project's lark_id. "
                    "Please select the correct tasklist or update the project's lark_id."
                ))
    
    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        # If lark_id is set but lark_tasklist_id is not, try to find a matching tasklist
        for project in projects:
            if project.lark_id and not project.lark_tasklist_id:
                tasklist = self.env['lark.tasklist'].search([('lark_guid', '=', project.lark_id)], limit=1)
                if tasklist:
                    project.lark_tasklist_id = tasklist.id
        return projects
    
    def write(self, vals):
        res = super().write(vals)
        # If lark_tasklist_id is updated, update lark_id to match
        if 'lark_tasklist_id' in vals:
            for project in self:
                if project.lark_tasklist_id and project.lark_id != project.lark_tasklist_id.lark_guid:
                    project.lark_id = project.lark_tasklist_id.lark_guid
        return res

    def create_in_lark(self):
        self.ensure_one()
        self.env["lark.api"].search([], limit=1).push_project_to_lark(self)
    
    def action_open_linked_tasklist(self):
        """Open the linked Lark tasklist in a form view."""
        self.ensure_one()
        if not self.lark_tasklist_id:
            raise UserError(_("No Lark tasklist is linked to this project."))
        return {
            'name': _("Linked Tasklist"),
            'type': 'ir.actions.act_window',
            'res_model': 'lark.tasklist',
            'res_id': self.lark_tasklist_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

class ProjectTaskExtension(models.Model):
    _inherit = 'project.task'

    def create_in_lark(self):
        self.ensure_one()
        self.env["lark.api"].search([], limit=1).push_task_to_lark(self)
