import { Building2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { BuildingUsage } from "../../types/api";

interface UsageByBuildingChartProps {
  buildings: BuildingUsage[];
  resource: "water" | "energy";
  /** True when at least one zone is configured in Settings → Infrastructure */
  hasZones?: boolean;
}

export function UsageByBuildingChart({ buildings, resource, hasZones = false }: UsageByBuildingChartProps) {
  const key = resource === "water" ? "water_usage_L" : "energy_usage_kWh";
  const unit = resource === "water" ? "L" : "kWh";
  const sorted = [...buildings].sort((a, b) => b[key] - a[key]);

  if (sorted.length === 0) {
    // No zones configured at all — guide user to Settings
    if (!hasZones) {
      return (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <Building2 className="h-8 w-8 text-slate-300" />
          <p className="text-sm font-medium text-slate-500">No buildings configured yet.</p>
          <p className="max-w-xs text-xs text-slate-400">
            Add zones in{" "}
            <Link to="/settings" className="font-medium text-brand-700 underline underline-offset-2">
              Settings → Infrastructure
            </Link>{" "}
            to see per-building usage here.
          </p>
        </div>
      );
    }
    // Zones exist but no usage records for this period
    return (
      <p className="py-8 text-center text-sm text-slate-400">
        No usage records found for this period. Upload data via{" "}
        <span className="font-medium text-slate-600">Settings → Usage CSV</span> or the API.
      </p>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sorted} layout="vertical" margin={{ left: 20 }}>
          <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="building"
            tick={{ fontSize: 12, fill: "#334155" }}
            axisLine={false}
            tickLine={false}
            width={100}
          />
          <Bar dataKey={key} fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-1 text-right text-xs text-slate-400">Values in {unit}</p>
    </div>
  );
}
