{
    "name": "Lark Project Sync",
    "version": "1.0",
    "depends": ["project", "base_setup", "web"],
    "data": [
        "security/ir.model.access.csv",
        "security/lark_security.xml",
        "wizards/link_project_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/lark_api_views.xml",
        "views/project_views.xml",
        "views/lark_tasklist_views.xml",
        "views/assets.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "lark_project_sync/static/src/js/many2one_autocomplete.js",
        ],
        "web.assets_qweb": [
            "lark_project_sync/static/src/xml/many2one_autocomplete.xml",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}