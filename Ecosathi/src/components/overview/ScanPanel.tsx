import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Camera,
  CheckCircle2,
  ClipboardList,
  Droplets,
  Loader2,
  MoreVertical,
  Recycle,
  Zap,
} from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { classifyWaste, deleteAction, generateActionPlan } from "../../lib/apiClient";
import type { RecommendedActionItem, WasteClassificationResponse } from "../../types/api";

const CATEGORY_BADGE: Record<string, string> = {
  recyclable: "bg-emerald-50 text-emerald-700",
  compostable: "bg-green-50 text-green-700",
  landfill: "bg-slate-100 text-slate-700",
  hazardous: "bg-red-50 text-red-700",
  "e-waste": "bg-amber-50 text-amber-700",
};

const PRIORITY_DOT: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-400",
  low: "bg-slate-400",
};

const PRIORITY_LABEL: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

/** Derive rough water / energy / days estimates from an action item. */
function deriveEstimates(action: RecommendedActionItem): {
  waterL: number | null;
  energyKWh: number | null;
  days: number;
} {
  const impact = action.estimated_monthly_impact ?? 0;
  if (action.category === "water") {
    return {
      waterL: Math.round((impact / 0.05) * 30),
      energyKWh: null,
      days: action.priority === "high" ? 7 : action.priority === "medium" ? 14 : 30,
    };
  }
  if (action.category === "energy") {
    return {
      waterL: null,
      energyKWh: Math.round((impact / 8) * 30),
      days: action.priority === "high" ? 7 : action.priority === "medium" ? 14 : 30,
    };
  }
  return {
    waterL: impact > 0 ? Math.round((impact / 0.05) * 5) : null,
    energyKWh: impact > 0 ? Math.round((impact / 8) * 5) : null,
    days: action.priority === "high" ? 3 : action.priority === "medium" ? 10 : 21,
  };
}

interface ScanPanelProps {
  triggerRef?: React.MutableRefObject<(() => void) | null>;
}

