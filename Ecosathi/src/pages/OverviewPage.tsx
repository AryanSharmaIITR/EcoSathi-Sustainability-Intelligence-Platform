import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Droplet, Droplets, Leaf, Timer, Zap } from "lucide-react";
import { AnomalyAlertsCard } from "../components/overview/AnomalyAlertsCard";
import { FeatureStrip } from "../components/overview/FeatureStrip";
import { ImpactCard } from "../components/overview/ImpactCard";
import { OverviewTopBar } from "../components/overview/OverviewTopBar";
import { RecommendationsCard } from "../components/overview/RecommendationsCard";
import { ScanPanel } from "../components/overview/ScanPanel";
import { StatCard } from "../components/overview/StatCard";
import { UsageChart } from "../components/overview/UsageChart";
import { UsageSummaryCard } from "../components/overview/UsageSummaryCard";
import { getActions, getUsage } from "../lib/apiClient";
import { classifyActionResource } from "../lib/actionResourceClassifier";

export function OverviewPage() {
  const usageQuery = useQuery({
    queryKey: ["usage-overview"],
    queryFn: () => getUsage(),
  });

  const actionsQuery = useQuery({
    queryKey: ["actions-overview"],
    queryFn: () => getActions({ page: 1, pageSize: 100 }),
  });

  const snap = usageQuery.data;
  const summary = snap?.summary;
  const actionsStats = actionsQuery.data?.stats;

  // Build chart data from daily_rows
  const waterChartData = (snap?.daily_rows ?? []).map((r) => ({
    date: r.date,
    actual: r.water_usage_L,
    forecast: null as number | null,
  }));
  const energyChartData = (snap?.daily_rows ?? []).map((r) => ({
    date: r.date,
    actual: r.energy_usage_kWh,
    forecast: null as number | null,
  }));

  // Overlay forecast series if present
  if (snap?.forecast_series) {
    for (const series of snap.forecast_series) {
      const target = series.resource === "water" ? waterChartData : energyChartData;
      for (const pt of series.data_points) {
        const row = target.find((r) => r.date === pt.date);
        if (row && pt.forecast !== null) row.forecast = pt.forecast;
      }
    }
  }

  const waterWow = summary?.water_wow_pct ?? 0;
  const energyWow = summary?.energy_wow_pct ?? 0;
  const wasteWow = summary?.waste_wow_pct ?? 0;

  const isLoading = usageQuery.isLoading || actionsQuery.isLoading;

  return (
    <div className="grid grid-cols-1 gap-6 p-6 xl:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <OverviewTopBar
          periodStart={snap?.period_start}
          periodEnd={snap?.period_end}
        />

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading overview…</p>
        ) : (
          <>
            {/* Row 1 — core usage stats */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={Droplet}
                iconClassName="bg-blue-50 text-blue-600"
                label="Water Usage"
                value={`${(summary?.total_water_usage_L ?? 0).toLocaleString()} L`}
                deltaLabel={`${Math.abs(waterWow)}% vs last week`}
                deltaDirection={waterWow <= 0 ? "down" : "up"}
                deltaGood={waterWow <= 0}
                sparkline={snap?.daily_rows.map((r) => r.water_usage_L) ?? []}
                sparklineColor="#3b82f6"
              />
              <StatCard
                icon={Zap}
                iconClassName="bg-amber-50 text-amber-600"
                label="Energy Usage"
                value={`${(summary?.total_energy_usage_kWh ?? 0).toLocaleString()} kWh`}
                deltaLabel={`${Math.abs(energyWow)}% vs last week`}
                deltaDirection={energyWow <= 0 ? "down" : "up"}
                deltaGood={energyWow <= 0}
                sparkline={snap?.daily_rows.map((r) => r.energy_usage_kWh) ?? []}
                sparklineColor="#f59e0b"
              />
              <StatCard
                icon={Leaf}
                iconClassName="bg-emerald-50 text-emerald-600"
                label="Waste Scans"
                value={(summary?.total_waste_scanned ?? 0).toLocaleString()}
                deltaLabel={`${Math.abs(wasteWow)}% vs last week`}
                deltaDirection={wasteWow >= 0 ? "up" : "down"}
                deltaGood={wasteWow >= 0}
                sparkline={[]}
                sparklineColor="#10b981"
              />
              <StatCard
                icon={CheckCircle2}
                iconClassName="bg-emerald-50 text-emerald-600"
                label="Actions Completed"
                value={(actionsStats?.completed_count ?? 0).toLocaleString()}
                deltaLabel={`${actionsStats?.total_actions_wow ?? 0} this week`}
                deltaDirection="up"
                deltaGood
                sparkline={[]}
                sparklineColor="#10b981"
              />
            </div>

            {/* Row 2 — action-derived resource cards (all statuses, no category filter) */}
            {(() => {
              const allActions = actionsQuery.data?.items ?? [];
              const inProgress = allActions.filter((a) => a.status === "in_progress");
              const pending    = allActions.filter((a) => a.status === "pending");
              const sum = (arr: typeof allActions) => arr.reduce((s, a) => s + (a.estimated_monthly_impact ?? 0), 0);
              // Split in-progress by resource: water vs energy; others go to water card
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

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <UsageChart
                title="Water Usage"
                unit="L"
                deltaLabel={`${Math.abs(waterWow)}%`}
                deltaGood={waterWow <= 0}
                color="#3b82f6"
                data={waterChartData}
              />
              <UsageChart
                title="Energy Usage"
                unit="kWh"
                deltaLabel={`${Math.abs(energyWow)}%`}
                deltaGood={energyWow <= 0}
                color="#10b981"
                data={energyChartData}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <RecommendationsCard actions={actionsQuery.data?.items ?? []} />
              <AnomalyAlertsCard summary={summary ?? null} dailyRows={snap?.daily_rows ?? []} />
              <UsageSummaryCard summary={summary ?? null} periodLabel="Last 7 Days" />
            </div>
          </>
        )}

        <FeatureStrip />
      </div>

      <div className="space-y-4">
        <ScanPanel />
        <ImpactCard completedCount={actionsStats?.completed_count ?? 0} />
      </div>
    </div>
  );
}
