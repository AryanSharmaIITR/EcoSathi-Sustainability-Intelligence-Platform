import {
  Bell,
  Building2,
  Camera,
  CheckSquare,
  FileText,
  LayoutDashboard,
  LifeBuoy,
  Settings,
  BarChart3,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import logo from "../../assets/logo.png";
import { getAlerts } from "../../lib/apiClient";

const BASE_NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/usage", label: "Usage", icon: BarChart3 },
  { to: "/waste-scans", label: "Waste Scans", icon: Camera },
  { to: "/actions", label: "Actions", icon: CheckSquare },
  { to: "/reports", label: "Reports", icon: FileText },
];

export function Sidebar() {
  const alertsQuery = useQuery({
    queryKey: ["alerts", "active"],
    queryFn: () => getAlerts({ status: "active" }),
    refetchInterval: 60_000, // re-check every minute
  });

  const activeCount = alertsQuery.data?.stats.total_active ?? 0;

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex h-screen w-64 shrink-0 flex-col justify-between overflow-hidden bg-brand-900 px-4 py-6 text-brand-100">
      <div>
        <div className="mb-8 flex items-center gap-2 px-2">
          <img src={logo} alt="EcoSathi Logo" className="h-9 w-9 object-contain" />
          <div>
            <div className="text-lg font-semibold leading-tight text-white">EcoSathi</div>
            <div className="text-xs text-white/50">Sustainability Intelligence</div>
          </div>
        </div>

        <nav className="space-y-1">
          {BASE_NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-600 text-white"
                    : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}

          {/* Alerts — with active badge */}
          <NavLink
            to="/alerts"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-white/70 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Bell className="h-4 w-4" />
            <span className="flex-1">Alerts</span>
            {activeCount > 0 && (
              <span className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-semibold text-white leading-none">
                {activeCount > 99 ? "99+" : activeCount}
              </span>
            )}
          </NavLink>

          {/* Settings */}
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-white/70 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Settings className="h-4 w-4" />
            Settings
          </NavLink>
        </nav>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3 rounded-lg bg-white/5 px-3 py-3">
          <Building2 className="h-5 w-5 text-white/70" />
          <div>
            <div className="text-sm font-medium text-white">Pilot Campus</div>
            <div className="text-xs text-white/50">Tenant</div>
          </div>
        </div>
        <a
          href="mailto:support@ecosathi.example"
          className="flex items-center gap-3 rounded-lg bg-white/5 px-3 py-3 hover:bg-white/10"
        >
          <LifeBuoy className="h-5 w-5 text-brand-500" />
          <div>
            <div className="text-sm font-medium text-white">Need help?</div>
            <div className="text-xs text-white/50">Contact support</div>
          </div>
        </a>
      </div>
    </aside>
  );
}