export function ScanPanel({ triggerRef }: ScanPanelProps = {}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [scannedAt, setScannedAt] = useState<string | null>(null);
  const [scannedFile, setScannedFile] = useState<File | null>(null);
  const [showPlan, setShowPlan] = useState(false);
  // Single selected action ID (radio behaviour)
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Phase 1 — classify image
  const classifyMutation = useMutation({
    mutationFn: classifyWaste,
    onSuccess: () => {
      setScannedAt(new Date().toLocaleString());
      queryClient.invalidateQueries({ queryKey: ["waste-scan-history"] });
    },
  });

  // Phase 2 — generate action plan (only on demand)
  const planMutation = useMutation({
    mutationFn: generateActionPlan,
    onSuccess: () => {
      setSelectedId(null);
      setShowPlan(true);
      queryClient.invalidateQueries({ queryKey: ["actions"] });
    },
  });

  function handlePick() {
    fileInputRef.current?.click();
  }

  if (triggerRef) {
    triggerRef.current = handlePick;
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPreviewUrl(URL.createObjectURL(file));
    setScannedFile(file);
    setShowPlan(false);
    setSelectedId(null);
    planMutation.reset();
    classifyMutation.mutate(file);
    event.target.value = "";
  }

  function handleScanAnother() {
    classifyMutation.reset();
    planMutation.reset();
    setPreviewUrl(null);
    setScannedFile(null);
    setScannedAt(null);
    setShowPlan(false);
    setSelectedId(null);
    fileInputRef.current?.click();
  }

  async function handleConfirm() {
    if (!planMutation.data || !selectedId) return;
    const allActions = planMutation.data.actions;
    const toDelete = allActions.filter((a) => a.id !== selectedId);

    setIsConfirming(true);
    try {
      await Promise.all(toDelete.map((a) => deleteAction(a.id)));
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      navigate("/actions");
    } finally {
      setIsConfirming(false);
    }
  }

  const result: WasteClassificationResponse | undefined = classifyMutation.data;
  const badgeClass = result ? CATEGORY_BADGE[result.category] ?? "bg-slate-100 text-slate-700" : "";
  const confidencePct = result?.confidence != null ? Math.round(result.confidence * 100) : null;

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Scan Item</h3>
        <MoreVertical className="h-4 w-4 text-slate-400" />
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Image drop zone */}
      <button
        type="button"
        onClick={handlePick}
        className="mt-4 flex aspect-square w-full items-center justify-center overflow-hidden rounded-lg border border-dashed border-slate-300 bg-slate-50"
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Scanned item" className="h-full w-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-400">
            <Camera className="h-8 w-8" />
            <span className="text-xs">Click to choose an image</span>
          </div>
        )}
      </button>

      {/* Phase 1 — classifying */}
      {classifyMutation.isPending && (
        <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Classifying…
        </div>
      )}

      {classifyMutation.isError && (
        <p className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {(classifyMutation.error as Error).message}
        </p>
      )}

      {/* Phase 1 result */}
      {result && !showPlan && (
        <>
          <span className={`mt-4 inline-flex w-fit items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${badgeClass}`}>
            <Recycle className="h-3.5 w-3.5" />
            {result.category}
          </span>

          <h4 className="mt-3 text-lg font-semibold text-slate-900">{result.item_name}</h4>
          <p className="mt-1 text-sm text-slate-600">{result.disposal_instructions}</p>

          {confidencePct !== null && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-slate-500">
                <span>Confidence</span>
                <span>{confidencePct}%</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${confidencePct}%` }} />
              </div>
            </div>
          )}

          <dl className="mt-4 space-y-2 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500">Category</dt>
              <dd className="font-medium text-slate-800">{result.category}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Disposal Guidance</dt>
              <dd className="max-w-[60%] text-right font-medium text-slate-800">
                {result.disposal_instructions}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Scanned At</dt>
              <dd className="font-medium text-slate-800">{scannedAt}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Source</dt>
              <dd className="font-medium text-slate-800">Vision API ({result.source})</dd>
            </div>
          </dl>

          <button
            type="button"
            disabled={planMutation.isPending}
            onClick={() => scannedFile && planMutation.mutate(scannedFile)}
            className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {planMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating Plan…
              </>
            ) : (
              <>
                <ClipboardList className="h-4 w-4" />
                Generate Action Plan
              </>
            )}
          </button>

          {planMutation.isError && (
            <p className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
              {(planMutation.error as Error).message}
            </p>
          )}

          <button
            type="button"
            onClick={handleScanAnother}
            className="mt-2 flex items-center justify-center gap-2 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Camera className="h-4 w-4" />
            Scan Another
          </button>
        </>
      )}

      {/* Phase 2 — action plan preview with single-select radio cards */}
      {showPlan && planMutation.data && (
        <>
          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Select a Plan
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Tap a plan to select it, then add it to your actions.
            </p>

            <div className="mt-3 space-y-2">
              {planMutation.data.actions.map((action) => {
                const est = deriveEstimates(action);
                const isSelected = selectedId === action.id;
                return (
                  <button
                    key={action.id}
                    type="button"
                    onClick={() => setSelectedId(action.id)}
                    className={`w-full rounded-lg border p-3 text-left transition-all ${
                      isSelected
                        ? "border-brand-600 bg-brand-600 shadow-sm"
                        : "border-slate-100 bg-slate-50 hover:border-brand-500 hover:bg-brand-100"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${
                          isSelected ? "bg-white/70" : PRIORITY_DOT[action.priority] ?? "bg-slate-400"
                        }`}
                      />
                      <span className={`flex-1 text-xs font-semibold ${isSelected ? "text-white" : "text-slate-800"}`}>
                        {action.title}
                      </span>
                      <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                        isSelected
                          ? "bg-white/20 text-white"
                          : action.priority === "high"
                          ? "bg-red-50 text-red-700"
                          : action.priority === "medium"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-slate-100 text-slate-600"
                      }`}>
                        {PRIORITY_LABEL[action.priority]}
                      </span>
                    </div>
                    <p className={`mt-1 text-xs ${isSelected ? "text-white/80" : "text-slate-500"}`}>
                      {action.rationale}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {est.waterL !== null && (
                        <span className={`flex items-center gap-1 text-xs ${isSelected ? "text-white/80" : "text-blue-600"}`}>
                          <Droplets className="h-3 w-3" />
                          {est.waterL.toLocaleString()} L/mo
                        </span>
                      )}
                      {est.energyKWh !== null && (
                        <span className={`flex items-center gap-1 text-xs ${isSelected ? "text-white/80" : "text-amber-600"}`}>
                          <Zap className="h-3 w-3" />
                          {est.energyKWh.toLocaleString()} kWh/mo
                        </span>
                      )}
                      <span className={`text-xs ${isSelected ? "text-white/60" : "text-slate-400"}`}>
                        ~{est.days}d to implement
                      </span>
                      {action.estimated_monthly_impact !== null && (
                        <span className={`text-xs font-medium ${isSelected ? "text-white" : "text-emerald-600"}`}>
                          ₹{action.estimated_monthly_impact.toLocaleString()}/mo
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            disabled={!selectedId || isConfirming}
            onClick={handleConfirm}
            className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-brand-700 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
          >
            {isConfirming ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Add to Actions
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleScanAnother}
            className="mt-2 flex items-center justify-center gap-2 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Camera className="h-4 w-4" />
            Scan Another
          </button>
        </>
      )}
    </div>
  );
}
