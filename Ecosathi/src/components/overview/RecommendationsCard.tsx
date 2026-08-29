import { ArrowRight, Sprout } from "lucide-react";
import { Link } from "react-router-dom";
import type { ActionRead } from "../../types/api";

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-50 text-red-700",
  medium: "bg-blue-50 text-blue-700",
  low: "bg-slate-100 text-slate-600",
};

interface RecommendationsCardProps {
  actions: ActionRead[];
}

export function RecommendationsCard({ actions }: RecommendationsCardProps) {
  // Show top 3 pending/in-progress actions ordered by priority
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const top = [...actions]
    .filter((a) => a.status !== "completed")
    .sort((a, b) => (priorityOrder[a.priority] ?? 9) - (priorityOrder[b.priority] ?? 9))
    .slice(0, 3);

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Top Recommendations</h3>
      {top.length === 0 ? (
        <p className="mt-3 flex-1 text-xs text-slate-400">No pending actions — scan an item to generate recommendations.</p>
      ) : (
        <ul className="mt-3 flex-1 space-y-3">
          {top.map((action) => (
            <li key={action.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-2 text-slate-700">
                <Sprout className="h-4 w-4 shrink-0 text-emerald-600" />
                <span className="line-clamp-1">{action.title}</span>
              </span>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PRIORITY_STYLES[action.priority] ?? "bg-slate-100 text-slate-600"}`}>
                {action.priority}
              </span>
            </li>
          ))}
        </ul>
      )}
      <Link
        to="/actions"
        className="mt-4 flex items-center gap-1 text-sm font-medium text-emerald-600 hover:text-emerald-700"
      >
        View all actions <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
