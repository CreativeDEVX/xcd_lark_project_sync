from odoo import models, fields, api
import re

class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    task_sequence = fields.Char(
        string='Task Number',
        readonly=True,
        copy=False,
        index=True,
        help='Auto-generated task sequence number'
    )
    
    @api.model
    def create(self, vals):
        # Call the original create method
        task = super(ProjectTask, self).create(vals)
        
        # Generate the sequence if name exists
        if task.name:
            # Get first 3 characters of the task name, convert to uppercase, and remove any non-alphabetic characters
            prefix = re.sub(r'[^a-zA-Z]', '', task.name)[:3].upper()
            
            # Ensure we have exactly 3 characters (pad with X if needed)
            if len(prefix) < 3:
                prefix = prefix.ljust(3, 'X')
            
            # Get or create the sequence
            sequence_code = f'project.task.{prefix.lower()}'
            sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
            
            if not sequence:
                sequence = self.env['ir.sequence'].create({
                    'name': f'Task {prefix} Sequence',
                    'code': sequence_code,
                    'prefix': f'{prefix}-',
                    'padding': 4,
                    'number_next_actual': 1,
                    'number_increment': 1,
                    'implementation': 'standard',
                })
            
            # Generate the sequence number
            sequence_number = sequence.next_by_id()
            
            # Store the sequence number in the task_sequence field
            if sequence_number:
                task.write({
                    'task_sequence': sequence_number,
                    # Keep the original name as is
                })
        
        return task
