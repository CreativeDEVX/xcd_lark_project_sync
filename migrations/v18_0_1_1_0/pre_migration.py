# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Add task_sequence field to project.task model"""
    # Add the task_sequence column
    cr.execute("""
        ALTER TABLE project_task
        ADD COLUMN IF NOT EXISTS task_sequence VARCHAR,
        ADD COLUMN IF NOT EXISTS task_sequence_prefix VARCHAR(3);
    """)
    
    # Add index on task_sequence for faster lookups
    cr.execute("""
        CREATE INDEX IF NOT EXISTS project_task_sequence_idx 
        ON project_task (task_sequence);
    """)
