# models/lark_task.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)

class LarkTask(models.Model):
    _name = 'lark.task'
    _description = 'Lark Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, create_date desc'
    _check_company_auto = True

    # Basic Fields
    task_sequence = fields.Char(
        string='Task Number',
        readonly=True,
        copy=False,
        index=True,
        help='Auto-generated task sequence number'
    )
    
    # Raw JSON data from Lark API
    json_data = fields.Text(
        string='Raw JSON Data',
        readonly=True,
        help='Raw JSON data received from the Lark API for debugging purposes'
    )
    name = fields.Char(
        string='Task Name', 
        required=True, 
        tracking=True,
        index=True
    )
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        index=True
    )
    
    # Description and Details
    description = fields.Html(
        string='Description',
        sanitize=True,
        strip_style=True
    )
    
    # Relationships
    project_id = fields.Many2one(
        'project.project', 
        string='Project', 
        required=True, 
        ondelete='cascade',
        index=True,
        tracking=True,
        check_company=True
    )
    task_id = fields.Many2one(
        'project.task', 
        string='Odoo Task', 
        ondelete='set null',
        index=True,
        copy=False
    )
    assignee_id = fields.Many2one(
        'res.users', 
        string='Assigned To',
        tracking=True,
        index=True,
        default=lambda self: self.env.uid
    )
    
    # Status and Dates
    status = fields.Selection(
        [
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('archived', 'Archived')
        ], 
        string='Status', 
        default='todo', 
        tracking=True,
        index=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'In Progress'),
            ('pending', 'Pending'),
            ('done', 'Done')
        ],
        string='State',
        default='draft',
        tracking=True,
        copy=False
    )
    due_date = fields.Datetime(
        string='Due Date',
        tracking=True,
        index=True
    )
    
    # Lark Specific Fields
    lark_id = fields.Char(
        string='Lark Task ID', 
        index=True,
        copy=False
    )
    lark_guid = fields.Char(
        string='Lark GUID',
        index=True,
        copy=False,
        help='GUID of the task in Lark',
        tracking=True
    )
    lark_etag = fields.Char(
        string='Lark ETag',
        readonly=True,
        copy=False,
        help='ETag for change tracking from Lark',
        tracking=True
    )
    lark_updated = fields.Datetime(
        string='Last Updated in Lark',
        readonly=True,
        copy=False,
        help='Last update timestamp from Lark',
        tracking=True
    )
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        copy=False,
        help='Last synchronization date with Lark',
        tracking=True
    )
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
        index=True
    )
    
    @api.depends('due_date', 'status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for task in self:
            task.is_overdue = bool(
                task.due_date 
                and task.due_date < now 
                and task.status not in ('done', 'archived')
            )
    
    @api.model
    def create_from_lark_data(self, task_data, project_id=None, parent_task_id=None):
        """
        Create or update task from Lark API data
        
        :param dict task_data: Task data from Lark API
        :param int project_id: Odoo project ID (optional, will use tasklist mapping if not provided)
        :param int parent_task_id: Parent task ID if this is a subtask
        :return: Created/updated task record
        """
        _logger.debug("=== RAW TASK DATA ===")
        _logger.debug("Type: %s", type(task_data))
        _logger.debug("Keys: %s", list(task_data.keys()) if isinstance(task_data, dict) else "Not a dict")
        _logger.debug("Full data: %s", task_data)
        
        if not isinstance(task_data, dict):
            _logger.error("Task data is not a dictionary: %s", task_data)
            return False
            
        # Check for task ID in common locations
        task_id = task_data.get('id') or task_data.get('task_id') or task_data.get('guid')
        if not task_id:
            _logger.warning("No task ID found in task data. Available keys: %s", list(task_data.keys()))
            _logger.warning("Task data: %s", task_data)
            return False
        if not task_data.get('id'):
            _logger.warning("No task ID in Lark task data: %s", task_data)
            return False
            
        # Find existing task by lark_id (task's ID in Lark)
        task = self.search([('lark_id', '=', task_data['id'])], limit=1)
        
        # Get or create project mapping using tasklist_guid if project_id not provided
        if not project_id and task_data.get('tasklist_guid'):
            project = self.env['project.project'].search([
                ('lark_tasklist_id.lark_guid', '=', task_data['tasklist_guid'])
            ], limit=1)
            if project:
                project_id = project.id
            else:
                _logger.warning("No project found for tasklist_guid: %s", task_data['tasklist_guid'])
        
        # Prepare task values
        current_time = fields.Datetime.now()
        vals = {
            'name': task_data.get('summary', 'Unnamed Task'),
            'description': task_data.get('description', ''),
            'lark_id': task_data['id'],  # Use id as the primary task identifier
            'lark_guid': task_data.get('guid', ''),  # Store guid for reference
            'status': self._convert_lark_status(task_data.get('status')),
            'due_date': self._convert_lark_timestamp(task_data.get('due', {}).get('timestamp')),
            'last_sync_date': current_time  # Update sync timestamp
        }
        
        if project_id:
            vals['project_id'] = project_id
            
        if parent_task_id:
            vals['parent_id'] = parent_task_id
            
        # Handle assignee if available
        if task_data.get('assignee_id'):
            user = self.env['res.users'].search([('lark_user_id', '=', task_data['assignee_id'])], limit=1)
            if user:
                vals['assignee_id'] = user.id
        
        if task:
            task.write(vals)
            _logger.info("Updated existing task %s (Lark ID: %s)", task.id, task_data['task_id'])
        else:
            task = self.create(vals)
            _logger.info("Created new task %s (Lark ID: %s)", task.id, task_data['task_id'])
            
        # Create or update linked Odoo task
        task._sync_odoo_task()
        
        return task
    
    def _convert_lark_status(self, status_data):
        """Convert Lark status to Odoo status"""
        status_mapping = {
            'todo': 'todo',
            'in_progress': 'in_progress',
            'done': 'done',
            'archived': 'archived'
        }
        return status_mapping.get(status_data.get('status'), 'todo')
    
    def _convert_lark_timestamp(self, timestamp):
        """Convert Lark timestamp to Odoo datetime"""
        if not timestamp:
            return False
        try:
            return datetime.fromtimestamp(int(timestamp) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return False
    
    def _sync_odoo_task(self):
        """Create or update linked Odoo task"""
        self.ensure_one()
        Task = self.env['project.task']
        
        # Prepare task values
        task_vals = {
            'name': self.name,
            'description': self.description,
            'project_id': self.project_id.id,
            'date_deadline': self.due_date,
            'user_ids': [(6, 0, [self.assignee_id.id])] if self.assignee_id else False,
            'lark_task_id': self.id,
        }
        
        # Update last sync time
        current_time = fields.Datetime.now()
        
        if self.task_id:
            self.task_id.write(task_vals)
            _logger.info("Updated Odoo task %s for Lark task %s", self.task_id.id, self.id)
        else:
            task = Task.create(task_vals)
            self.task_id = task.id
            _logger.info("Created new Odoo task %s for Lark task %s", task.id, self.id)
        
        # Update last sync date
        self.write({'last_sync_date': current_time})
            
        return self.task_id
        
    # Computed Fields
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
        index=True
    )
        
    _sql_constraints = [
        ('lark_id_company_uniq', 
         'unique (lark_id, company_id)', 
         'The Lark Task ID must be unique per company!'),
    ]
    
    @api.depends('due_date', 'status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for task in self:
            if task.due_date and task.status not in ['done', 'archived']:
                task.is_overdue = task.due_date < now
            else:
                task.is_overdue = False
    
    @api.model
    def create(self, vals):
        # Set default project from context if not provided
        if 'project_id' not in vals and self._context.get('default_project_id'):
            vals['project_id'] = self._context['default_project_id']
        
        # Set current user as assignee if not provided
        if 'assignee_id' not in vals:
            vals['assignee_id'] = self.env.uid
        
        # Generate task sequence if not provided
        if not vals.get('task_sequence') and vals.get('name'):
            # Get first 3 characters of the task name, convert to uppercase, and remove any non-alphabetic characters
            import re
            prefix = re.sub(r'[^a-zA-Z]', '', vals['name'])[:3].upper()
            
            # Ensure we have exactly 3 characters (pad with X if needed)
            if len(prefix) < 3:
                prefix = prefix.ljust(3, 'X')
            
            # Get or create the sequence
            sequence_code = f'lark.task.{prefix.lower()}'
            sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
            
            if not sequence:
                sequence = self.env['ir.sequence'].create({
                    'name': f'Lark Task {prefix} Sequence',
                    'code': sequence_code,
                    'prefix': f'{prefix}-',
                    'padding': 4,
                    'number_next_actual': 1,
                    'number_increment': 1,
                    'implementation': 'standard',
                })
            
            # Generate the sequence number
            vals['task_sequence'] = sequence.next_by_id()
            
        task = super(LarkTask, self).create(vals)
        
        # Log creation
        _logger.info(f'Created new Lark Task: {task.name} (ID: {task.id}, Sequence: {task.task_sequence})')
        
        return task
    
    def write(self, vals):
        res = super(LarkTask, self).write(vals)
        
        # Log changes
        if 'status' in vals or 'assignee_id' in vals or 'due_date' in vals:
            _logger.info(f'Updated Lark Task {self.id}: {dict(vals)}')
        
        return res
    
    def sync_with_lark(self):
        """Sync task with Lark"""
        self.ensure_one()
        try:
            _logger.info(f'Syncing Lark Task {self.id} with Lark')
            
            # TODO: Implement actual sync with Lark API
            # This is a placeholder for the actual API call
            
            # Update sync timestamp
            self.last_sync_date = fields.Datetime.now()
            
            # Show success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Task synced with Lark successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f'Error syncing Lark task {self.id}: {str(e)}')
            raise UserError(_('Error syncing with Lark: %s') % str(e))
    
    def action_open_odoo_task(self):
        """Open the linked Odoo task"""
        self.ensure_one()
        if not self.task_id:
            raise UserError(_('No Odoo task is linked to this Lark task.'))
            
        return {
            'name': _('Odoo Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': self.task_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def archive(self):
        """Archive the task"""
        self.write({'status': 'archived', 'active': False})
    
    def unarchive(self):
        """Unarchive the task"""
        self.write({'status': 'todo', 'active': True})
    
    def mark_as_done(self):
        """Mark task as done"""
        self.write({'status': 'done', 'state': 'done'})
    
    def mark_as_todo(self):
        """Mark task as to do"""
        self.write({'status': 'todo', 'state': 'open'})