import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Leaf, Recycle, Search, Target, ScanLine } from "lucide-react";
import { useRef, useState } from "react";
import { ScanPanel } from "../components/overview/ScanPanel";
import { StatCard } from "../components/overview/StatCard";
import { getWasteScanHistory } from "../lib/apiClient";

const RESULT_LABEL: Record<string, string> = {
  recyclable: "Recyclable",
  compostable: "Compostable",
  landfill: "Non-Recyclable",
  hazardous: "Non-Recyclable",
  "e-waste": "Non-Recyclable",
};

// Colored by the displayed Result group (Recyclable/Compostable/Non-Recyclable),
// not the raw category — otherwise "Non-Recyclable" renders in three
// different colors depending on which category produced it.
const RESULT_PILL: Record<string, string> = {
  Recyclable: "bg-emerald-50 text-emerald-700",
  Compostable: "bg-green-50 text-green-700",
  "Non-Recyclable": "bg-red-50 text-red-700",
};

export function WasteScansPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const scanTriggerRef = useRef<(() => void) | null>(null);

  const query = useQuery({
    queryKey: ["waste-scan-history", page, search, category],
    queryFn: () => getWasteScanHistory({ page, pageSize: 10, search: search || undefined, category }),
  });

  if (query.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading scan history...</p>;
  }
  if (query.isError || !query.data) {
    return (
      <p className="p-6 text-sm text-red-600">
        Failed to load scan history: {(query.error as Error)?.message}
      </p>
    );
  }

  const { stats, items, total_pages } = query.data;

  return (
    <div className="grid grid-cols-1 gap-6 p-6 xl:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Waste Scans</h1>
          <p className="mt-1 text-sm text-slate-500">View all waste scans and get disposal guidance.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            icon={Target}
            iconClassName="bg-emerald-50 text-emerald-600"
            label="Total Scans"
            value={String(stats.total_scans)}
            deltaLabel={`${Math.abs(stats.total_scans_wow_pct ?? 0)}% vs last week`}
            deltaDirection={(stats.total_scans_wow_pct ?? 0) >= 0 ? "up" : "down"}
            deltaGood={(stats.total_scans_wow_pct ?? 0) >= 0}
            sparkline={[stats.total_scans]}
            sparklineColor="#10b981"
          />
          <StatCard
            icon={Recycle}
            iconClassName="bg-blue-50 text-blue-600"
            label="Recyclable"
            value={String(stats.recyclable_count)}
            deltaLabel={`${stats.total_scans ? Math.round((stats.recyclable_count / stats.total_scans) * 100) : 0}% of total`}
            deltaDirection="up"
            deltaGood
            sparkline={[stats.recyclable_count]}
            sparklineColor="#3b82f6"
          />
          <StatCard
            icon={Leaf}
            iconClassName="bg-amber-50 text-amber-600"
            label="Compostable"
            value={String(stats.compostable_count)}
            deltaLabel={`${stats.total_scans ? Math.round((stats.compostable_count / stats.total_scans) * 100) : 0}% of total`}
            deltaDirection="up"
            deltaGood
            sparkline={[stats.compostable_count]}
            sparklineColor="#f59e0b"
          />
          <StatCard
            icon={CheckCircle2}
            iconClassName="bg-red-50 text-red-600"
            label="Non-Recyclable"
            value={String(stats.non_recyclable_count)}
            deltaLabel={`${stats.total_scans ? Math.round((stats.non_recyclable_count / stats.total_scans) * 100) : 0}% of total`}
            deltaDirection="down"
            deltaGood={false}
            sparkline={[stats.non_recyclable_count]}
            sparklineColor="#ef4444"
          />
          <StatCard
            icon={Target}
            iconClassName="bg-violet-50 text-violet-600"
            label="Avg. Confidence"
            value={stats.avg_confidence !== null ? `${Math.round(stats.avg_confidence * 100)}%` : "n/a"}
            deltaLabel="across all scans"
            deltaDirection="up"
            deltaGood
            sparkline={[stats.avg_confidence ?? 0]}
            sparklineColor="#8b5cf6"
          />
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h2 className="text-sm font-semibold text-slate-900">Scan History</h2>
            <button
              type="button"
              onClick={() => scanTriggerRef.current?.()}
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              <ScanLine className="h-4 w-4" />
              New Scan
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={search}
                onChange={(e) => {
                  setPage(1);
                  setSearch(e.target.value);
                }}
                placeholder="Search by item name..."
                className="w-full rounded-lg border border-slate-200 py-2 pl-8 pr-3 text-sm"
              />
            </div>
            <select
              value={category}
              onChange={(e) => {
                setPage(1);
                setCategory(e.target.value);
              }}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600"
            >
              <option value="all">All Categories</option>
              <option value="recyclable">Recyclable</option>
              <option value="compostable">Compostable</option>
              <option value="landfill">Landfill</option>
              <option value="hazardous">Hazardous</option>
              <option value="e-waste">E-waste</option>
            </select>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500">
                  <th className="py-2 font-medium">Item</th>
                  <th className="py-2 font-medium">Result</th>
                  <th className="py-2 font-medium">Confidence</th>
                  <th className="py-2 font-medium">Scanned At</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100">
                    <td className="py-2.5 text-slate-800">{item.item_name}</td>
                    <td className="py-2.5">
                      {(() => {
                        const label = RESULT_LABEL[item.category] ?? item.category;
                        return (
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              RESULT_PILL[label] ?? "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {label}
                          </span>
                        );
                      })()}
                    </td>
                    <td className="py-2.5 text-slate-600">
                      {item.confidence !== null ? `${Math.round(item.confidence * 100)}%` : "n/a"}
                    </td>
                    <td className="py-2.5 text-slate-500">
                      {new Date(item.scanned_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-6 text-center text-slate-400">
                      No scans match your filters yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {total_pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
              <span>
                Page {page} of {total_pages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(total_pages, p + 1))}
                  disabled={page >= total_pages}
                  className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <ScanPanel triggerRef={scanTriggerRef} />
      </div>
    </div>
  );
}
