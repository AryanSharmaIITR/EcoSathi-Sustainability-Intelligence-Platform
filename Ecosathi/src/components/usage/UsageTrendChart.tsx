import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastSeries } from "../../types/api";

interface UsageTrendChartProps {
  series: ForecastSeries | undefined;
  color: string;
}

export function UsageTrendChart({ series, color }: UsageTrendChartProps) {
  if (!series) {
    return <p className="py-12 text-center text-sm text-slate-400">No data for this resource yet.</p>;
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">
        {series.resource[0].toUpperCase() + series.resource.slice(1)} Usage ({series.unit})
      </h3>
      <div className="mt-3 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series.data_points} margin={{ left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toLocaleString()} ${series.unit}`,
                name === "actual" ? "Actual" : "Forecast",
              ]}
            />
            <Line
              type="monotone"
              dataKey="actual"
              name="actual"
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="forecast"
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
