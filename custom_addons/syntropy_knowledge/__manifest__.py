{
    "name": "Syntropy Knowledge",
    "summary": "Centralize, manage, share and grow your knowledge library",
    "version": "18.0.1.0.0",
    "author": "Syntropy",
    "license": "LGPL-3",
    "category": "Productivity/Knowledge",
    "depends": [
        "base",
        "mail",
        "web",
        "web_editor",
        "html_editor",
        "hr",
        "portal",
    ],
    "external_dependencies": {
        "python": ["bs4"],
    },
    "data": [
        # security
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # data
        "data/ir_config_parameter_data.xml",
        "data/knowledge_article_stage_data.xml",
        "data/ir_actions_data.xml",
        "data/mail_templates.xml",
        # wizard
        "wizard/knowledge_invite_views.xml",
        # views
        "views/knowledge_article_views.xml",
        "views/knowledge_article_favorite_views.xml",
        "views/knowledge_article_member_views.xml",
        "views/knowledge_article_stage_views.xml",
        "views/knowledge_menus.xml",
        "views/article_public_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # SCSS
            "syntropy_knowledge/static/src/scss/knowledge_common.scss",
            "syntropy_knowledge/static/src/scss/knowledge_views.scss",
            "syntropy_knowledge/static/src/scss/knowledge_editor.scss",
            # JS - Core
            "syntropy_knowledge/static/src/js/knowledge_utils.js",
            "syntropy_knowledge/static/src/js/knowledge_views.js",
            "syntropy_knowledge/static/src/js/knowledge_controller.js",
            "syntropy_knowledge/static/src/js/knowledge_renderers.js",
            # JS - Components
            "syntropy_knowledge/static/src/components/sidebar/sidebar.js",
            "syntropy_knowledge/static/src/components/sidebar/sidebar_section.js",
            "syntropy_knowledge/static/src/components/sidebar/sidebar_row.js",
            "syntropy_knowledge/static/src/components/topbar/topbar.js",
            "syntropy_knowledge/static/src/components/permission_panel/permission_panel.js",
            "syntropy_knowledge/static/src/components/knowledge_cover/knowledge_cover.js",
            "syntropy_knowledge/static/src/components/knowledge_cover/knowledge_cover_dialog.js",
            "syntropy_knowledge/static/src/components/knowledge_icon/knowledge_icon.js",
            "syntropy_knowledge/static/src/components/comments/comments_panel.js",
            "syntropy_knowledge/static/src/components/move_article_dialog/move_article_dialog.js",
            # XML Templates
            "syntropy_knowledge/static/src/xml/knowledge_controller.xml",
            "syntropy_knowledge/static/src/components/sidebar/sidebar.xml",
            "syntropy_knowledge/static/src/components/sidebar/sidebar_section.xml",
            "syntropy_knowledge/static/src/components/sidebar/sidebar_row.xml",
            "syntropy_knowledge/static/src/components/topbar/topbar.xml",
            "syntropy_knowledge/static/src/components/permission_panel/permission_panel.xml",
            "syntropy_knowledge/static/src/components/knowledge_cover/knowledge_cover.xml",
            "syntropy_knowledge/static/src/components/knowledge_cover/knowledge_cover_dialog.xml",
            "syntropy_knowledge/static/src/components/knowledge_icon/knowledge_icon.xml",
            "syntropy_knowledge/static/src/components/comments/comments_panel.xml",
            "syntropy_knowledge/static/src/components/move_article_dialog/move_article_dialog.xml",
            # Lib
            "syntropy_knowledge/static/lib/html2pdf.bundle.min.js",
        ],
        "web.assets_frontend": [
            "syntropy_knowledge/static/src/scss/knowledge_public.scss",
        ],
    },
    "installable": True,
    "application": True,
}
