export interface AIGeneratedResponse {
  confidence: number | null;
  source: string | null;
}

export interface WasteClassificationResponse extends AIGeneratedResponse {
  item_name: string;
  category: string;
  disposal_instructions: string;
}

export interface RecommendedActionItem {
  id: string;
  title: string;
  priority: "high" | "medium" | "low";
  rationale: string;
  category: "water" | "energy" | "waste" | "general";
  estimated_monthly_impact: number | null;
}

export interface RecommendationResponse extends AIGeneratedResponse {
  actions: RecommendedActionItem[];
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

// --- Usage / Telemetry (mirrors Backend/app/schemas/telemetry_schema.py) ---
// datetime.date fields serialize as "YYYY-MM-DD" strings over the wire.

export interface UsageSummaryCards {
  total_water_usage_L: number;
  total_energy_usage_kWh: number;
  total_waste_scanned: number;
  avg_daily_water_L: number;
  avg_daily_energy_kWh: number;
  water_wow_pct: number | null;
  energy_wow_pct: number | null;
  waste_wow_pct: number | null;
  peak_water_day: string | null;
  peak_water_day_L: number | null;
  peak_energy_day: string | null;
  peak_energy_day_kWh: number | null;
}

export interface DailyUsageRow {
  date: string;
  water_usage_L: number;
  energy_usage_kWh: number;
  avg_temp_C: number;
  rainfall_mm: number;
}

export interface ForecastDataPoint {
  date: string;
  actual: number | null;
  forecast: number | null;
}

export interface ForecastSeries {
  resource: string;
  unit: string;
  data_points: ForecastDataPoint[];
  forecast_insight: string | null;
}

export interface BuildingUsage {
  building: string;
  water_usage_L: number;
  energy_usage_kWh: number;
  waste_scanned_count: number;
}

export interface TelemetrySnapshot {
  tenant_id: string;
  period_start: string;
  period_end: string;
  summary: UsageSummaryCards;
  daily_rows: DailyUsageRow[];
  forecast_series: ForecastSeries[];
  buildings: BuildingUsage[];
}

// --- Waste Scans (mirrors Backend/app/schemas/waste_scan.py) ---

export interface WasteScanItem {
  id: string;
  item_name: string;
  category: string;
  disposal_instructions: string;
  confidence: number | null;
  source: string | null;
  input_ref: string;
  scanned_at: string;
}

export interface WasteScanStats {
  total_scans: number;
  recyclable_count: number;
  compostable_count: number;
  non_recyclable_count: number;
  avg_confidence: number | null;
  total_scans_wow_pct: number | null;
}

export interface WasteScanHistoryResponse {
  stats: WasteScanStats;
  items: WasteScanItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

// --- Actions (mirrors Backend/app/schemas/action.py) ---

export type ActionStatus = "pending" | "in_progress" | "completed";
export type ActionPriority = "high" | "medium" | "low";

export interface ActionRead {
  id: string;
  title: string;
  rationale: string;
  category: string;
  priority: ActionPriority;
  status: ActionStatus;
  progress_pct: number;
  estimated_monthly_impact: number | null;
  due_date: string | null;
  source: string;
  recommended_steps: string[];
  created_at: string;
  completed_at: string | null;
}

export interface ActionUpdatePayload {
  status?: ActionStatus;
  progress_pct?: number;
}

export interface ActionStats {
  total_actions: number;
  in_progress_count: number;
  pending_count: number;
  completed_count: number;
  total_actions_wow: number | null;
  estimated_monthly_impact_total: number;
}

export interface ActionListResponse {
  stats: ActionStats;
  items: ActionRead[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

// --- Reports (mirrors Backend/app/schemas/report.py) ---

export type ReportType = "sustainability" | "water" | "energy" | "waste" | "emissions";

export interface GeneratedReportRead {
  id: string;
  report_type: ReportType;
  period_start: string;
  period_end: string;
  generated_by: string;
  download_count: number;
  created_at: string;
}

export interface GenerateReportRequest {
  report_type: ReportType;
  period_start: string;
  period_end: string;
}

export interface ReportsStats {
  reports_generated: number;
  total_downloads: number;
  data_points_analyzed: number;
  insights_generated: number;
  co2_avoided_kg: number;
}

export interface ReportsListResponse {
  stats: ReportsStats;
  items: GeneratedReportRead[];
}

// --- Facility Settings (mirrors Backend/app/schemas/facility_settings.py) ---

export interface FacilitySettings {
  id: string;
  tenant_id: string;
  // Resource caps
  water_daily_limit_L: number | null;
  water_reserve_buffer_L: number | null;
  energy_daily_limit_kWh: number | null;
  energy_peak_load_kW: number | null;
  solar_generation_kWh: number | null;
  // Workforce
  headcount_morning: number | null;
  headcount_evening: number | null;
  headcount_night: number | null;
  // Financial
  monthly_budget_INR: number | null;
  electricity_rate_per_kWh: number | null;
  water_rate_per_1000L: number | null;
  labor_cost_per_shift: number | null;
  hauling_fee_per_ton: number | null;
  // Revenue
  plastic_yield_per_ton_INR: number | null;
  compost_yield_per_ton_INR: number | null;
  metal_yield_per_ton_INR: number | null;
  updated_at: string;
}

export type FacilitySettingsUpdate = Partial<Omit<FacilitySettings, "id" | "tenant_id" | "updated_at">>;

export interface BuildingZone {
  id: string;
  tenant_id: string;
  name: string;
  max_capacity_kg: number | null;
  floor_area_sqm: number | null;
  machinery: string[];
  created_at: string;
  updated_at: string;
}

export interface BuildingZoneCreate {
  name: string;
  max_capacity_kg?: number | null;
  floor_area_sqm?: number | null;
  machinery?: string[];
}

export interface BuildingZoneUpdatePayload {
  name?: string;
  max_capacity_kg?: number | null;
  floor_area_sqm?: number | null;
  machinery?: string[];
}

// --- Alerts (mirrors Backend/app/schemas/alert.py) ---

export type AlertSeverity = "critical" | "high" | "warning" | "info";
export type AlertStatus = "active" | "acknowledged" | "resolved";
export type AlertTriggerType = "water_deficit" | "energy_overload" | "roi_negative" | "workforce_deficit";

export interface AlertIncident {
  id: string;
  tenant_id: string;
  severity: AlertSeverity;
  trigger_type: AlertTriggerType;
  title: string;
  message: string;
  metric_actual: number | null;
  metric_limit: number | null;
  metric_unit: string | null;
  building: string | null;
  ai_recommendation: string | null;
  status: AlertStatus;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface AlertStats {
  total_active: number;
  critical_count: number;
  high_count: number;
  warning_count: number;
  info_count: number;
}

export interface AlertsListResponse {
  stats: AlertStats;
  items: AlertIncident[];
}
