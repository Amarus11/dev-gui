# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import api, fields, models, tools


class TimesheetTimeReport(models.Model):
    _name = "timesheet.time.report"
    _description = "Timesheet Time Analysis Report"
    _auto = False
    _order = "date desc"

    date = fields.Date(string="Date", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    unit_amount = fields.Float(string="Duration (Hours)", readonly=True)
    date_time = fields.Datetime(string="Start Time", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    department_id = fields.Many2one(
        "hr.department", string="Department", readonly=True
    )
    day_of_week = fields.Char(string="Day of Week", readonly=True)
    week_number = fields.Integer(string="Week Number", readonly=True)
    month = fields.Selection(
        [
            ("01", "January"),
            ("02", "February"),
            ("03", "March"),
            ("04", "April"),
            ("05", "May"),
            ("06", "June"),
            ("07", "July"),
            ("08", "August"),
            ("09", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        readonly=True,
    )
    quarter = fields.Selection(
        [("1", "Q1"), ("2", "Q2"), ("3", "Q3"), ("4", "Q4")],
        string="Quarter",
        readonly=True,
    )
    year = fields.Integer(string="Year", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    aal.id AS id,
                    aal.date AS date,
                    aal.employee_id AS employee_id,
                    aal.user_id AS user_id,
                    aal.project_id AS project_id,
                    aal.task_id AS task_id,
                    aal.unit_amount AS unit_amount,
                    aal.date_time AS date_time,
                    aal.company_id AS company_id,
                    emp.department_id AS department_id,
                    trim(to_char(aal.date, 'Day')) AS day_of_week,
                    EXTRACT(WEEK FROM aal.date)::integer AS week_number,
                    to_char(aal.date, 'MM') AS month,
                    EXTRACT(QUARTER FROM aal.date)::text AS quarter,
                    EXTRACT(YEAR FROM aal.date)::integer AS year
                FROM account_analytic_line aal
                LEFT JOIN hr_employee emp ON emp.id = aal.employee_id
                WHERE aal.project_id IS NOT NULL
            )
        """
            % self._table
        )

    @api.model
    def get_dashboard_data(self):
        """Return aggregated data for the timesheet dashboard."""
        user = self.env.user
        today = fields.Date.context_today(self)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        base_domain = [("project_id", "!=", False)]
        if not user.has_group("hr_timesheet.group_timesheet_manager"):
            base_domain.append(("user_id", "=", user.id))

        # Today total
        today_domain = base_domain + [("date", "=", today)]
        today_data = self.read_group(today_domain, ["unit_amount"], [])
        today_total = today_data[0]["unit_amount"] if today_data else 0

        # Week total
        week_domain = base_domain + [
            ("date", ">=", week_start),
            ("date", "<=", today),
        ]
        week_data = self.read_group(week_domain, ["unit_amount"], [])
        week_total = week_data[0]["unit_amount"] if week_data else 0

        # Month total
        month_domain = base_domain + [
            ("date", ">=", month_start),
            ("date", "<=", today),
        ]
        month_data = self.read_group(month_domain, ["unit_amount"], [])
        month_total = month_data[0]["unit_amount"] if month_data else 0

        # Quarter
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        quarter_start = today.replace(month=quarter_month, day=1)
        quarter_domain = base_domain + [
            ("date", ">=", quarter_start),
            ("date", "<=", today),
        ]
        quarter_data = self.read_group(quarter_domain, ["unit_amount"], [])
        quarter_total = quarter_data[0]["unit_amount"] if quarter_data else 0

        # Year
        year_start = today.replace(month=1, day=1)
        year_domain = base_domain + [
            ("date", ">=", year_start),
            ("date", "<=", today),
        ]
        year_data = self.read_group(year_domain, ["unit_amount"], [])
        year_total = year_data[0]["unit_amount"] if year_data else 0

        # Project breakdown for this month
        breakdown_data = self.read_group(
            month_domain,
            ["unit_amount", "project_id", "task_id"],
            ["project_id", "task_id"],
            lazy=False,
        )
        breakdown = []
        for item in breakdown_data:
            proj_id = item["project_id"][0] if item["project_id"] else 0
            task_id = item["task_id"][0] if item["task_id"] else 0
            breakdown.append(
                {
                    "id": f"{proj_id}_{task_id}",
                    "project_name": (
                        item["project_id"][1] if item["project_id"] else ""
                    ),
                    "task_name": item["task_id"][1] if item["task_id"] else "",
                    "hours": item["unit_amount"] or 0,
                    "percentage": (
                        round((item["unit_amount"] or 0) / month_total * 100, 1)
                        if month_total
                        else 0
                    ),
                }
            )
        breakdown.sort(key=lambda x: x["hours"], reverse=True)

        # Daily breakdown for the current week (for chart)
        daily_data = self.read_group(
            week_domain,
            ["unit_amount", "date"],
            ["date:day"],
            lazy=False,
        )
        daily_breakdown = []
        for item in daily_data:
            daily_breakdown.append(
                {
                    "date": item["date:day"],
                    "hours": item["unit_amount"] or 0,
                }
            )

        return {
            "today_total": today_total or 0,
            "week_total": week_total or 0,
            "month_total": month_total or 0,
            "quarter_total": quarter_total or 0,
            "year_total": year_total or 0,
            "project_breakdown": breakdown,
            "daily_breakdown": daily_breakdown,
        }
