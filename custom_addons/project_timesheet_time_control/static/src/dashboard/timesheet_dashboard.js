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

    getMaxDailyHours() {
        if (!this.state.dailyBreakdown.length) return 1;
        return Math.max(...this.state.dailyBreakdown.map((d) => d.hours), 1);
    }

    getDailyBarHeight(hours) {
        const max = this.getMaxDailyHours();
        return Math.max((hours / max) * 100, 2);
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
        this.action.doAction(
            "project_timesheet_time_control.timesheet_time_report_action",
            {
                additionalContext: {
                    [`search_default_${filterName}`]: 1,
                },
            }
        );
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("timesheet_time_control_dashboard", TimesheetDashboard);
