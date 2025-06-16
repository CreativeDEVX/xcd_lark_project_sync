{
    "name": "Lark Project Sync",
    "version": "18.0.1.1.3",
    "post_init_hook": "post_init_hook",
    "summary": "Synchronize Odoo Projects with Lark Tasks",
    "description": """
        This module integrates Odoo Projects with Lark Tasks, allowing you to:
        - Sync projects and tasks between Odoo and Lark
        - Manage Lark tasks directly from Odoo
        - Track task status, assignees, and due dates
    """,
    "category": "Project/Lark",
    "author": "Creative Dev Co.,Ltd.",
    "website": "https://www.creativedev.co.th",
    "depends": [
        "project", 
        "base_setup", 
        "web",
        "mail"
    ],
    "data": [
        # Security
        'security/ir.model.access.csv',
        'security/lark_security.xml',
        
        # Wizards
        'wizards/link_project_wizard_views.xml',
        
        # Views
        'views/res_config_settings_views.xml',
        'views/lark_api_views.xml',
        'views/project_views.xml',
        'views/lark_tasklist_views.xml',
        'views/lark_task_views.xml',
        'views/lark_api_log_views.xml',
        'views/lark_menus.xml',
        'views/assets.xml',
        
        # Data
        'data/mail_data.xml',
        # 'data/ir_cron.xml',
    ],
    "demo": [
        'demo/lark_task_demo.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "web/static/lib/fontawesome/css/font-awesome.css",
            "lark_project_sync/static/src/scss/lark_project_sync.scss"
        ],
        "web.assets_backend_legacy_public": [
            "web/static/lib/fontawesome/css/font-awesome.css",
            "lark_project_sync/static/src/js/lark_project_sync.js"
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
    "external_dependencies": {
        "python": [
            "lark_oapi",
            "requests",
        ],
    },
    "summary": "Synchronize tasks between Odoo Projects and Lark Tasklists"
}