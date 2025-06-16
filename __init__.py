import logging
from odoo import api, SUPERUSER_ID

from . import models
from . import wizards

_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry):
    """Post init hook to add Lark fields to models"""
    _logger.info('Adding parent_id and has_children fields to lark.api.log')
    cr.execute("""
        DO $$
        BEGIN
            -- Add parent_id column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='lark_api_log' AND column_name='parent_id') THEN
                ALTER TABLE lark_api_log 
                ADD COLUMN parent_id INTEGER REFERENCES lark_api_log(id) ON DELETE CASCADE;
            END IF;
            
            -- Add has_children column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='lark_api_log' AND column_name='has_children') THEN
                ALTER TABLE lark_api_log 
                ADD COLUMN has_children BOOLEAN DEFAULT FALSE;
            END IF;
        END
        $$;
    """)
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