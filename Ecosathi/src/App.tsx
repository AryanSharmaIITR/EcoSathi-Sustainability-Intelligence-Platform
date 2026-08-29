import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { OverviewPage } from "./pages/OverviewPage";
import { UsagePage } from "./pages/UsagePage";
import { WasteScansPage } from "./pages/WasteScansPage";
import { ActionsPage } from "./pages/ActionsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AlertsPage } from "./pages/AlertsPage";
import { SettingsPage } from "./pages/SettingsPage";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/usage" element={<UsagePage />} />
        <Route path="/waste-scans" element={<WasteScansPage />} />
        <Route path="/actions" element={<ActionsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
