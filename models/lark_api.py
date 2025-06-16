import requests
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from odoo import http

_logger = logging.getLogger(__name__)

def lark_ms_to_odoo_datetime(ms):
    if not ms:
        return False
    return datetime.fromtimestamp(int(ms) / 1000.0)

class LarkAPI(models.Model):
    _name = "lark.api"
    _description = "Lark API Integration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string="Connection Name", required=True, default="Lark Connection", tracking=True)
    app_id = fields.Char(string="Lark App ID", required=True, default="cli_a7cfed7fdab8d003")
    app_secret = fields.Char(required=True, default="tOji58BRiUQEQFXAcU8xjdYbDHcRUY7t")
    user_access_token = fields.Char(string="User Access Token", required=True)
    is_token_valid = fields.Boolean(compute='_compute_is_token_valid', string="Is Token Valid")
    tasklist_data = fields.Text(string="Lark Tasklists (JSON)", readonly=True)
    token_expire = fields.Datetime(string="Token Expires On", readonly=True)
    token_remaining_time = fields.Char(string="Token Remaining", compute="_compute_token_remaining_time")
    redirect_uri = fields.Char(string="Redirect URI")
    authorization_code = fields.Char(string="Authorization Code")
    refresh_token = fields.Char(string="Refresh Token")
    oauth_state = fields.Char(string="OAuth State", readonly=True)

    @api.depends('token_expire')
    def _compute_token_remaining_time(self):
        for rec in self:
            if rec.token_expire:
                now = fields.Datetime.now()
                delta = rec.token_expire - now
                minutes = int(delta.total_seconds() // 60)
                if minutes > 0:
                    rec.token_remaining_time = f"{minutes} minute(s) remaining"
                else:
                    rec.token_remaining_time = "Expired"
            else:
                rec.token_remaining_time = "Not available"

    @api.depends('user_access_token', 'token_expire')
    def _compute_is_token_valid(self):
        for record in self:
            record.is_token_valid = bool(record.user_access_token and record.token_expire and record.token_expire > fields.Datetime.now())

    def get_access_token(self):
        """Return the user access token from the record"""
        self.ensure_one()
        if not self.user_access_token:
            raise UserError(_("Please provide a valid User Access Token."))
        return self.user_access_token

    def action_get_access_token(self):
        """Button action to manually get access token"""
        self.ensure_one()
        try:
            token = self.get_access_token()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Access token retrieved successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def sync_lark_tasks(self, project_id=None):
        """
        Fetch tasks from Lark and create/update them in Odoo
        
        :param int project_id: Optional Odoo project ID to link tasks to
        :return: dict with sync results
        """
        self.ensure_one()
        
        if not self.user_access_token:
            raise UserError(_("No valid Lark access token. Please authenticate first."))
            
        # Get task lists from Lark
        tasklists = self.get_tasklists()
        if not tasklists:
            return {'success': False, 'message': 'No task lists found in Lark'}
            
        results = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'tasklists': []
        }
        
        # Process each task list
        for tasklist in tasklists:
            try:
                tasks = self.get_tasks(tasklist['tasklist_id'])
                if not tasks:
                    continue
                    
                tasklist_info = {
                    'name': tasklist.get('name', 'Unnamed List'),
                    'tasks': [],
                    'count': 0
                }
                
                # Process each task in the list
                for task_data in tasks:
                    try:
                        task = self.env['lark.task'].create_from_lark_data(
                            task_data,
                            project_id=project_id
                        )
                        if task:
                            results['total'] += 1
                            tasklist_info['count'] += 1
                            tasklist_info['tasks'].append({
                                'id': task.id,
                                'name': task.name,
                                'status': task.status
                            })
                            if task_data.get('is_new', True):
                                results['created'] += 1
                            else:
                                results['updated'] += 1
                    except Exception as e:
                        _logger.error("Error processing task %s: %s", task_data.get('task_id'), str(e))
                        results['errors'] += 1
                        
                if tasklist_info['count'] > 0:
                    results['tasklists'].append(tasklist_info)
                    
            except Exception as e:
                _logger.error("Error processing task list %s: %s", tasklist.get('tasklist_id'), str(e))
                results['errors'] += 1
                
        return results
        
    def _get_paginated_results(self, url, params=None):
        """Handle paginated API responses"""
        results = []
        page_token = None
        
        try:
            while True:
                request_params = params.copy() if params else {}
                if page_token:
                    request_params['page_token'] = page_token
                
                _logger.info("Making request to %s with params: %s", url, request_params)
                headers = {
                    "Authorization": f"Bearer {self.user_access_token}",
                    "Content-Type": "application/json; charset=utf-8"
                }
                _logger.debug("Request headers: %s", headers)
                
                response = requests.get(
                    url,
                    headers=headers,
                    params=request_params,
                    timeout=30
                )
                
                # import pdb; pdb.set_trace()
                
                # Log the raw response for debugging
                _logger.debug("Response status: %s", response.status_code)
                _logger.debug("Response headers: %s", response.headers)
                _logger.debug("Response content: %s", response.text)
                
                response.raise_for_status()
                
                # Add PDB debugger for tasklist responses
                data = response.json()
                
                if 'task/v2/tasklists' in url:
                    # import pdb; pdb.set_trace()
                    _logger.info("PDB: Debugging tasklist response. Type 'p data' to see the response data")
                    _logger.info("Available variables: response, data, results, page_token")
                    _logger.info("Tasklist items: %s", data.get('data', {}).get('items', []))
                
                if data.get('code') != 0:
                    error_msg = f"API Error: {data.get('msg', 'Unknown error')} (Code: {data.get('code')})"
                    _logger.error(error_msg)
                    raise UserError(_(error_msg))
                    
                items = data.get('data', {}).get('items', [])
                _logger.info("Retrieved %d items", len(items))
                results.extend(items)
                
                # Check if there are more pages
                if not data.get('data', {}).get('has_more'):
                    _logger.info("No more pages to fetch")
                    break
                    
                page_token = data.get('data', {}).get('page_token')
                if not page_token:
                    _logger.info("No page token in response")
                    break
                    
        except requests.exceptions.RequestException as e:
            error_msg = f"Error making request to {url}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nStatus Code: {e.response.status_code}"
                try:
                    error_data = e.response.json()
                    error_msg += f"\nError Code: {error_data.get('code')}"
                    error_msg += f"\nError Message: {error_data.get('msg')}"
                except ValueError:
                    error_msg += f"\nResponse: {e.response.text}"
            _logger.error(error_msg, exc_info=True)
            raise UserError(_(error_msg)) from e
                
        return results

    def sync_projects_from_lark(self):
        self.ensure_one()
        request_params = {}
        try:
            _logger.info("Starting sync of all Lark tasklists to Odoo projects.")
            tasklists_url = "https://open.larksuite.com/open-apis/task/v2/tasklists"
            tasklists = self._get_paginated_results(tasklists_url)
            tasklist_count = len(tasklists) if tasklists else 0
            
            if not tasklists:
                self.message_post(
                    body="<b>⚠️ No Tasklists Found:</b> No tasklists were found in Lark with the current permissions.",
                    message_type="comment"
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Tasklists Found'),
                        'message': _('No tasklists were found in Lark with the current permissions.'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            # Count existing and new projects
            projects_updated = 0
            projects_created = 0
            
            for tasklist in tasklists:
                try:
                    guid = tasklist.get('id') or tasklist.get('guid')
                    tasklist_name = tasklist.get('name', 'Unnamed Tasklist')
                    
                    # First try to find by lark_id
                    project_domain = ['|', 
                                   ('lark_id', '=', guid),
                                   ('name', '=', tasklist_name)]
                    
                    odoo_project = self.env['project.project'].search(project_domain, limit=1)
                    
                    project_values = {
                        'name': tasklist_name,
                        'lark_id': guid,
                        'description': tasklist.get('description', ''),
                    }
                    
                    if odoo_project:
                        # If project found, update it
                        odoo_project.write(project_values)
                        projects_updated += 1
                        _logger.info(f"Updated existing project: {tasklist_name} (Lark ID: {guid})")
                    else:
                        # If no project found, create a new one
                        new_project = self.env['project.project'].create(project_values)
                        projects_created += 1
                        _logger.info(f"Created new project: {tasklist_name} (Lark ID: {guid})")

                    # Also sync lark.tasklist view
                    guid = tasklist.get('id') or tasklist.get('guid')
                    tasklist_vals = {
                        'name': tasklist.get('name'),
                        'lark_guid': guid,
                        'url': tasklist.get('url'),
                        'creator_id': (tasklist.get('creator') or {}).get('id'),
                        'owner_id': (tasklist.get('owner') or {}).get('id'),
                        'created_at': lark_ms_to_odoo_datetime(tasklist.get('created_at')),
                        'updated_at': lark_ms_to_odoo_datetime(tasklist.get('updated_at')),
                        'json_data': json.dumps(tasklist, ensure_ascii=False),
                    }
                    
                    # Update or create lark.tasklist record
                    existing_tasklist = self.env['lark.tasklist'].search([('lark_guid', '=', guid)], limit=1)
                    if existing_tasklist:
                        existing_tasklist.write(tasklist_vals)
                    else:
                        self.env['lark.tasklist'].create(tasklist_vals)
                        
                except Exception as e:
                    _logger.error("Failed to process tasklist %s: %s", tasklist.get('id'), str(e), exc_info=True)
                    continue
                    
            # Log the API call
            self.env['lark.api.log'].create({
                'name': 'Sync Tasklists',
                'api_link': tasklists_url,
                'related_model': 'lark.api',
                'response_type': 'success',
                'request_method': 'GET',
                'request_param': str(request_params),
                'response_data': json.dumps({
                    'tasklists_found': tasklist_count,
                    'projects_created': projects_created,
                    'projects_updated': projects_updated,
                }),
            })
            
            # Prepare success message
            success_message = (
                f"<b>✅ Tasklist Sync Completed</b><br/>"
                f"• Total tasklists found: <b>{tasklist_count}</b><br/>"
                f"• Projects created: <b>{projects_created}</b><br/>"
                f"• Projects updated: <b>{projects_updated}</b>"
            )
            
            # Post to chatter
            self.message_post(body=success_message, message_type="comment")
            
            # Log to chatter as well
            self.log_json_to_chatter({
                'tasklists_found': tasklist_count,
                'projects_created': projects_created,
                'projects_updated': projects_updated,
            }, subject="Lark Tasklist Sync Summary")
            
            # Return success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Successful'),
                    'message': (
                        f'Synced {tasklist_count} tasklists: '
                        f'{projects_created} created, {projects_updated} updated.'
                    ),
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error("Error syncing tasklists: %s", str(e), exc_info=True)
            error_message = _('Error syncing tasklists: {}').format(str(e))
            self.message_post(
                body=f"<b>❌ Sync Failed:</b> {error_message}",
                message_type="comment"
            )
            # Log the error
            self.env['lark.api.log'].create({
                'name': 'Sync Tasklists',
                'api_link': 'https://open.larksuite.com/open-apis/task/v2/tasklists',
                'related_model': 'lark.api',
                'response_type': 'fail',
                'request_method': 'GET',
                'request_param': str(request_params),
                'response_data': str(e),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sync Failed'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def sync_tasks_from_lark(self):
        """Sync tasks from Lark to Odoo for all linked projects."""
        self.ensure_one()
        _logger.info("Starting full task sync from Lark.")
        
        try:
            projects = self.env['project.project'].search([('lark_id', '!=', False)])
            if not projects:
                raise UserError(_("No Lark-linked projects found in Odoo. Please sync projects or sections first."))
                
            tasks_synced_total = 0
            
            for project in projects:
                try:
                    tasks_data = []
                    if hasattr(project, 'lark_parent_tasklist_guid') and project.lark_parent_tasklist_guid:
                        # Project is a Lark Section.
                        _logger.info(f"Fetching tasks for SECTION project '{project.name}' (ID: {project.lark_id})")
                        url = f"https://open.larksuite.com/open-apis/task/v2/sections/{project.lark_id}/tasks"
                        tasks_data = self._get_paginated_results(url, {'page_size': 100})
                    else:
                        # Project is a Lark Tasklist.
                        _logger.info(f"Fetching tasks for TASKLIST project '{project.name}' (ID: {project.lark_id})")
                        tasks_data = self._get_all_tasks_for_project(project.lark_id)
                    
                    tasks_processed = self._process_task_data(tasks_data, project.id)
                    tasks_synced_total += tasks_processed

                except Exception as e:
                    _logger.error(f"Failed to sync tasks for project '{project.name}' (Lark ID: {project.lark_id}). Error: {e}", exc_info=True)
                    continue

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Total of %s tasks synchronized across all projects.') % tasks_synced_total,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("General error in sync_tasks_from_lark: %s", str(e), exc_info=True)
            raise UserError(_("Error during task sync: %s") % str(e))
            
    
    def _log_task_data(self, task_data, index=None):
        """Safely log task data for debugging"""
        try:
            import json
            from datetime import datetime
            
            log_data = {}
            if index is not None:
                _logger.info("\n=== Processing Task %s ===", index)
                
            # Safely extract and log task data
            for field in ['id', 'summary', 'description', 'due', 'completed', 'assignee_id', 'parent_id']:
                value = task_data.get(field)
                if isinstance(value, dict):
                    log_data[field] = {k: v for k, v in value.items() if not k.startswith('_')}
                else:
                    log_data[field] = value
            
            _logger.info("Task data: %s", json.dumps(log_data, indent=2, default=str))
            
        except Exception as e:
            _logger.error("Error logging task data: %s", str(e), exc_info=True)
    
    def _process_task_data(self, tasks_data, project_id):
        """Helper to process a list of Lark task data and sync them to a specific Odoo project.
        
        Args:
            tasks_data (list): List of task dictionaries from Lark API
            project_id (int): ID of the Odoo project to sync tasks to
            
        Returns:
            int: Number of tasks successfully processed
        """
        _logger.info("=== PROCESSING %d TASKS FOR PROJECT %s ===", 
                    len(tasks_data) if tasks_data else 0, project_id)
        
        Task = self.env['project.task']
        Project = self.env['project.project']
        tasks_synced = 0
        
        # Get the project to check if it's linked to Lark
        project = Project.browse(project_id)
        if not project.exists():
            _logger.error("Project with ID %s not found", project_id)
            return 0
            
        if not project.lark_id:
            _logger.warning("Project %s is not linked to a Lark tasklist. Skipping task sync.", project.name)
            return 0
            
        _logger.info("Project '%s' is linked to Lark tasklist: %s", project.name, project.lark_id)
            
        for idx, task_data in enumerate(tasks_data or [], 1):
            # Use ID if available, otherwise use GUID
            task_id = task_data.get('id') or task_data.get('guid')
            if not task_id:
                _logger.warning("Skipping task at index %d with no ID or GUID. Data: %s", idx, task_data)
                continue
                
            try:
                _logger.debug("\n=== Processing task %d/%d (ID: %s) ===", 
                            idx, len(tasks_data), task_id)
                
                # Log task data structure for debugging
                self._log_task_data(task_data, idx)
                
                # Try to find existing task by lark_id
                task = Task.search([('lark_id', '=', task_id)], limit=1)
                _logger.debug("Found existing task: %s", task.id if task else 'None')
                
                # Prepare task values with error handling
                due_date = None
                try:
                    if isinstance(task_data.get('due'), dict):
                        due_date = task_data.get('due', {}).get('date')
                        if due_date:
                            due_date = fields.Datetime.to_datetime(due_date)
                            _logger.debug("Parsed due date: %s", due_date)
                except Exception as e:
                    _logger.warning("Error parsing due date for task %s: %s", task_id, str(e))
                
                is_completed = task_data.get('completed', False)
                task_name = task_data.get('summary', 'Unnamed Task')
                
                # Get the Odoo user ID if assignee exists
                odoo_user_id = self._find_odoo_user_id(task_data.get('assignee_id'))
                
                values = {
                    'project_id': project_id,
                    'name': task_name,
                    'description': task_data.get('description', ''),
                    'lark_id': task_id,
                    'lark_guid': task_data.get('guid'),
                    'lark_etag': task_data.get('etag'),
                    'lark_updated': fields.Datetime.now(),
                    'date_deadline': due_date or False,
                    'user_ids': [(6, 0, [odoo_user_id])] if odoo_user_id else False,
                    'stage_id': self._get_task_stage_id(project_id, is_completed),
                    'date_last_stage_update': fields.Datetime.now() if is_completed else False,
                }
                
                # Log values except description to keep logs clean
                log_values = {k: v for k, v in values.items() 
                             if not k.startswith('description')}
                _logger.debug("Task values: %s", log_values)
                
                # Handle parent task if exists
                parent_id = task_data.get('parent_id')
                if parent_id:
                    parent_task = Task.search([('lark_id', '=', parent_id)], limit=1)
                    if parent_task:
                        values['parent_id'] = parent_task.id
                        _logger.debug("Linked to parent task ID: %s", parent_task.id)
                
                try:
                    if task:
                        # Update existing task
                        task.write(values)
                        _logger.info("Updated task '%s' (Lark ID: %s) in project '%s'", 
                                   task_name, task_id, project.name)
                    else:
                        # Create new task
                        task = Task.create(values)
                        _logger.info("Created new task '%s' (Lark ID: %s) in project '%s' (Odoo ID: %s)", 
                                   task_name, task_id, project.name, task.id)
                    
                    tasks_synced += 1
                    
                except Exception as e:
                    _logger.error("Error saving task %s (%s): %s", 
                                 task_name, task_id, str(e), exc_info=True)
                    continue
                
            except Exception as e:
                task_id_str = str(task_id) if 'task_id' in locals() else 'unknown'
                _logger.error("Error syncing task %s: %s", task_id_str, str(e), exc_info=True)
                continue
                
        success_rate = (tasks_synced / len(tasks_data) * 100) if tasks_data else 0
        _logger.info("=== TASK SYNC COMPLETE ===")
        _logger.info("Project: %s (ID: %s)", project.name, project_id)
        _logger.info("Tasks processed: %d", len(tasks_data) if tasks_data else 0)
        _logger.info("Tasks synced: %d (%.1f%%)", tasks_synced, success_rate)
        _logger.info("Failed: %d", (len(tasks_data) if tasks_data else 0) - tasks_synced)
        
        return tasks_synced

    def _get_all_tasks_for_project(self, tasklist_guid):
        """Get all tasks for a given tasklist using the Lark API.
        
        Args:
            tasklist_guid (str): The GUID of the tasklist to fetch tasks from
            
        Returns:
            list: List of task dictionaries with required fields
        """
        _logger.info("=== FETCHING TASKS FOR TASKLIST: %s ===", tasklist_guid)
        url = f"https://open.larksuite.com/open-apis/task/v2/tasklists/{tasklist_guid}/tasks"
        _logger.info("Requesting tasks from URL: %s", url)
        
        try:
            # Get paginated results
            tasks = self._get_paginated_results(url, {'page_size': 100})
            _logger.info("Retrieved %d tasks from API", len(tasks) if tasks else 0)
            
            if not tasks:
                _logger.warning("No tasks returned from API for tasklist %s", tasklist_guid)
                return []
                
            # Log first task as sample
            if tasks:
                _logger.info("Sample task data (first task): %s", json.dumps(tasks[0], indent=2, default=str))
                
                # Check for required fields
                for i, task in enumerate(tasks, 1):
                    if not task.get('id'):
                        _logger.warning("Task at index %d is missing 'id' field: %s", i, task)
                    if not task.get('summary'):
                        _logger.warning("Task at index %d is missing 'summary' field: %s", i, task)
            
            return tasks
            
        except Exception as e:
            _logger.error("Error fetching tasks for tasklist %s: %s", tasklist_guid, str(e), exc_info=True)
            return []
            
        return tasks

    def _find_odoo_user_id(self, lark_user_id):
        """Find Odoo user ID from Lark user ID"""
        if not lark_user_id:
            return False
            
        # You might need to implement a mapping between Lark and Odoo users
        # For now, return the current user or False
        return self.env.user.id or False
    
    def _get_task_stage_id(self, project_id, is_completed):
        """Get the appropriate stage ID for a task based on completion status.
        
        Args:
            project_id (int): ID of the project
            is_completed (bool): Whether the task is completed
            
        Returns:
            int: ID of the stage, or False if no stages found
        """
        _logger.debug("Getting stage for project %s (completed=%s)", project_id, is_completed)
        
        # Get the project and verify it exists
        project = self.env['project.project'].browse(project_id)
        if not project.exists():
            _logger.error("Project with ID %s not found", project_id)
            return False
        
        # Get all stages for the project
        stages = self.env['project.task.type'].search([('project_ids', 'in', [project_id])])
        
        if not stages:
            _logger.warning("No stages found for project '%s' (ID: %s)", project.name, project_id)
            return False
            
        _logger.debug("Available stages for project '%s': %s", 
                     project.name, 
                     [(s.id, s.name, s.sequence) for s in stages])
        
        if is_completed:
            # Look for completed stages in order of preference
            for stage_name in ['Done', 'Completed', 'Closed']:
                done_stage = stages.filtered(
                    lambda s: stage_name.lower() in s.name.lower()
                )
                if done_stage:
                    stage = min(done_stage, key=lambda x: x.sequence)  # Get the first in sequence if multiple
                    _logger.debug("Using '%s' stage (ID: %s) for completed task", 
                                 stage.name, stage.id)
                    return stage.id
            
            # If no specific done stage found, use the last stage in the sequence
            last_stage = max(stages, key=lambda x: x.sequence)
            _logger.debug("Using last stage '%s' (ID: %s) for completed task", 
                         last_stage.name, last_stage.id)
            return last_stage.id
        else:
            # For incomplete tasks, use the first stage in the sequence
            first_stage = min(stages, key=lambda x: x.sequence)
            _logger.debug("Using first stage '%s' (ID: %s) for new task", 
                         first_stage.name, first_stage.id)
            return first_stage.id


    def push_task_to_lark(self, task):
        if not task.project_id.lark_id:
            raise UserError(_("Cannot push task to Lark: related project is not linked to Lark."))
        if not self.user_access_token:
            raise UserError(_("User access token is required to push tasks to Lark."))

        headers = {"Authorization": f"Bearer {self.user_access_token}"}
        url = "https://open.larksuite.com/open-apis/project/v1/tasks" # Check if this is the correct URL for user-initiated task creation
        data = {
            "summary": task.name,
            "project_id": task.project_id.lark_id
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10).json()
            if response.get("code") == 0:
                task.lark_id = response["data"]["task_id"]
                _logger.info(f"Task '{task.name}' pushed to Lark with ID: {task.lark_id}")
            else:
                error_msg = f"Failed to push task to Lark: {response.get('msg', 'Unknown error')} (Code: {response.get('code')})"
                _logger.error(error_msg)
                raise UserError(_(error_msg))
        except requests.exceptions.RequestException as e:
            raise UserError(_("Error connecting to Lark API: %s") % str(e))
        if not task.project_id.lark_id:
            return
        token = self.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://open.larksuite.com/open-apis/project/v1/tasks"
        data = {
            "summary": task.name,
            "project_id": task.project_id.lark_id
        }
        response = requests.post(url, headers=headers, json=data).json()
        if response.get("code") == 0:
            task.lark_id = response["data"]["task_id"]

    def fetch_and_map_tasklists(self):
        """Fetch Lark tasklists and map them to Odoo projects by name. If a project with the same name exists, update its lark_id. If not, create a new project."""
        self.ensure_one()
        _logger.info("Fetching and mapping Lark tasklists to Odoo projects by name.")
        try:
            tasklists_url = "https://open.larksuite.com/open-apis/task/v2/tasklists"
            tasklists = self._get_paginated_results(tasklists_url)
            if not tasklists:
                _logger.info("No tasklists found in Lark.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Tasklists Found'),
                        'message': _('No tasklists were found in Lark.'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            mapped = 0
            created = 0
            for tasklist in tasklists:
                name = tasklist.get('name', 'Unnamed Tasklist')
                guid = tasklist.get('id')
                if not name or not guid:
                    continue
                # Try to find by name
                project = self.env['project.project'].search([('name', '=', name)], limit=1)
                if project:
                    # Update lark_id if not set
                    if not project.lark_id:
                        project.lark_id = guid
                        _logger.info(f"Mapped Lark tasklist '{name}' (guid={guid}) to existing Odoo project (id={project.id}).")
                        mapped += 1
                    else:
                        _logger.info(f"Odoo project '{name}' (id={project.id}) already mapped to Lark (lark_id={project.lark_id}).")
                else:
                    # Create new project
                    new_project = self.env['project.project'].create({
                        'name': name,
                        'lark_id': guid,
                        'description': tasklist.get('description', ''),
                    })
                    _logger.info(f"Created new Odoo project '{name}' (id={new_project.id}) for Lark tasklist (guid={guid}).")
                    created += 1
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Tasklists Mapped'),
                    'message': _(f"{mapped} projects mapped, {created} projects created from Lark tasklists."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_msg = _(f"Error during fetch and map: {str(e)}")
            _logger.error(error_msg, exc_info=True)
            raise UserError(error_msg) from e

    def log_json_to_chatter(self, json_data, subject="Lark API JSON Log"):
        """Post JSON data to the mail chatter for this record."""
        self.ensure_one()
        self.message_post(
            body=f"<pre>{json.dumps(json_data, indent=2, ensure_ascii=False)}</pre>",
            subject=subject
        )

    def fetch_and_store_tasklists(self):
        """Fetch Lark tasklists and store them as JSON in the tasklist_data field, and log the JSON in the mail chatter."""
        self.ensure_one()
        try:
            tasklists_url = "https://open.larksuite.com/open-apis/task/v2/tasklists"
            tasklists = self._get_paginated_results(tasklists_url)
            json_data = json.dumps(tasklists, indent=2, ensure_ascii=False)
            self.tasklist_data = json_data
            # Log in mail chatter using helper
            self.log_json_to_chatter(tasklists, subject="Fetched Lark Tasklists JSON")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Tasklists Fetched'),
                    'message': _('Fetched and stored Lark tasklists.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_msg = _(f"Error during fetch and store: {str(e)}")
            _logger.error(error_msg, exc_info=True)
            raise UserError(error_msg) from e

    def action_open_related_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Documents',
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'domain': [('model', '=', 'lark.api'), ('res_id', '=', self.id)],
            'context': dict(self.env.context, default_model='lark.api', default_res_id=self.id),
            'target': 'current',
        }

    def action_open_lark_tasklists(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lark Tasklists',
            'res_model': 'lark.tasklist',
            'view_mode': 'kanban,list,form',
            'views': [
                (False, 'kanban'),
                (False, 'list'),
                (False, 'form'),
            ],
            'target': 'current',
            'context': {},
        }

    def sync_lark_tasklists(self):
        # Fetch from Lark API (see: https://open.larksuite.com/document/uAjLw4CM/ukTMukTMukTM/task-v2/tasklist/list)
        tasklists = ...  # your API call
        for item in tasklists:
            vals = {
                'name': item.get('name'),
                'lark_guid': item.get('guid'),
                'url': item.get('url'),
                'creator_id': (item.get('creator') or {}).get('id'),
                'owner_id': (item.get('owner') or {}).get('id'),
                'created_at': lark_ms_to_odoo_datetime(item.get('created_at')),
                'updated_at': lark_ms_to_odoo_datetime(item.get('updated_at')),
                'json_data': json.dumps(item, ensure_ascii=False),
            }
            existing = self.env['project.task'].search([('lark_id', '=', vals['lark_id'])], limit=1)
            if existing:
                existing.write(vals)
            else:
                self.env['project.task'].create(vals)

    def action_open_lark_tasks(self):
        self.ensure_one()
        return {
            'name': _('Lark Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'lark.task',
            'view_mode': 'list,form',
            'domain': [('id', '!=', False)],  # Show all tasks for now
            'context': {
                'search_default_group_by_project': True
            },
            'target': 'current',
        }

    def action_start_lark_oauth(self):
        """Redirect user to Lark OAuth authorization URL (new endpoint)."""
        self.ensure_one()
        import secrets
        state = secrets.token_urlsafe(16)
        self.oauth_state = state
        params = {
            "app_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        base_url = "https://accounts.larksuite.com/open-apis/authen/v1/authorize"
        url = base_url + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_map_to_project(self):
        for tasklist in self:
            project = self.env['project.project'].search([('name', '=', tasklist.name)], limit=1)
            if project:
                tasklist.project_id = project.id

class ResCompany(models.Model):
    _inherit = 'res.company'
    lark_api_id = fields.Many2one('lark.api', string='Lark API')
    

class LarkOAuthController(http.Controller):
    @http.route('/lark/oauth/callback', type='http', auth='public')
    def lark_oauth_callback(self, **kwargs):
        code = kwargs.get('code')
        if not code:
            return "No code provided"
        # Exchange code for token
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(
            "https://accounts.larksuite.com/open-apis/authen/v1/authorize",
            json=payload
        )
        data = response.json()
        # Save access_token to your model (implement as needed)
        # ...
        return "Token received. You can close this window."
    

