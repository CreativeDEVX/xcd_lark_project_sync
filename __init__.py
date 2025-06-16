import logging
from odoo import api, SUPERUSER_ID

from . import models
from . import wizards

_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry):
    """Post init hook to add Lark fields to project.task"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Running post-init hook for Lark Project Sync")
    
    # Add Lark fields to project.task
    cr.execute("""
        ALTER TABLE project_task
        ADD COLUMN IF NOT EXISTS lark_id VARCHAR,
        ADD COLUMN IF NOT EXISTS lark_guid VARCHAR,
        ADD COLUMN IF NOT EXISTS lark_etag VARCHAR,
        ADD COLUMN IF NOT EXISTS lark_updated TIMESTAMP;
    """)
    
    # Add index on lark_id for faster lookups
    cr.execute("""
        CREATE INDEX IF NOT EXISTS project_task_lark_id_idx 
        ON project_task (lark_id);
    """)

def uninstall_hook(cr, registry):
    """Uninstall hook to clean up Lark fields"""
    _logger.info("Running uninstall hook for Lark Project Sync")
    
    # Remove the index
    cr.execute("""
        DROP INDEX IF EXISTS project_task_lark_id_idx;
    """)
    
    # Note: We don't drop the columns here to prevent data loss in case of accidental uninstall