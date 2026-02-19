/** @odoo-module */

import { Component, useState, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { computeElapsedSeconds, formatAdaptiveTimer } from "@project_timesheet_time_control/utils/timer_utils";

export class LiveTimer extends Component {
    static template = "project_timesheet_time_control.LiveTimer";
    static props = {
        dateTime: { type: [String, Object, Boolean], optional: true },
        isRunning: { type: Boolean, optional: true },
        staticValue: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({
            displayText: "",
        });
        this._intervalId = null;

        onMounted(() => {
            this._updateDisplay();
            if (this.props.isRunning && this.props.dateTime) {
                this._startTicking();
            }
        });

        onWillUpdateProps((nextProps) => {
            this._stopTicking();
            if (nextProps.isRunning && nextProps.dateTime) {
                this._startTicking();
            }
        });

        onWillUnmount(() => {
            this._stopTicking();
        });
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
        if (this.props.isRunning && this.props.dateTime) {
            const elapsed = computeElapsedSeconds(this.props.dateTime);
            this.state.displayText = formatAdaptiveTimer(elapsed);
        } else if (this.props.staticValue) {
            const totalSec = Math.round(this.props.staticValue * 3600);
            this.state.displayText = formatAdaptiveTimer(totalSec);
        } else {
            this.state.displayText = "0s";
        }
    }
}
