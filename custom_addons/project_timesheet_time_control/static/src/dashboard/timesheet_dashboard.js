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
        const filterMap = {
            today: "filter_today",
            week: "filter_this_week",
            month: "filter_this_month",
            quarter: "filter_this_quarter",
            year: "filter_this_year",
        };
        const filterName = filterMap[period] || "filter_this_month";
        // Clear all default period filters, then activate only the requested one
        const ctx = {
            search_default_filter_today: 0,
            search_default_filter_this_week: 0,
            search_default_filter_this_month: 0,
            search_default_filter_this_quarter: 0,
            search_default_filter_this_year: 0,
            search_default_group_project: 1,
        };
        ctx[`search_default_${filterName}`] = 1;
        this.action.doAction(
            "project_timesheet_time_control.timesheet_time_report_action",
            { additionalContext: ctx }
        );
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("timesheet_time_control_dashboard", TimesheetDashboard);
