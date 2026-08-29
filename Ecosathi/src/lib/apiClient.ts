import type {
  ActionListResponse,
  ActionUpdatePayload,
  AlertIncident,
  AlertsListResponse,
  BuildingZone,
  BuildingZoneCreate,
  BuildingZoneUpdatePayload,
  FacilitySettings,
  FacilitySettingsUpdate,
  GenerateReportRequest,
  GeneratedReportRead,
  RecommendationResponse,
  ReportsListResponse,
  Tenant,
  TelemetrySnapshot,
  WasteClassificationResponse,
  WasteScanHistoryResponse,
} from "../types/api";
import { getCurrentTenantId } from "./tenant";

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function tenantHeaders(): HeadersInit {
  const tenantId = getCurrentTenantId();
  return tenantId ? { "X-Tenant-Id": tenantId } : {};
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : response.statusText;
  } catch {
    return response.statusText;
  }
}

async function apiGet<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  const response = await fetch(url, { headers: tenantHeaders() });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

async function apiJson<T>(
  path: string,
  method: "POST" | "PATCH",
  body: unknown,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { ...tenantHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

export async function getTenant(tenantId: string): Promise<Tenant> {
  const response = await fetch(`${BASE_URL}/api/v1/tenants/me`, {
    headers: { "X-Tenant-Id": tenantId },
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

export async function classifyWaste(file: File): Promise<WasteClassificationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/api/v1/classify`, {
    method: "POST",
    headers: tenantHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

export async function generateActionPlan(file: File): Promise<RecommendationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/api/v1/recommend`, {
    method: "POST",
    headers: tenantHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

export function getUsage(periodStart?: string, periodEnd?: string): Promise<TelemetrySnapshot> {
  return apiGet<TelemetrySnapshot>("/api/v1/usage", {
    period_start: periodStart,
    period_end: periodEnd,
  });
}

export function getWasteScanHistory(params: {
  page?: number;
  pageSize?: number;
  category?: string;
  search?: string;
}): Promise<WasteScanHistoryResponse> {
  return apiGet<WasteScanHistoryResponse>("/api/v1/classify/history", {
    page: params.page,
    page_size: params.pageSize,
    category: params.category,
    search: params.search,
  });
}

export function getActions(params: {
  page?: number;
  pageSize?: number;
  status?: string;
  category?: string;
}): Promise<ActionListResponse> {
  return apiGet<ActionListResponse>("/api/v1/actions", {
    page: params.page,
    page_size: params.pageSize,
    status_filter: params.status,
    category: params.category,
  });
}

export function updateAction(actionId: string, payload: ActionUpdatePayload) {
  return apiJson(`/api/v1/actions/${actionId}`, "PATCH", payload);
}

export async function deleteAction(actionId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/v1/actions/${actionId}`, {
    method: "DELETE",
    headers: tenantHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
}

export function getReports(): Promise<ReportsListResponse> {
  return apiGet<ReportsListResponse>("/api/v1/reports");
}

export function generateReport(payload: GenerateReportRequest): Promise<GeneratedReportRead> {
  return apiJson<GeneratedReportRead>("/api/v1/reports/generate", "POST", payload);
}

export function exportReportUrl(reportId: string): string {
  // A plain download link can't carry the X-Tenant-Id header; this relies
  // on the backend's current dev-only tenant auto-selection (see
  // Backend/app/dependencies.py::get_current_tenant) until real
  // auth/session-based tenant resolution replaces the header entirely.
  return `${BASE_URL}/api/v1/reports/${reportId}/export.csv`;
}

// --- Settings ---

export function getSettings(): Promise<FacilitySettings> {
  return apiGet<FacilitySettings>("/api/v1/settings");
}

export async function updateSettings(payload: FacilitySettingsUpdate): Promise<FacilitySettings> {
  const response = await fetch(`${BASE_URL}/api/v1/settings`, {
    method: "PUT",
    headers: { ...tenantHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json();
}

export function getZones(): Promise<BuildingZone[]> {
  return apiGet<BuildingZone[]>("/api/v1/settings/zones");
}

export function createZone(payload: BuildingZoneCreate): Promise<BuildingZone> {
  return apiJson<BuildingZone>("/api/v1/settings/zones", "POST", payload);
}

export function updateZone(id: string, payload: BuildingZoneUpdatePayload): Promise<BuildingZone> {
  return apiJson<BuildingZone>(`/api/v1/settings/zones/${id}`, "PATCH", payload);
}

export function syncZonesFromUsage(): Promise<BuildingZone[]> {
  return apiJson<BuildingZone[]>("/api/v1/settings/zones/sync-from-usage", "POST", {});
}

export async function deleteZone(id: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/v1/settings/zones/${id}`, {
    method: "DELETE",
    headers: tenantHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
}

// --- Alerts ---

export function getAlerts(params?: { status?: string; severity?: string }): Promise<AlertsListResponse> {
  return apiGet<AlertsListResponse>("/api/v1/alerts", {
    alert_status: params?.status,
    severity: params?.severity,
  });
}

export function evaluateAlerts(): Promise<AlertIncident[]> {
  return apiJson<AlertIncident[]>("/api/v1/alerts/evaluate", "POST", {});
}

export function acknowledgeAlert(id: string): Promise<AlertIncident> {
  return apiJson<AlertIncident>(`/api/v1/alerts/${id}`, "PATCH", { status: "acknowledged" });
}

export function resolveAlert(id: string): Promise<AlertIncident> {
  return apiJson<AlertIncident>(`/api/v1/alerts/${id}`, "PATCH", { status: "resolved" });
}
