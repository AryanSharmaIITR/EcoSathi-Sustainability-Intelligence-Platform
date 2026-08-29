import { Sprout } from "lucide-react";

interface ImpactCardProps {
  completedCount: number;
}

export function ImpactCard({ completedCount }: ImpactCardProps) {
  const message =
    completedCount === 0
      ? "Complete your first action to start making an impact!"
      : completedCount < 5
      ? "You're making a difference — keep it up!"
      : "Outstanding sustainability progress!";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-4">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
        <Sprout className="h-5 w-5" />
      </span>
      <div>
        <div className="text-sm font-semibold text-emerald-800">
          {completedCount} action{completedCount !== 1 ? "s" : ""} completed
        </div>
        <div className="text-xs text-emerald-700">{message}</div>
      </div>
    </div>
  );
}
