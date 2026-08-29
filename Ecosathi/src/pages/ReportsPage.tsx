import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Download, FileText, Leaf, Sparkles } from "lucide-react";
import { useState } from "react";
import { exportReportUrl, generateReport, getReports } from "../lib/apiClient";
import { StatCard } from "../components/overview/StatCard";
import type { ReportType } from "../types/api";

const REPORT_TYPES: ReportType[] = ["sustainability", "water", "energy", "waste", "emissions"];

function defaultPeriod() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

export function ReportsPage() {
  const period = defaultPeriod();
  const [reportType, setReportType] = useState<ReportType>("sustainability");
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["reports"],
    queryFn: getReports,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      generateReport({ report_type: reportType, period_start: period.start, period_end: period.end }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });

  if (query.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading reports...</p>;
  }
  if (query.isError || !query.data) {
    return (
      <p className="p-6 text-sm text-red-600">Failed to load reports: {(query.error as Error)?.message}</p>
    );
  }

  const { stats, items } = query.data;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Reports</h1>
          <p className="mt-1 text-sm text-slate-500">Generate and download sustainability reports and insights.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value as ReportType)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600"
          >
            {REPORT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            {generateMutation.isPending ? "Generating..." : "Generate Report"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          icon={FileText}
          iconClassName="bg-emerald-50 text-emerald-600"
          label="Reports Generated"
          value={String(stats.reports_generated)}
          deltaLabel="all time"
          deltaDirection="up"
          deltaGood
          sparkline={[stats.reports_generated]}
          sparklineColor="#10b981"
        />
        <StatCard
          icon={Download}
          iconClassName="bg-blue-50 text-blue-600"
          label="Downloads"
          value={String(stats.total_downloads)}
          deltaLabel="all time"
          deltaDirection="up"
          deltaGood
          sparkline={[stats.total_downloads]}
          sparklineColor="#3b82f6"
        />
        <StatCard
          icon={BarChart3}
          iconClassName="bg-violet-50 text-violet-600"
          label="Data Points Analyzed"
          value={stats.data_points_analyzed.toLocaleString()}
          deltaLabel="usage + audit rows"
          deltaDirection="up"
          deltaGood
          sparkline={[stats.data_points_analyzed]}
          sparklineColor="#8b5cf6"
        />
        <StatCard
          icon={Sparkles}
          iconClassName="bg-amber-50 text-amber-600"
          label="Insights Generated"
          value={String(stats.insights_generated)}
          deltaLabel="recommend calls"
          deltaDirection="up"
          deltaGood
          sparkline={[stats.insights_generated]}
          sparklineColor="#f59e0b"
        />
        <StatCard
          icon={Leaf}
          iconClassName="bg-emerald-50 text-emerald-600"
          label="CO2 Avoided"
          value={`${stats.co2_avoided_kg} kg`}
          deltaLabel="estimated"
          deltaDirection="up"
          deltaGood
          sparkline={[stats.co2_avoided_kg]}
          sparklineColor="#10b981"
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Reports Library</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500">
                <th className="py-2 font-medium">Type</th>
                <th className="py-2 font-medium">Period</th>
                <th className="py-2 font-medium">Generated On</th>
                <th className="py-2 font-medium">Downloads</th>
                <th className="py-2 font-medium">Export</th>
              </tr>
            </thead>
            <tbody>
              {items.map((report) => (
                <tr key={report.id} className="border-b border-slate-100">
                  <td className="py-2.5 capitalize text-slate-800">{report.report_type}</td>
                  <td className="py-2.5 text-slate-600">
                    {report.period_start} – {report.period_end}
                  </td>
                  <td className="py-2.5 text-slate-500">{new Date(report.created_at).toLocaleString()}</td>
                  <td className="py-2.5 text-slate-600">{report.download_count}</td>
                  <td className="py-2.5">
                    <a
                      href={exportReportUrl(report.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-emerald-600 hover:text-emerald-700"
                    >
                      <Download className="h-3.5 w-3.5" /> CSV
                    </a>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    No reports generated yet — pick a type above and click Generate Report.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
