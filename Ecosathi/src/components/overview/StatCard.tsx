import type { LucideIcon } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface StatCardProps {
  icon: LucideIcon;
  iconClassName: string;
  label: string;
  value: string;
  deltaLabel: string;
  deltaDirection: "up" | "down";
  deltaGood: boolean;
  sparkline: number[];
  sparklineColor: string;
}

export function StatCard({
  icon: Icon,
  iconClassName,
  label,
  value,
  deltaLabel,
  deltaDirection,
  deltaGood,
  sparkline,
  sparklineColor,
}: StatCardProps) {
  const data = sparkline.map((v, i) => ({ i, v }));
  const gradientId = `spark-${label.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span className={`flex h-8 w-8 items-center justify-center rounded-full ${iconClassName}`}>
          <Icon className="h-4 w-4" />
        </span>
        <span className="text-sm font-medium text-slate-600">{label}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-900">{value}</div>
      <div className={`mt-1 text-xs font-medium ${deltaGood ? "text-emerald-600" : "text-red-500"}`}>
        {deltaDirection === "down" ? "↓" : "↑"} {deltaLabel}
      </div>
      <div className="mt-2 h-10">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={sparklineColor} stopOpacity={0.4} />
                <stop offset="100%" stopColor={sparklineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke={sparklineColor}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
