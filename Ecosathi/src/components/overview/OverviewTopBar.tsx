import { ChevronDown, SlidersHorizontal } from "lucide-react";

interface OverviewTopBarProps {
  periodStart?: string;
  periodEnd?: string;
}

function fmtDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function OverviewTopBar({ periodStart, periodEnd }: OverviewTopBarProps) {
  const label =
    periodStart && periodEnd
      ? `${fmtDate(periodStart)} – ${fmtDate(periodEnd)}`
      : "Last 7 Days";

  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Overview</h1>
        <button className="mt-1 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          Pilot Campus <ChevronDown className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
          {label} <ChevronDown className="h-3.5 w-3.5" />
        </button>
        <button className="rounded-lg border border-slate-200 bg-white p-2 text-slate-500 shadow-sm">
          <SlidersHorizontal className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
