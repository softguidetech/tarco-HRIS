/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const COLORS = ["#13A89E", "#E8902A", "#0F2C4C", "#1A4370", "#EF4444", "#66788A", "#9FDCD5", "#8B5CF6"];

export class TarcoDashboardCharts extends Component {
    static template = "tarco_hris.DashboardCharts";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });
        this.charts = {};
        this.chartRefs = {
            statusDonut: useRef("statusDonut"),
            leaveDonut: useRef("leaveDonut"),
            dailyBar: useRef("dailyBar"),
            lateLine: useRef("lateLine"),
            payrollBar: useRef("payrollBar"),
            deptBar: useRef("deptBar"),
        };
        onWillStart(() => this.loadData());
        onMounted(() => this.renderCharts());
        onWillUnmount(() => this.destroyCharts());
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call("tarco.hr.dashboard", "get_chart_data", []);
        this.state.loading = false;
    }

    async reload() {
        this.destroyCharts();
        await this.loadData();
        this.renderCharts();
    }

    openTiles() {
        this.action.doAction("tarco_hris.action_tarco_dashboard");
    }

    destroyCharts() {
        for (const key of Object.keys(this.charts)) {
            if (this.charts[key]) {
                try {
                    this.charts[key].destroy();
                } catch (_err) {
                    // canvas already gone
                }
                this.charts[key] = null;
            }
        }
    }

    _ctx(name) {
        const canvas = this.chartRefs[name]?.el;
        if (!canvas || typeof Chart === "undefined") {
            return null;
        }
        if (Chart.getChart) {
            const existing = Chart.getChart(canvas);
            if (existing) {
                existing.destroy();
            }
        }
        return canvas.getContext("2d");
    }

    _empty(ctx, ref, message) {
        if (!ctx) {
            return;
        }
        this.charts[ref] = new Chart(ctx, {
            type: "bar",
            data: { labels: [message], datasets: [{ data: [0], backgroundColor: "#D9E2EC" }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { display: false } } },
        });
    }

    renderCharts() {
        if (!this.state.data || typeof Chart === "undefined") {
            return;
        }
        const data = this.state.data;
        this._doughnut("statusDonut", data.attendance_status, "No attendance this month");
        this._doughnut("leaveDonut", data.leave_types, "No approved leave this month");
        this._histogram(data.attendance_daily);
        this._line(data.late_minutes);
        this._bar("payrollBar", data.payroll_mix, COLORS);
        if (data.is_hr) {
            this._bar("deptBar", data.departments, ["#0F2C4C"]);
        }
    }

    _doughnut(ref, series, emptyText) {
        const ctx = this._ctx(ref);
        if (!ctx) {
            return;
        }
        if (!series?.labels?.length) {
            this._empty(ctx, ref, emptyText);
            return;
        }
        this.charts[ref] = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: series.labels,
                datasets: [{ data: series.values, backgroundColor: COLORS, borderWidth: 0 }],
            },
            options: {
                cutout: "62%",
                plugins: { legend: { position: "bottom" } },
            },
        });
    }

    _histogram(series) {
        const ctx = this._ctx("dailyBar");
        if (!ctx) {
            return;
        }
        if (!series?.labels?.length) {
            this._empty(ctx, "dailyBar", "No daily attendance");
            return;
        }
        this.charts.dailyBar = new Chart(ctx, {
            type: "bar",
            data: {
                labels: series.labels,
                datasets: [
                    { label: "Present", data: series.present, backgroundColor: "#13A89E" },
                    { label: "Late", data: series.late, backgroundColor: "#E8902A" },
                    { label: "Absent", data: series.absent, backgroundColor: "#EF4444" },
                ],
            },
            options: {
                responsive: true,
                scales: { x: { stacked: false }, y: { beginAtZero: true, ticks: { precision: 0 } } },
            },
        });
    }

    _line(series) {
        const ctx = this._ctx("lateLine");
        if (!ctx) {
            return;
        }
        if (!series?.labels?.length) {
            this._empty(ctx, "lateLine", "No lateness this month");
            return;
        }
        this.charts.lateLine = new Chart(ctx, {
            type: "line",
            data: {
                labels: series.labels,
                datasets: [{
                    label: "Late minutes",
                    data: series.values,
                    borderColor: "#0F2C4C",
                    backgroundColor: "rgba(19, 168, 158, 0.18)",
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: { scales: { y: { beginAtZero: true } } },
        });
    }

    _bar(ref, series, colors) {
        const ctx = this._ctx(ref);
        if (!ctx) {
            return;
        }
        if (!series?.labels?.length) {
            this._empty(ctx, ref, "No data");
            return;
        }
        this.charts[ref] = new Chart(ctx, {
            type: "bar",
            data: {
                labels: series.labels,
                datasets: [{ data: series.values, backgroundColor: colors, borderRadius: 6 }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } },
            },
        });
    }
}

registry.category("actions").add("tarco_hris.dashboard_charts", TarcoDashboardCharts);
