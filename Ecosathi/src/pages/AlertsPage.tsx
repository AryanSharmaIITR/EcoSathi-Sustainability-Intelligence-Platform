import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import {
  acknowledgeAlert,
  evaluateAlerts,
  getAlerts,
  resolveAlert,
} from "../lib/apiClient";
import { StatCard } from "../components/overview/StatCard";
import type { AlertIncident, AlertSeverity, AlertStatus } from "../types/api";

// ── Severity config ──────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<
  AlertSeverity,
  { label: string; badgeClass: string; iconClass: string; Icon: React.ElementType }
> = {
  critical: {
    label: "CRITICAL",
    badgeClass: "bg-red-100 text-red-700",
    iconClass: "text-red-500",
    Icon: XCircle,
  },
  high: {
    label: "HIGH",
    badgeClass: "bg-orange-100 text-orange-700",
    iconClass: "text-orange-500",
    Icon: AlertTriangle,
  },
  warning: {
    label: "WARNING",
    badgeClass: "bg-amber-100 text-amber-700",
    iconClass: "text-amber-500",
    Icon: AlertTriangle,
  },
  info: {
    label: "INFO",
    badgeClass: "bg-blue-100 text-blue-700",
    iconClass: "text-blue-500",
    Icon: Info,
  },
};

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Alert card ───────────────────────────────────────────────────────────────

