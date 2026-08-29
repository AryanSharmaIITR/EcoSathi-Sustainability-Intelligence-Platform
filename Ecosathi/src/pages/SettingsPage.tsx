import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, DollarSign, Droplets, Plus, RefreshCw, Trash2, Users, Wrench, X, Zap } from "lucide-react";
import { useState } from "react";
import {
  createZone,
  deleteZone,
  getSettings,
  getZones,
  syncZonesFromUsage,
  updateSettings,
  updateZone,
} from "../lib/apiClient";
import type {
  BuildingZone,
  BuildingZoneCreate,
  FacilitySettings,
  FacilitySettingsUpdate,
} from "../types/api";

// ── helpers ─────────────────────────────────────────────────────────────────

function n(val: number | null | undefined): string {
  return val == null ? "" : String(val);
}
function numOrNull(s: string): number | null {
  if (s.trim() === "") return null;
  const v = Number(s);
  return isNaN(v) ? null : v;
}

type Tab = "infrastructure" | "resources" | "workforce" | "financial";

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "infrastructure", label: "Infrastructure", icon: Building2 },
  { id: "resources", label: "Resource Constraints", icon: Droplets },
  { id: "workforce", label: "Workforce", icon: Users },
  { id: "financial", label: "Financial", icon: DollarSign },
];

// ── FieldInput ───────────────────────────────────────────────────────────────

function FieldInput({
  label,
  unit,
  value,
  onChange,
}: {
  label: string;
  unit?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600">
        {label}
        {unit && <span className="ml-1 text-slate-400">({unit})</span>}
      </label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
        placeholder="—"
      />
    </div>
  );
}

// ── SaveBar ──────────────────────────────────────────────────────────────────

function SaveBar({
  isDirty,
  isPending,
  isError,
  errorMessage,
  onSave,
}: {
  isDirty: boolean;
  isPending: boolean;
  isError: boolean;
  errorMessage?: string;
  onSave: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <span className="text-sm text-slate-500">
        {isError ? (
          <span className="text-red-600">{errorMessage ?? "Save failed."}</span>
        ) : isDirty ? (
          "You have unsaved changes."
        ) : (
          "All changes saved."
        )}
      </span>
      <button
        onClick={onSave}
        disabled={!isDirty || isPending}
        className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
      >
        {isPending ? "Saving…" : "Save Changes"}
      </button>
    </div>
  );
}

// ── Infrastructure tab ───────────────────────────────────────────────────────

