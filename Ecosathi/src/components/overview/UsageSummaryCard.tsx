import { Calendar, Droplet, TrendingUp, Zap } from "lucide-react";
import type { UsageSummaryCards } from "../../types/api";

interface UsageSummaryCardProps {
  summary: UsageSummaryCards | null;
  periodLabel?: string;
}

function deltaBadge(pct: number | null, lowerIsGood = true) {
  if (pct === null) return null;
  const good = lowerIsGood ? pct <= 0 : pct >= 0;
  const arrow = pct <= 0 ? "↓" : "↑";
  return (
    <span className={`text-xs ${good ? "text-emerald-600" : "text-red-500"}`}>
      {arrow} {Math.abs(pct)}%
    </span>
  );
}

export function UsageSummaryCard({ summary, periodLabel = "This Week" }: UsageSummaryCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Usage Summary</h3>
        <span className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500">
          {periodLabel}
        </span>
      </div>
      <dl className="mt-3 space-y-3 text-sm">
        <div className="flex items-center justify-between">
          <dt className="flex items-center gap-2 text-slate-600">
            <Droplet className="h-4 w-4 text-blue-500" /> Water Usage
          </dt>
          <dd className="flex items-center gap-2">
            <span className="font-medium text-slate-900">
              {summary ? `${summary.total_water_usage_L.toLocaleString()} L` : "—"}
            </span>
            {deltaBadge(summary?.water_wow_pct ?? null)}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="flex items-center gap-2 text-slate-600">
            <Zap className="h-4 w-4 text-amber-500" /> Energy Usage
          </dt>
          <dd className="flex items-center gap-2">
            <span className="font-medium text-slate-900">
              {summary ? `${summary.total_energy_usage_kWh.toLocaleString()} kWh` : "—"}
            </span>
            {deltaBadge(summary?.energy_wow_pct ?? null)}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="flex items-center gap-2 text-slate-600">
            <TrendingUp className="h-4 w-4 text-slate-400" /> Avg. Daily Water
          </dt>
          <dd className="font-medium text-slate-900">
            {summary ? `${summary.avg_daily_water_L.toLocaleString()} L` : "—"}
          </dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="flex items-center gap-2 text-slate-600">
            <Calendar className="h-4 w-4 text-slate-400" /> Peak Water Day
          </dt>
          <dd className="font-medium text-slate-900">
            {summary?.peak_water_day
              ? `${summary.peak_water_day} · ${summary.peak_water_day_L?.toLocaleString()} L`
              : "—"}
          </dd>
        </div>
      </dl>
    </div>
  );
}