function AlertCard({ alert }: { alert: AlertIncident }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);

  const cfg = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info;
  const { Icon } = cfg;

  const ackMutation = useMutation({
    mutationFn: () => acknowledgeAlert(alert.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveAlert(alert.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div
      className={`rounded-xl border bg-white shadow-sm ${
        alert.status === "resolved"
          ? "border-slate-200 opacity-60"
          : alert.severity === "critical"
          ? "border-red-200"
          : alert.severity === "high"
          ? "border-orange-200"
          : "border-slate-200"
      }`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${cfg.iconClass}`} />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.badgeClass}`}
                >
                  {cfg.label}
                </span>
                {alert.building && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                    {alert.building}
                  </span>
                )}
                <span className="text-xs text-slate-400">{formatDate(alert.triggered_at)}</span>
              </div>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">{alert.title}</h3>
              <p className="mt-0.5 text-sm text-slate-600">{alert.message}</p>
              {alert.metric_actual != null && alert.metric_limit != null && (
                <p className="mt-1 text-xs text-slate-500">
                  Actual:{" "}
                  <span className="font-medium text-slate-800">
                    {alert.metric_actual.toLocaleString()} {alert.metric_unit}
                  </span>{" "}
                  · Limit:{" "}
                  <span className="font-medium text-slate-800">
                    {alert.metric_limit.toLocaleString()} {alert.metric_unit}
                  </span>
                </p>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                alert.status === "active"
                  ? "bg-red-50 text-red-600"
                  : alert.status === "acknowledged"
                  ? "bg-amber-50 text-amber-700"
                  : "bg-emerald-50 text-emerald-700"
              }`}
            >
              {alert.status}
            </span>
            {alert.ai_recommendation && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="flex items-center gap-1 text-xs text-brand-700 hover:underline"
              >
                AI Rec.
                {expanded ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Expanded AI recommendation */}
        {expanded && alert.ai_recommendation && (
          <div className="mt-3 rounded-lg bg-brand-100/60 px-4 py-3 text-sm text-brand-900">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
              AI Recommendation
            </p>
            <p>{alert.ai_recommendation}</p>
          </div>
        )}

        {/* Action buttons */}
        {alert.status !== "resolved" && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => ackMutation.mutate()}
              disabled={alert.status === "acknowledged" || ackMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50"
            >
              <Bell className="h-3.5 w-3.5" />
              {ackMutation.isPending ? "…" : "Acknowledge"}
            </button>
            <button
              onClick={() => resolveMutation.mutate()}
              disabled={resolveMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              {resolveMutation.isPending ? "…" : "Resolve"}
            </button>
          </div>
        )}
        {ackMutation.isError && (
          <p className="mt-1 text-xs text-red-600">{(ackMutation.error as Error).message}</p>
        )}
        {resolveMutation.isError && (
          <p className="mt-1 text-xs text-red-600">{(resolveMutation.error as Error).message}</p>
        )}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export function AlertsPage() {
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("all");
  const queryClient = useQueryClient();

  const alertsQuery = useQuery({
    queryKey: ["alerts", statusFilter],
    queryFn: () => getAlerts({ status: statusFilter }),
  });

  const evaluateMutation = useMutation({
    mutationFn: evaluateAlerts,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  if (alertsQuery.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading alerts…</p>;
  }
  if (alertsQuery.isError || !alertsQuery.data) {
    return (
      <p className="p-6 text-sm text-red-600">
        Failed to load alerts: {(alertsQuery.error as Error)?.message}
      </p>
    );
  }

  const { stats, items } = alertsQuery.data;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Alerts</h1>
          <p className="mt-1 text-sm text-slate-500">
            Dynamic threshold monitoring and anomaly detection across all facility constraints.
          </p>
        </div>
        <button
          onClick={() => evaluateMutation.mutate()}
          disabled={evaluateMutation.isPending}
          className="flex items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${evaluateMutation.isPending ? "animate-spin" : ""}`}
          />
          {evaluateMutation.isPending ? "Evaluating…" : "Evaluate Now"}
        </button>
      </div>

      {evaluateMutation.isError && (
        <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
          {(evaluateMutation.error as Error).message}
        </p>
      )}
      {evaluateMutation.isSuccess && evaluateMutation.data.length === 0 && (
        <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          ✓ No new alerts — all constraints within limits.
        </p>
      )}
      {evaluateMutation.isSuccess && evaluateMutation.data.length > 0 && (
        <p className="rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-700">
          ⚠ {evaluateMutation.data.length} new alert(s) triggered.
        </p>
      )}

      {/* Summary stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Bell}
          iconClassName="bg-slate-100 text-slate-600"
          label="Total Active"
          value={String(stats.total_active)}
          deltaLabel="open alerts"
          deltaDirection="down"
          deltaGood={stats.total_active === 0}
          sparkline={[stats.total_active]}
          sparklineColor="#64748b"
        />
        <StatCard
          icon={XCircle}
          iconClassName="bg-red-50 text-red-600"
          label="Critical"
          value={String(stats.critical_count)}
          deltaLabel="critical violations"
          deltaDirection="down"
          deltaGood={stats.critical_count === 0}
          sparkline={[stats.critical_count]}
          sparklineColor="#ef4444"
        />
        <StatCard
          icon={AlertTriangle}
          iconClassName="bg-orange-50 text-orange-600"
          label="High Severity"
          value={String(stats.high_count)}
          deltaLabel="high severity"
          deltaDirection="down"
          deltaGood={stats.high_count === 0}
          sparkline={[stats.high_count]}
          sparklineColor="#f97316"
        />
        <StatCard
          icon={AlertTriangle}
          iconClassName="bg-amber-50 text-amber-600"
          label="Warnings"
          value={String(stats.warning_count)}
          deltaLabel="warnings"
          deltaDirection="down"
          deltaGood={stats.warning_count === 0}
          sparkline={[stats.warning_count]}
          sparklineColor="#f59e0b"
        />
      </div>

      {/* Filter bar + alert feed */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        {/* Filter tabs */}
        <div className="flex gap-2 border-b border-slate-200 px-4 pt-3">
          {STATUS_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setStatusFilter(value as AlertStatus | "all")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                statusFilter === value
                  ? "bg-brand-700 text-white"
                  : "text-slate-500 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Alert feed */}
        <div className="p-4 space-y-3">
          {items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 py-12 text-center">
              <Bell className="mx-auto mb-3 h-8 w-8 text-slate-300" />
              <p className="text-sm text-slate-400">
                {statusFilter === "all"
                  ? 'No alerts yet. Click "Evaluate Now" to run constraint checks.'
                  : `No ${statusFilter} alerts.`}
              </p>
            </div>
          ) : (
            items.map((alert) => <AlertCard key={alert.id} alert={alert} />)
          )}
        </div>
      </div>
    </div>
  );
}
