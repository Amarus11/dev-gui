/** @odoo-module */

import { Component, useState, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { computeElapsedSeconds, formatAdaptiveTimer } from "@project_timesheet_time_control/utils/timer_utils";

export class LiveTimerField extends Component {
    static template = "project_timesheet_time_control.LiveTimerField";
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
            // Defer to let OWL update the record data
            setTimeout(() => this._sync(), 0);
        });

        onWillUnmount(() => {
            this._stopTicking();
        });
    }

    get isRunning() {
        const record = this.props.record;
        const unitAmount = record.data.unit_amount;
        const dateTime = record.data.date_time;
        return unitAmount === 0 && !!dateTime;
    }

    get dateTimeValue() {
        return this.props.record.data.date_time || false;
    }

    get unitAmount() {
        return this.props.record.data.unit_amount || 0;
    }

    _sync() {
        this._updateDisplay();
        if (this.isRunning) {
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
            // Not running: show standard float time format
            const val = this.unitAmount;
            if (val <= 0) {
                this.state.displayText = "0:00";
                return;
            }
            const negative = val < 0;
            const absVal = Math.abs(val);
            const hours = Math.floor(absVal);
            const minutes = Math.round((absVal - hours) * 60);
            this.state.displayText = `${negative ? "-" : ""}${hours}:${String(minutes).padStart(2, "0")}`;
        }
    }
}

export const liveTimerField = {
    component: LiveTimerField,
    supportedTypes: ["float"],
};

registry.category("fields").add("live_timer", liveTimerField);
