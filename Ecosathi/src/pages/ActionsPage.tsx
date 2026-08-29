import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, Droplets, IndianRupee, PlayCircle, Timer, X, Zap } from "lucide-react";
import { useState } from "react";
import { getActions, updateAction } from "../lib/apiClient";
import { StatCard } from "../components/overview/StatCard";
import type { ActionRead } from "../types/api";

const PRIORITY_PILL: Record<string, string> = {
  high: "bg-red-50 text-red-700",
  medium: "bg-amber-50 text-amber-700",
  low: "bg-slate-100 text-slate-600",
};

const STATUS_PILL: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  in_progress: "bg-blue-50 text-blue-700",
  completed: "bg-emerald-50 text-emerald-700",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
};

export function ActionsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [selected, setSelected] = useState<ActionRead | null>(null);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["actions", statusFilter],
    queryFn: () => getActions({ page: 1, pageSize: 50, status: statusFilter }),
  });

  const completeMutation = useMutation({
    mutationFn: (actionId: string) => updateAction(actionId, { status: "completed" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      setSelected(null);
    },
  });

  const inProgressMutation = useMutation({
    mutationFn: (actionId: string) => updateAction(actionId, { status: "in_progress" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      setSelected(null);
    },
  });

  if (query.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading actions...</p>;
  }
  if (query.isError || !query.data) {
    return (
      <p className="p-6 text-sm text-red-600">Failed to load actions: {(query.error as Error)?.message}</p>
    );
  }

  const { stats, items } = query.data;

  return (
    <div className="grid grid-cols-1 gap-6 p-6 xl:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Actions</h1>
          <p className="mt-1 text-sm text-slate-500">
            Recommended actions to improve sustainability and reduce costs.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            icon={CheckCircle2}
            iconClassName="bg-emerald-50 text-emerald-600"
            label="Total Actions"
            value={String(stats.total_actions)}
            deltaLabel={`${stats.total_actions_wow ?? 0} this week`}
            deltaDirection="up"
            deltaGood
            sparkline={[stats.total_actions]}
            sparklineColor="#10b981"
          />
          <StatCard
            icon={PlayCircle}
            iconClassName="bg-blue-50 text-blue-600"
            label="In Progress"
            value={String(stats.in_progress_count)}
            deltaLabel={`${stats.total_actions ? Math.round((stats.in_progress_count / stats.total_actions) * 100) : 0}% of total`}
            deltaDirection="up"
            deltaGood
            sparkline={[stats.in_progress_count]}
            sparklineColor="#3b82f6"
          />
          <StatCard
            icon={Clock}
            iconClassName="bg-amber-50 text-amber-600"
            label="Pending"
            value={String(stats.pending_count)}
            deltaLabel={`${stats.total_actions ? Math.round((stats.pending_count / stats.total_actions) * 100) : 0}% of total`}
            deltaDirection="down"
            deltaGood={false}
            sparkline={[stats.pending_count]}
            sparklineColor="#f59e0b"
          />
          <StatCard
            icon={CheckCircle2}
            iconClassName="bg-violet-50 text-violet-600"
            label="Completed"
            value={String(stats.completed_count)}
            deltaLabel={`${stats.total_actions ? Math.round((stats.completed_count / stats.total_actions) * 100) : 0}% of total`}
            deltaDirection="up"
            deltaGood
            sparkline={[stats.completed_count]}
            sparklineColor="#8b5cf6"
          />
          <StatCard
            icon={IndianRupee}
            iconClassName="bg-emerald-50 text-emerald-600"
            label="Est. Impact (Monthly)"
            value={`₹${stats.estimated_monthly_impact_total.toLocaleString()}`}
            deltaLabel="agent-estimated"
            deltaDirection="down"
            deltaGood
            sparkline={[stats.estimated_monthly_impact_total]}
            sparklineColor="#10b981"
          />
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex gap-2">
            {["all", "pending", "in_progress", "completed"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  statusFilter === s ? "bg-brand-700 text-white" : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                {s === "all" ? "All Actions" : STATUS_LABEL[s]}
              </button>
            ))}
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500">
                  <th className="py-2 font-medium">Action</th>
                  <th className="py-2 font-medium">Category</th>
                  <th className="py-2 font-medium">Priority</th>
                  <th className="py-2 font-medium">Status</th>
                  <th className="py-2 font-medium">Est. Impact</th>
                </tr>
              </thead>
              <tbody>
                {items.map((action) => (
                  <tr
                    key={action.id}
                    onClick={() => setSelected(action)}
                    className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="max-w-xs py-2.5 text-slate-800">{action.title}</td>
                    <td className="py-2.5 capitalize text-slate-600">{action.category}</td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_PILL[action.priority]}`}>
                        {action.priority}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_PILL[action.status]}`}>
                        {STATUS_LABEL[action.status]}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-600">
                      {action.estimated_monthly_impact !== null
                        ? `₹${action.estimated_monthly_impact.toLocaleString()}/mo`
                        : "n/a"}
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-400">
                      No actions yet — run a recommendation from the Scanner to generate some.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {selected ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between">
              <h3 className="text-sm font-semibold text-slate-900">Action Details</h3>
              <button onClick={() => setSelected(null)}>
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>
            <h4 className="mt-3 font-semibold text-slate-900">{selected.title}</h4>
            <p className="mt-2 text-sm text-slate-600">{selected.rationale}</p>
            <dl className="mt-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <dt className="text-slate-500">Category</dt>
                <dd className="font-medium capitalize text-slate-800">{selected.category}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Status</dt>
                <dd className="font-medium text-slate-800">{STATUS_LABEL[selected.status]}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Est. Monthly Impact</dt>
                <dd className="font-medium text-slate-800">
                  {selected.estimated_monthly_impact !== null
                    ? `₹${selected.estimated_monthly_impact.toLocaleString()}/mo`
                    : "n/a"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Source</dt>
                <dd className="font-medium text-slate-800">{selected.source}</dd>
              </div>
            </dl>

            {/* Water / Energy consumption derived from category + impact */}
            {(selected.category === "water" || selected.category === "energy") && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Resource Consumption
                </p>
                {selected.category === "water" && (
                  <div className="flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2">
                    <span className="flex items-center gap-2 text-xs text-blue-700">
                      <Droplets className="h-3.5 w-3.5" />
                      Water Usage
                    </span>
                    <span className="text-xs font-semibold text-blue-800">
                      {selected.estimated_monthly_impact !== null
                        ? `${Math.round((selected.estimated_monthly_impact / 0.05) * 30).toLocaleString()} L/mo`
                        : "n/a"}
                    </span>
                  </div>
                )}
                {selected.category === "energy" && (
                  <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2">
                    <span className="flex items-center gap-2 text-xs text-amber-700">
                      <Zap className="h-3.5 w-3.5" />
                      Energy Consumption
                    </span>
                    <span className="text-xs font-semibold text-amber-800">
                      {selected.estimated_monthly_impact !== null
                        ? `${Math.round((selected.estimated_monthly_impact / 8) * 30).toLocaleString()} kWh/mo`
                        : "n/a"}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* General / waste actions: show both water + energy estimates if impact known */}
            {(selected.category === "general" || selected.category === "waste") &&
              selected.estimated_monthly_impact !== null && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Resource Consumption
                </p>
                <div className="flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2">
                  <span className="flex items-center gap-2 text-xs text-blue-700">
                    <Droplets className="h-3.5 w-3.5" />
                    Water Usage
                  </span>
                  <span className="text-xs font-semibold text-blue-800">
                    {`${Math.round((selected.estimated_monthly_impact / 0.05) * 5).toLocaleString()} L/mo`}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2">
                  <span className="flex items-center gap-2 text-xs text-amber-700">
                    <Zap className="h-3.5 w-3.5" />
                    Energy Consumption
                  </span>
                  <span className="text-xs font-semibold text-amber-800">
                    {`${Math.round((selected.estimated_monthly_impact / 8) * 5).toLocaleString()} kWh/mo`}
                  </span>
                </div>
              </div>
            )}
            {selected.status !== "completed" && (
              <div className="mt-4 flex flex-col gap-2">
                {selected.status !== "in_progress" && (
                  <button
                    onClick={() => inProgressMutation.mutate(selected.id)}
                    disabled={inProgressMutation.isPending}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                  >
                    <Timer className="h-4 w-4" />
                    Mark as In Progress
                  </button>
                )}
                <button
                  onClick={() => completeMutation.mutate(selected.id)}
                  disabled={completeMutation.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-700 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Mark as Completed
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-400">
            Select an action to see details.
          </div>
        )}

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Overall Impact Summary</h3>
          <div className="mt-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Total Estimated Impact</span>
              <span className="font-medium text-slate-900">
                ₹{stats.estimated_monthly_impact_total.toLocaleString()}/mo
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
