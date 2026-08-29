import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/layout/Sidebar";

export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="ml-64 min-w-0 flex-1 overflow-y-auto overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
}
