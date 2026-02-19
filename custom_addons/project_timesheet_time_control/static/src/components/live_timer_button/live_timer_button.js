/** @odoo-module */

import { Component, useState, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { computeElapsedSeconds, formatAdaptiveTimer } from "@project_timesheet_time_control/utils/timer_utils";

export class LiveTimerButtonField extends Component {
    static template = "project_timesheet_time_control.LiveTimerButtonField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({
            displayText: "",
        });
        this._intervalId = null;

        onMounted(() => {
            this._sync();
        });

        onWillUpdateProps(() => {
            this._stopTicking();
            setTimeout(() => this._sync(), 0);
        });

        onWillUnmount(() => {
            this._stopTicking();
        });
    }

    get isRunning() {
        const stc = this.props.record.data.show_time_control;
        return stc === "stop";
    }

    get dateTimeValue() {
        return this.props.record.data.running_timer_date_time || false;
    }

    _sync() {
        this._updateDisplay();
        if (this.isRunning && this.dateTimeValue) {
            this._startTicking();
        }
    }

    _startTicking() {
        this._stopTicking();
        this._intervalId = setInterval(() => {
            this._updateDisplay();
        }, 1000);
    }

    _stopTicking() {
        if (this._intervalId) {
            clearInterval(this._intervalId);
            this._intervalId = null;
        }
    }

    _updateDisplay() {
        if (this.isRunning && this.dateTimeValue) {
            const elapsed = computeElapsedSeconds(this.dateTimeValue);
            this.state.displayText = formatAdaptiveTimer(elapsed);
        } else {
            this.state.displayText = "";
        }
    }
}

export const liveTimerButtonField = {
    component: LiveTimerButtonField,
    supportedTypes: ["datetime"],
};

registry.category("fields").add("live_timer_button", liveTimerButtonField);
