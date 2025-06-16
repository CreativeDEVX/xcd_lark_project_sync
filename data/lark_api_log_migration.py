def migrate(cr, version):
    cr.execute("""
        ALTER TABLE lark_api_log 
        ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES lark_api_log(id) ON DELETE CASCADE,
        ADD COLUMN IF NOT EXISTS has_children BOOLEAN DEFAULT FALSE;
    """)
