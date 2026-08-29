import { ArrowRight, Droplet, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import type { DailyUsageRow, UsageSummaryCards } from "../../types/api";

interface AnomalyAlertsCardProps {
  summary: UsageSummaryCards | null;
  dailyRows: DailyUsageRow[];
}

interface Alert {
  kind: "water" | "energy";
  message: string;
  timestamp: string;
}

const ICONS = { water: Droplet, energy: Zap };
const ICON_STYLES = {
  water: "bg-blue-50 text-blue-600",
  energy: "bg-amber-50 text-amber-600",
};

/** Derive simple threshold-based anomaly alerts from real telemetry data. */
function deriveAlerts(summary: UsageSummaryCards | null, dailyRows: DailyUsageRow[]): Alert[] {
  const alerts: Alert[] = [];

  if (!summary || dailyRows.length === 0) return alerts;

  const avgWater = summary.avg_daily_water_L;
  const avgEnergy = summary.avg_daily_energy_kWh;

  // Check last two days for spikes (>20% above average)
  const recent = dailyRows.slice(-2);
  for (const row of recent) {
    if (avgWater > 0 && row.water_usage_L > avgWater * 1.2) {
      const pct = Math.round(((row.water_usage_L - avgWater) / avgWater) * 100);
      alerts.push({
        kind: "water",
        message: `Water usage is ${pct}% higher than the period average on ${row.date}.`,
        timestamp: row.date,
      });
    }
    if (avgEnergy > 0 && row.energy_usage_kWh > avgEnergy * 1.2) {
      const pct = Math.round(((row.energy_usage_kWh - avgEnergy) / avgEnergy) * 100);
      alerts.push({
        kind: "energy",
        message: `Energy usage is ${pct}% above average on ${row.date}.`,
        timestamp: row.date,
      });
    }
  }

  // WoW spike alert
  if ((summary.water_wow_pct ?? 0) > 15) {
    alerts.push({
      kind: "water",
      message: `Water usage up ${summary.water_wow_pct}% compared to last week.`,
      timestamp: "This week",
    });
  }
  if ((summary.energy_wow_pct ?? 0) > 15) {
    alerts.push({
      kind: "energy",
      message: `Energy usage up ${summary.energy_wow_pct}% compared to last week.`,
      timestamp: "This week",
    });
  }

  return alerts.slice(0, 3);
}

export function AnomalyAlertsCard({ summary, dailyRows }: AnomalyAlertsCardProps) {
  const alerts = deriveAlerts(summary, dailyRows);

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Anomaly Alerts</h3>
      {alerts.length === 0 ? (
        <p className="mt-3 flex-1 text-xs text-slate-400">No anomalies detected in the current period.</p>
      ) : (
        <ul className="mt-3 flex-1 space-y-4">
          {alerts.map((alert, i) => {
            const Icon = ICONS[alert.kind];
            return (
              <li key={i} className="flex gap-3">
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${ICON_STYLES[alert.kind]}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <div className="text-sm">
                  <p className="text-slate-700">{alert.message}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{alert.timestamp}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <Link
        to="/alerts"
        className="mt-4 flex items-center gap-1 text-sm font-medium text-emerald-600 hover:text-emerald-700"
      >
        View all alerts <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
