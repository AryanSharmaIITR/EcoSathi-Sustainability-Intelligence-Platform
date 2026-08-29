import type { DailyUsageRow } from "../../types/api";

export function DailyUsageTable({ rows }: { rows: DailyUsageRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500">
            <th className="py-2 font-medium">Date</th>
            <th className="py-2 font-medium">Water Usage (L)</th>
            <th className="py-2 font-medium">Energy Usage (kWh)</th>
            <th className="py-2 font-medium">Avg Temp (°C)</th>
            <th className="py-2 font-medium">Rainfall (mm)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.date} className="border-b border-slate-100">
              <td className="py-2 text-slate-700">{row.date}</td>
              <td className="py-2 text-slate-700">{row.water_usage_L.toLocaleString()}</td>
              <td className="py-2 text-slate-700">{row.energy_usage_kWh.toLocaleString()}</td>
              <td className="py-2 text-slate-700">{row.avg_temp_C}</td>
              <td className="py-2 text-slate-700">{row.rainfall_mm}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 text-center text-slate-400">
                No usage data uploaded for this period yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
