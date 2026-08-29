import { useQuery } from "@tanstack/react-query";
import { Droplet, Droplets, Leaf, Settings, Timer, TrendingUp, Zap } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { DailyUsageTable } from "../components/usage/DailyUsageTable";
import { UsageByBuildingChart } from "../components/usage/UsageByBuildingChart";
import { UsageTrendChart } from "../components/usage/UsageTrendChart";
import { StatCard } from "../components/overview/StatCard";
import { getActions, getUsage, getZones } from "../lib/apiClient";
import { classifyActionResource } from "../lib/actionResourceClassifier";

type ResourceTab = "water" | "energy";

const TAB_COLORS: Record<ResourceTab, string> = { water: "#3b82f6", energy: "#f59e0b" };

export function UsagePage() {
  const [tab, setTab] = useState<ResourceTab>("water");

  const query = useQuery({
    queryKey: ["usage"],
    queryFn: () => getUsage(),
  });

  const actionsQuery = useQuery({
    queryKey: ["actions-usage"],
    queryFn: () => getActions({ page: 1, pageSize: 100 }),
  });

  const zonesQuery = useQuery({
    queryKey: ["zones"],
    queryFn: getZones,
  });

  if (query.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading usage data...</p>;
  }
  if (query.isError || !query.data) {
    return (
      <p className="p-6 text-sm text-red-600">
        Failed to load usage data: {(query.error as Error)?.message}
      </p>
    );
  }

  const snapshot = query.data;
  const { summary } = snapshot;
  const series = snapshot.forecast_series.find((s) => s.resource === tab);
  const sparkFor = (s: typeof series) =>
    s ? s.data_points.map((p) => p.actual ?? p.forecast ?? 0) : [];

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Usage</h1>
          <p className="mt-1 text-sm text-slate-500">Track resource consumption and forecast future usage.</p>
        </div>
        <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
          {snapshot.period_start} – {snapshot.period_end}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Droplet}
          iconClassName="bg-blue-50 text-blue-600"
          label="Water Usage"
          value={`${summary.total_water_usage_L.toLocaleString()} L`}
          deltaLabel={`${Math.abs(summary.water_wow_pct ?? 0)}% vs last week`}
          deltaDirection={(summary.water_wow_pct ?? 0) <= 0 ? "down" : "up"}
          deltaGood={(summary.water_wow_pct ?? 0) <= 0}
          sparkline={sparkFor(snapshot.forecast_series.find((s) => s.resource === "water"))}
          sparklineColor="#3b82f6"
        />
        <StatCard
          icon={Zap}
          iconClassName="bg-amber-50 text-amber-600"
          label="Energy Usage"
          value={`${summary.total_energy_usage_kWh.toLocaleString()} kWh`}
          deltaLabel={`${Math.abs(summary.energy_wow_pct ?? 0)}% vs last week`}
          deltaDirection={(summary.energy_wow_pct ?? 0) <= 0 ? "down" : "up"}
          deltaGood={(summary.energy_wow_pct ?? 0) <= 0}
          sparkline={sparkFor(snapshot.forecast_series.find((s) => s.resource === "energy"))}
          sparklineColor="#f59e0b"
        />
        <StatCard
          icon={Leaf}
          iconClassName="bg-emerald-50 text-emerald-600"
          label="Waste Scanned"
          value={`${summary.total_waste_scanned} items`}
          deltaLabel={`${Math.abs(summary.waste_wow_pct ?? 0)}% vs last week`}
          deltaDirection={(summary.waste_wow_pct ?? 0) >= 0 ? "up" : "down"}
          deltaGood={(summary.waste_wow_pct ?? 0) >= 0}
          // No per-day waste-scan breakdown exists yet (only the period
          // total) — a flat line is honest; a derived trend would not be.
          sparkline={Array(7).fill(summary.total_waste_scanned)}
          sparklineColor="#10b981"
        />
        <StatCard
          icon={TrendingUp}
          iconClassName="bg-violet-50 text-violet-600"
          label="Avg Daily Usage"
          value={`${summary.avg_daily_water_L.toLocaleString()} L`}
          deltaLabel="daily average"
          deltaDirection="down"
          deltaGood
          sparkline={snapshot.daily_rows.map((r) => r.water_usage_L)}
          sparklineColor="#8b5cf6"
        />
      </div>

      {/* Action-derived resource cards */}
      {(() => {
        const allActions = actionsQuery.data?.items ?? [];
        const inProgress = allActions.filter((a) => a.status === "in_progress");
        const pending    = allActions.filter((a) => a.status === "pending");
        const sum = (arr: typeof allActions) => arr.reduce((s, a) => s + (a.estimated_monthly_impact ?? 0), 0);
        // Energy-tagged actions go to energy card; everything else (water/waste/general) → water card
        const ipWater  = inProgress.filter((a) => classifyActionResource(a) !== "energy");
        const ipEnergy = inProgress.filter((a) => classifyActionResource(a) === "energy");
        const pdWater  = pending.filter((a) => classifyActionResource(a) !== "energy");
        const pdEnergy = pending.filter((a) => classifyActionResource(a) === "energy");
        return (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={Droplets}
              iconClassName="bg-blue-50 text-blue-700"
              label="Water Current Usage"
              value={`₹${sum(ipWater).toLocaleString()}/mo`}
              deltaLabel={`${ipWater.length} in-progress action${ipWater.length !== 1 ? "s" : ""}`}
              deltaDirection="up"
              deltaGood={false}
              sparkline={ipWater.map((a) => a.estimated_monthly_impact ?? 0)}
              sparklineColor="#3b82f6"
            />
            <StatCard
              icon={Zap}
              iconClassName="bg-amber-50 text-amber-700"
              label="Energy Current Usage"
              value={`₹${sum(ipEnergy).toLocaleString()}/mo`}
              deltaLabel={`${ipEnergy.length} in-progress action${ipEnergy.length !== 1 ? "s" : ""}`}
              deltaDirection="up"
              deltaGood={false}
              sparkline={ipEnergy.map((a) => a.estimated_monthly_impact ?? 0)}
              sparklineColor="#f59e0b"
            />
            <StatCard
              icon={Timer}
              iconClassName="bg-sky-50 text-sky-600"
              label="Water Needed"
              value={`₹${sum(pdWater).toLocaleString()}/mo`}
              deltaLabel={`${pdWater.length} pending action${pdWater.length !== 1 ? "s" : ""}`}
              deltaDirection="down"
              deltaGood
              sparkline={pdWater.map((a) => a.estimated_monthly_impact ?? 0)}
              sparklineColor="#0ea5e9"
            />
            <StatCard
              icon={Timer}
              iconClassName="bg-violet-50 text-violet-600"
              label="Energy Needed"
              value={`₹${sum(pdEnergy).toLocaleString()}/mo`}
              deltaLabel={`${pdEnergy.length} pending action${pdEnergy.length !== 1 ? "s" : ""}`}
              deltaDirection="down"
              deltaGood
              sparkline={pdEnergy.map((a) => a.estimated_monthly_impact ?? 0)}
              sparklineColor="#8b5cf6"
            />
          </div>
        );
      })()}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex gap-2">
            {(["water", "energy"] as ResourceTab[]).map((r) => (
              <button
                key={r}
                onClick={() => setTab(r)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  tab === r ? "bg-brand-700 text-white" : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {r[0].toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
          <div className="mt-4">
            <UsageTrendChart series={series} color={TAB_COLORS[tab]} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Usage Summary (This Week)</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Total Water Usage</dt>
                <dd className="font-medium text-slate-900">
                  {summary.total_water_usage_L.toLocaleString()} L
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Total Energy Usage</dt>
                <dd className="font-medium text-slate-900">
                  {summary.total_energy_usage_kWh.toLocaleString()} kWh
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Peak Water Day</dt>
                <dd className="font-medium text-slate-900">
                  {summary.peak_water_day ?? "n/a"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Peak Energy Day</dt>
                <dd className="font-medium text-slate-900">
                  {summary.peak_energy_day ?? "n/a"}
                </dd>
              </div>
            </dl>
          </div>

          {series?.forecast_insight && (
            <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
              <h4 className="text-sm font-semibold text-emerald-800">Forecast Insight</h4>
              <p className="mt-1 text-xs text-emerald-700">{series.forecast_insight}</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Usage by Building (This Week)</h3>
            <Link
              to="/settings"
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-brand-700"
            >
              <Settings className="h-3 w-3" />
              Manage zones
            </Link>
          </div>
          <div className="mt-3">
            <UsageByBuildingChart
              buildings={snapshot.buildings}
              resource={tab}
              hasZones={(zonesQuery.data?.length ?? 0) > 0}
            />
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Daily Usage Table</h3>
          <div className="mt-3">
            <DailyUsageTable rows={snapshot.daily_rows} />
          </div>
        </div>
      </div>
    </div>
  );
}
