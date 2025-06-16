def uninstall_hook(env):
    """Uninstall hook to clean up related data when the module is uninstalled."""
    try:
        # Clean up Lark-related data
        env['lark.api'].search([]).unlink()
        env['lark.tasklist'].search([]).unlink()
        env['lark.task'].search([]).unlink()
        env['lark.api.log'].search([]).unlink()
        # Remove Lark fields from projects and tasks
        env.cr.execute("""
            ALTER TABLE project_project DROP COLUMN IF EXISTS lark_tasklist_id;
            ALTER TABLE project_project DROP COLUMN IF EXISTS lark_id;
            ALTER TABLE project_project DROP COLUMN IF EXISTS lark_parent_tasklist_guid;
            ALTER TABLE project_task DROP COLUMN IF EXISTS lark_id;
            ALTER TABLE project_task DROP COLUMN IF EXISTS lark_task_id;
            ALTER TABLE project_task DROP COLUMN IF EXISTS task_sequence;
        """)
    finally:
        # In Odoo's ORM, the transaction is usually managed at a higher level,
        # so explicit commit/close here might not be necessary or even desirable
        # unless you're absolutely sure it's required for standalone SQL execution.
        # If env.cr.execute commits implicitly, or if the overall Odoo process
        # manages the commit, this block might be redundant or problematic.
        # If you *must* commit here, consider using env.cr.commit() if available
        # or rely on the overall transaction management.
        pass # Or env.cr.commit() if appropriate