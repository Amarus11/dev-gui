/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@project_timesheet_time_control/utils/timer_utils";

export class TimesheetDashboard extends Component {
    static template = "project_timesheet_time_control.TimesheetDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            todayTotal: 0,
            weekTotal: 0,
            monthTotal: 0,
            quarterTotal: 0,
            yearTotal: 0,
            projectBreakdown: [],
            dailyBreakdown: [],
            loading: true,
            collapsedProjects: {},
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "timesheet.time.report",
                "get_dashboard_data",
                [],
            );
            this.state.todayTotal = data.today_total;
            this.state.weekTotal = data.week_total;
            this.state.monthTotal = data.month_total;
            this.state.quarterTotal = data.quarter_total;
            this.state.yearTotal = data.year_total;
            this.state.projectBreakdown = data.project_breakdown;
            this.state.dailyBreakdown = data.daily_breakdown;
        } catch (e) {
            console.error("Failed to load dashboard data:", e);
        }
        this.state.loading = false;
    }

    formatHours(val) {
        return formatFloatTime(val);
    }

    getGroupedBreakdown() {
        const groups = {};
        for (const row of this.state.projectBreakdown) {
            const key = row.project_name || '';
            if (!groups[key]) {
                groups[key] = {
                    project_name: key,
                    rows: [],
                    total_hours: 0,
                    total_percentage: 0,
                };
                // Collapse by default on first load
                if (!(key in this.state.collapsedProjects)) {
                    this.state.collapsedProjects[key] = true;
                }
            }
            groups[key].rows.push(row);
            groups[key].total_hours += row.hours;
            groups[key].total_percentage = Math.round(
                (groups[key].total_percentage * 10 + row.percentage * 10) / 10
            );
        }
        // Recalculate percentage properly
        for (const g of Object.values(groups)) {
            g.total_percentage = Math.round(g.rows.reduce((s, r) => s + r.percentage, 0) * 10) / 10;
        }
        return Object.values(groups).sort((a, b) => b.total_hours - a.total_hours);
    }

    toggleProjectGroup(projectName) {
        this.state.collapsedProjects[projectName] = !this.state.collapsedProjects[projectName];
    }

    getMaxDailyHours() {
        if (!this.state.dailyBreakdown.length) return 1;
        return Math.max(...this.state.dailyBreakdown.map((d) => d.hours), 1);
    }

    getDailyBarHeight(hours) {
        const maxBarPx = 170; // max bar height in pixels (fits within 220px container)
        const max = this.getMaxDailyHours();
        return Math.max(Math.round((hours / max) * maxBarPx), 4);
    }

    openAnalysis(period) {
        const { DateTime } = luxon;
        const now = DateTime.now();
        let domain = [];
        let name = "Timesheet Analysis";

        switch (period) {
            case "today":
                domain = [["date", "=", now.toFormat("yyyy-MM-dd")]];
                name = "Today's Timesheets";
                break;
            case "week": {
                const startOfWeek = now.startOf("week");
                const endOfWeek = now.endOf("week");
                domain = [
                    ["date", ">=", startOfWeek.toFormat("yyyy-MM-dd")],
                    ["date", "<=", endOfWeek.toFormat("yyyy-MM-dd")],
                ];
                name = "This Week's Timesheets";
                break;
            }
            case "month": {
                const startOfMonth = now.startOf("month");
                const endOfMonth = now.endOf("month");
                domain = [
                    ["date", ">=", startOfMonth.toFormat("yyyy-MM-dd")],
                    ["date", "<=", endOfMonth.toFormat("yyyy-MM-dd")],
                ];
                name = "This Month's Timesheets";
                break;
            }
            case "quarter": {
                const quarterMonth = Math.floor((now.month - 1) / 3) * 3 + 1;
                const startOfQuarter = DateTime.local(now.year, quarterMonth, 1);
                const endOfQuarter = startOfQuarter.plus({ months: 3 }).minus({ days: 1 });
                domain = [
                    ["date", ">=", startOfQuarter.toFormat("yyyy-MM-dd")],
                    ["date", "<=", endOfQuarter.toFormat("yyyy-MM-dd")],
                ];
                name = "This Quarter's Timesheets";
                break;
            }
            case "year": {
                domain = [
                    ["date", ">=", now.startOf("year").toFormat("yyyy-MM-dd")],
                    ["date", "<=", now.endOf("year").toFormat("yyyy-MM-dd")],
                ];
                name = "This Year's Timesheets";
                break;
            }
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "timesheet.time.report",
            views: [
                [false, "graph"],
                [false, "pivot"],
                [false, "list"],
            ],
            domain: domain,
            context: { search_default_group_project: 1 },
        });
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("timesheet_time_control_dashboard", TimesheetDashboard);
