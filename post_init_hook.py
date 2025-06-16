import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry=None):
    """Post init hook to add Lark fields to models
    
    Args:
        cr: database cursor or Environment object
        registry: Odoo model registry (optional)
    """
    _logger.info('Running post_init_hook for xcd_lark_project_sync')
    
    try:
        # Handle both Environment and cursor parameters
        if hasattr(cr, 'cr'):  # cr is actually an Environment object
            env = cr
            cr = env.cr
        else:
            env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Add parent_id and has_children columns to lark_api_log
        _logger.info('Adding parent_id and has_children fields to lark.api.log')
        cr.execute("""
            ALTER TABLE lark_api_log 
            ADD COLUMN IF NOT EXISTS parent_id integer;
            ALTER TABLE lark_api_log 
            ADD COLUMN IF NOT EXISTS has_children boolean DEFAULT false;
        """)
        
        # Update has_children flag for existing records
        cr.execute("""
            UPDATE lark_api_log SET has_children = true
            WHERE id IN (
                SELECT DISTINCT parent_id FROM lark_api_log
                WHERE parent_id IS NOT NULL
            );
        """)
        
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
        
        _logger.info("Successfully ran post-init hook for Lark Project Sync")
        
    except Exception as e:
        _logger.error(f"Error in post_init_hook: {str(e)}")
        _logger.error("Traceback:", exc_info=True)
        raise