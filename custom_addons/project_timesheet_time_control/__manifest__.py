# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2016 Tecnativa - Sergio Teruel
# Copyright 2016-2018 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Project timesheet time control",
    "version": "18.0.2.0.0",
    "category": "Project",
    "author": "Tecnativa," "Odoo Community Association (OCA)",
    "maintainers": ["victoralmau"],
    "website": "https://github.com/OCA/project",
    "depends": [
        "hr_timesheet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/timesheet_report_security.xml",
        "report/timesheet_report_view.xml",
        "views/account_analytic_line_view.xml",
        "views/project_project_view.xml",
        "views/project_task_view.xml",
        "views/timesheet_report_menu.xml",
        "wizards/hr_timesheet_switch_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_timesheet_time_control/static/src/utils/*.js",
            "project_timesheet_time_control/static/src/components/**/*.js",
            "project_timesheet_time_control/static/src/components/**/*.xml",
            "project_timesheet_time_control/static/src/components/**/*.scss",
            "project_timesheet_time_control/static/src/fields/*.js",
            "project_timesheet_time_control/static/src/fields/*.xml",
            "project_timesheet_time_control/static/src/dashboard/*.js",
            "project_timesheet_time_control/static/src/dashboard/*.xml",
            "project_timesheet_time_control/static/src/dashboard/*.scss",
        ],
    },
    "license": "AGPL-3",
    "installable": True,
    "post_init_hook": "post_init_hook",
}
