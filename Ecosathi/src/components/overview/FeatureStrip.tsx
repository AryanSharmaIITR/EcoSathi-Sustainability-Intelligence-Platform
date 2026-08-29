import { FileText, Recycle, Target, Droplet } from "lucide-react";

const FEATURES = [
  {
    icon: Recycle,
    title: "Reduce Waste",
    description: "Cut contamination and improve recycling rates.",
  },
  {
    icon: Droplet,
    title: "Save Resources",
    description: "Monitor and reduce water and energy waste.",
  },
  {
    icon: Target,
    title: "Take Action",
    description: "Data-driven recommendations for real impact.",
  },
  {
    icon: FileText,
    title: "Report & Comply",
    description: "Generate audit-ready sustainability reports.",
  },
];

export function FeatureStrip() {
  return (
    <div className="grid grid-cols-1 gap-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
      {FEATURES.map(({ icon: Icon, title, description }) => (
        <div key={title} className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <Icon className="h-4 w-4" />
          </span>
          <div>
            <div className="text-sm font-semibold text-slate-900">{title}</div>
            <div className="text-xs text-slate-500">{description}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
