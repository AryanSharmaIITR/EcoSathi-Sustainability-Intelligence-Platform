import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface UsagePoint {
  date: string;
  actual: number | null;
  forecast: number | null;
}

interface UsageChartProps {
  title: string;
  unit: string;
  deltaLabel: string;
  deltaGood?: boolean;
  color: string;
  data: UsagePoint[];
}

export function UsageChart({ title, unit, deltaLabel, deltaGood = true, color, data }: UsageChartProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">
          {title} ({unit})
        </h3>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${deltaGood ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}`}>
          {deltaGood ? "↓" : "↑"} {deltaLabel}
        </span>
      </div>
      <div className="mt-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual"
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke={color}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4" style={{ backgroundColor: color }} />
          Actual
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 border-t-2 border-dashed" style={{ borderColor: color }} />
          Forecast
        </span>
      </div>
    </div>
  );
}
