# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Add Lark-related fields to project.task model"""
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