function InfrastructureTab() {
  const queryClient = useQueryClient();
  const zonesQuery = useQuery({ queryKey: ["zones"], queryFn: getZones });

  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCapacity, setNewCapacity] = useState("");
  const [newArea, setNewArea] = useState("");
  const [newMachinery, setNewMachinery] = useState("");

  const createMutation = useMutation({
    mutationFn: (payload: BuildingZoneCreate) => createZone(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      setShowAdd(false);
      setNewName("");
      setNewCapacity("");
      setNewArea("");
      setNewMachinery("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteZone(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  });

  const syncMutation = useMutation({
    mutationFn: syncZonesFromUsage,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  });

  function handleCreate() {
    if (!newName.trim()) return;
    createMutation.mutate({
      name: newName.trim(),
      max_capacity_kg: numOrNull(newCapacity),
      floor_area_sqm: numOrNull(newArea),
      machinery: newMachinery
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    });
  }

  if (zonesQuery.isLoading) return <p className="text-sm text-slate-400">Loading zones…</p>;
  if (zonesQuery.isError)
    return (
      <p className="text-sm text-red-600">
        Failed to load zones: {(zonesQuery.error as Error)?.message}
      </p>
    );

  const zones = zonesQuery.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-slate-500">
          Define buildings and zones with their capacities and equipment.{" "}
          <span className="text-slate-400">
            Zone names must match the <code className="rounded bg-slate-100 px-1 text-xs">building</code> column in uploaded usage CSVs to appear in the Usage chart.
          </span>
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            title="Create a zone for every building name already seen in uploaded usage CSVs but missing here"
            className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
            {syncMutation.isPending ? "Syncing…" : "Sync from Usage Data"}
          </button>
          <button
            onClick={() => setShowAdd((v) => !v)}
            className="flex items-center gap-2 rounded-lg border border-brand-700 px-3 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-700 hover:text-white"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Zone
          </button>
        </div>
      </div>

      {syncMutation.isSuccess && (
        <p className="text-xs text-slate-500">
          {syncMutation.data.length === 0
            ? "No new buildings found in uploaded usage data — everything is already in sync."
            : `Added ${syncMutation.data.length} zone${syncMutation.data.length === 1 ? "" : "s"} from usage data: ${syncMutation.data.map((z) => z.name).join(", ")}.`}
        </p>
      )}
      {syncMutation.isError && (
        <p className="text-xs text-red-600">
          Sync failed: {(syncMutation.error as Error)?.message}
        </p>
      )}

      {showAdd && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h4 className="mb-3 text-sm font-semibold text-slate-800">New Building Zone</h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Name *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Block A"
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
              />
            </div>
            <FieldInput
              label="Max Capacity"
              unit="kg"
              value={newCapacity}
              onChange={setNewCapacity}
            />
            <FieldInput
              label="Floor Area"
              unit="sqm"
              value={newArea}
              onChange={setNewArea}
            />
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Machinery{" "}
                <span className="text-slate-400">(comma-separated)</span>
              </label>
              <input
                value={newMachinery}
                onChange={(e) => setNewMachinery(e.target.value)}
                placeholder="Baler, Shredder"
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
              />
            </div>
          </div>
          {createMutation.isError && (
            <p className="mt-2 text-xs text-red-600">
              {(createMutation.error as Error)?.message}
            </p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending || !newName.trim()}
              className="rounded-lg bg-brand-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
            >
              {createMutation.isPending ? "Adding…" : "Add Zone"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="rounded-lg px-4 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {zones.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-10 text-center text-sm text-slate-400">
          No zones configured yet. Add your first building zone above, or click{" "}
          <span className="font-medium text-slate-500">Sync from Usage Data</span> to pull in
          building names already seen in uploaded usage CSVs.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500">
                <th className="px-4 py-3 font-medium">Zone Name</th>
                <th className="px-4 py-3 font-medium">Capacity</th>
                <th className="px-4 py-3 font-medium">Floor Area</th>
                <th className="px-4 py-3 font-medium">Machinery</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <ZoneRow
                  key={zone.id}
                  zone={zone}
                  onDelete={() => deleteMutation.mutate(zone.id)}
                  isDeleting={deleteMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ZoneRow({
  zone,
  onDelete,
  isDeleting,
}: {
  zone: BuildingZone;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(zone.name);
  const [capacity, setCapacity] = useState(n(zone.max_capacity_kg));
  const [area, setArea] = useState(n(zone.floor_area_sqm));
  const [machinery, setMachinery] = useState(zone.machinery.join(", "));

  const updateMutation = useMutation({
    mutationFn: () =>
      updateZone(zone.id, {
        name: name.trim() || zone.name,
        max_capacity_kg: numOrNull(capacity),
        floor_area_sqm: numOrNull(area),
        machinery: machinery
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["zones"] });
      setEditing(false);
    },
  });

  if (editing) {
    return (
      <tr className="border-b border-slate-100 bg-brand-100/40">
        <td className="px-4 py-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:border-brand-600 focus:outline-none"
          />
        </td>
        <td className="px-4 py-2">
          <input
            type="number"
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-sm focus:border-brand-600 focus:outline-none"
          />
        </td>
        <td className="px-4 py-2">
          <input
            type="number"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-sm focus:border-brand-600 focus:outline-none"
          />
        </td>
        <td className="px-4 py-2">
          <input
            value={machinery}
            onChange={(e) => setMachinery(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm focus:border-brand-600 focus:outline-none"
          />
        </td>
        <td className="px-4 py-2">
          <div className="flex gap-2">
            <button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
              className="text-xs font-medium text-brand-700 hover:underline disabled:opacity-50"
            >
              {updateMutation.isPending ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="text-xs text-slate-400 hover:underline"
            >
              Cancel
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-4 py-3 font-medium text-slate-800">{zone.name}</td>
      <td className="px-4 py-3 text-slate-600">
        {zone.max_capacity_kg != null ? `${zone.max_capacity_kg.toLocaleString()} kg` : "—"}
      </td>
      <td className="px-4 py-3 text-slate-600">
        {zone.floor_area_sqm != null ? `${zone.floor_area_sqm.toLocaleString()} m²` : "—"}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {zone.machinery.length === 0 ? (
            <span className="text-slate-400">—</span>
          ) : (
            zone.machinery.map((m) => (
              <span
                key={m}
                className="flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
              >
                <Wrench className="h-2.5 w-2.5" />
                {m}
              </span>
            ))
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          <button
            onClick={() => setEditing(true)}
            className="text-xs font-medium text-brand-700 hover:underline"
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="text-xs text-red-500 hover:underline disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ── Resource Constraints tab ─────────────────────────────────────────────────

function ResourceTab({
  settings,
  onSave,
}: {
  settings: FacilitySettings;
  onSave: (p: FacilitySettingsUpdate) => Promise<FacilitySettings>;
}) {
  const [waterLimit, setWaterLimit] = useState(n(settings.water_daily_limit_L));
  const [waterBuffer, setWaterBuffer] = useState(n(settings.water_reserve_buffer_L));
  const [energyLimit, setEnergyLimit] = useState(n(settings.energy_daily_limit_kWh));
  const [peakLoad, setPeakLoad] = useState(n(settings.energy_peak_load_kW));
  const [solar, setSolar] = useState(n(settings.solar_generation_kWh));

  const initial = {
    water_daily_limit_L: n(settings.water_daily_limit_L),
    water_reserve_buffer_L: n(settings.water_reserve_buffer_L),
    energy_daily_limit_kWh: n(settings.energy_daily_limit_kWh),
    energy_peak_load_kW: n(settings.energy_peak_load_kW),
    solar_generation_kWh: n(settings.solar_generation_kWh),
  };

  const isDirty =
    waterLimit !== initial.water_daily_limit_L ||
    waterBuffer !== initial.water_reserve_buffer_L ||
    energyLimit !== initial.energy_daily_limit_kWh ||
    peakLoad !== initial.energy_peak_load_kW ||
    solar !== initial.solar_generation_kWh;

  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>();

  async function handleSave() {
    setIsPending(true);
    setIsError(false);
    try {
      await onSave({
        water_daily_limit_L: numOrNull(waterLimit),
        water_reserve_buffer_L: numOrNull(waterBuffer),
        energy_daily_limit_kWh: numOrNull(energyLimit),
        energy_peak_load_kW: numOrNull(peakLoad),
        solar_generation_kWh: numOrNull(solar),
      });
    } catch (e) {
      setIsError(true);
      setErrorMsg((e as Error).message);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Droplets className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-800">Water Constraints</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FieldInput
            label="Daily Limit"
            unit="L/day"
            value={waterLimit}
            onChange={setWaterLimit}
          />
          <FieldInput
            label="Reserve Buffer"
            unit="L"
            value={waterBuffer}
            onChange={setWaterBuffer}
          />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-800">Energy Constraints</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FieldInput
            label="Daily Limit"
            unit="kWh/day"
            value={energyLimit}
            onChange={setEnergyLimit}
          />
          <FieldInput
            label="Peak Load"
            unit="kW"
            value={peakLoad}
            onChange={setPeakLoad}
          />
          <FieldInput
            label="Solar Generation"
            unit="kWh/day"
            value={solar}
            onChange={setSolar}
          />
        </div>
      </div>

      <SaveBar
        isDirty={isDirty}
        isPending={isPending}
        isError={isError}
        errorMessage={errorMsg}
        onSave={handleSave}
      />
    </div>
  );
}

// ── Workforce tab ────────────────────────────────────────────────────────────

function WorkforceTab({
  settings,
  onSave,
}: {
  settings: FacilitySettings;
  onSave: (p: FacilitySettingsUpdate) => Promise<FacilitySettings>;
}) {
  const [morning, setMorning] = useState(n(settings.headcount_morning));
  const [evening, setEvening] = useState(n(settings.headcount_evening));
  const [night, setNight] = useState(n(settings.headcount_night));

  const isDirty =
    morning !== n(settings.headcount_morning) ||
    evening !== n(settings.headcount_evening) ||
    night !== n(settings.headcount_night);

  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>();

  async function handleSave() {
    setIsPending(true);
    setIsError(false);
    try {
      await onSave({
        headcount_morning: numOrNull(morning),
        headcount_evening: numOrNull(evening),
        headcount_night: numOrNull(night),
      });
    } catch (e) {
      setIsError(true);
      setErrorMsg((e as Error).message);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-4 w-4 text-violet-600" />
          <h3 className="text-sm font-semibold text-slate-800">Shift Headcount</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FieldInput
            label="Morning Shift"
            unit="people"
            value={morning}
            onChange={setMorning}
          />
          <FieldInput
            label="Evening Shift"
            unit="people"
            value={evening}
            onChange={setEvening}
          />
          <FieldInput
            label="Night Shift"
            unit="people"
            value={night}
            onChange={setNight}
          />
        </div>
      </div>
      <SaveBar
        isDirty={isDirty}
        isPending={isPending}
        isError={isError}
        errorMessage={errorMsg}
        onSave={handleSave}
      />
    </div>
  );
}

// ── Financial tab ────────────────────────────────────────────────────────────

function FinancialTab({
  settings,
  onSave,
}: {
  settings: FacilitySettings;
  onSave: (p: FacilitySettingsUpdate) => Promise<FacilitySettings>;
}) {
  const [budget, setBudget] = useState(n(settings.monthly_budget_INR));
  const [elec, setElec] = useState(n(settings.electricity_rate_per_kWh));
  const [water, setWater] = useState(n(settings.water_rate_per_1000L));
  const [labor, setLabor] = useState(n(settings.labor_cost_per_shift));
  const [hauling, setHauling] = useState(n(settings.hauling_fee_per_ton));
  const [plastic, setPlastic] = useState(n(settings.plastic_yield_per_ton_INR));
  const [compost, setCompost] = useState(n(settings.compost_yield_per_ton_INR));
  const [metal, setMetal] = useState(n(settings.metal_yield_per_ton_INR));

  const isDirty =
    budget !== n(settings.monthly_budget_INR) ||
    elec !== n(settings.electricity_rate_per_kWh) ||
    water !== n(settings.water_rate_per_1000L) ||
    labor !== n(settings.labor_cost_per_shift) ||
    hauling !== n(settings.hauling_fee_per_ton) ||
    plastic !== n(settings.plastic_yield_per_ton_INR) ||
    compost !== n(settings.compost_yield_per_ton_INR) ||
    metal !== n(settings.metal_yield_per_ton_INR);

  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>();

  async function handleSave() {
    setIsPending(true);
    setIsError(false);
    try {
      await onSave({
        monthly_budget_INR: numOrNull(budget),
        electricity_rate_per_kWh: numOrNull(elec),
        water_rate_per_1000L: numOrNull(water),
        labor_cost_per_shift: numOrNull(labor),
        hauling_fee_per_ton: numOrNull(hauling),
        plastic_yield_per_ton_INR: numOrNull(plastic),
        compost_yield_per_ton_INR: numOrNull(compost),
        metal_yield_per_ton_INR: numOrNull(metal),
      });
    } catch (e) {
      setIsError(true);
      setErrorMsg((e as Error).message);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-800">Budget</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FieldInput
            label="Monthly Budget"
            unit="₹"
            value={budget}
            onChange={setBudget}
          />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-800">Cost Rates</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FieldInput
            label="Electricity Rate"
            unit="₹/kWh"
            value={elec}
            onChange={setElec}
          />
          <FieldInput
            label="Water Rate"
            unit="₹/1000L"
            value={water}
            onChange={setWater}
          />
          <FieldInput
            label="Labor Cost"
            unit="₹/shift"
            value={labor}
            onChange={setLabor}
          />
          <FieldInput
            label="Hauling Fee"
            unit="₹/ton"
            value={hauling}
            onChange={setHauling}
          />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-800">Revenue Rates</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FieldInput
            label="Plastic Yield"
            unit="₹/ton"
            value={plastic}
            onChange={setPlastic}
          />
          <FieldInput
            label="Compost Yield"
            unit="₹/ton"
            value={compost}
            onChange={setCompost}
          />
          <FieldInput
            label="Metal Yield"
            unit="₹/ton"
            value={metal}
            onChange={setMetal}
          />
        </div>
      </div>

      <SaveBar
        isDirty={isDirty}
        isPending={isPending}
        isError={isError}
        errorMessage={errorMsg}
        onSave={handleSave}
      />
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("infrastructure");
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  const saveMutation = useMutation({
    mutationFn: (payload: FacilitySettingsUpdate) => updateSettings(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  if (settingsQuery.isLoading) {
    return <p className="p-6 text-sm text-slate-500">Loading settings…</p>;
  }
  if (settingsQuery.isError || !settingsQuery.data) {
    return (
      <p className="p-6 text-sm text-red-600">
        Failed to load settings: {(settingsQuery.error as Error)?.message}
      </p>
    );
  }

  const settings = settingsQuery.data;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Configure facility constraints, workforce, and financial parameters.
        </p>
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex flex-wrap gap-2 border-b border-slate-200 pb-0">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === id
                ? "border-b-2 border-brand-600 text-brand-700"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "infrastructure" && <InfrastructureTab />}
      {activeTab === "resources" && (
        <ResourceTab settings={settings} onSave={saveMutation.mutateAsync} />
      )}
      {activeTab === "workforce" && (
        <WorkforceTab settings={settings} onSave={saveMutation.mutateAsync} />
      )}
      {activeTab === "financial" && (
        <FinancialTab settings={settings} onSave={saveMutation.mutateAsync} />
      )}
    </div>
  );
}
