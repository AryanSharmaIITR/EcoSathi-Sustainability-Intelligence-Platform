import type { LucideIcon } from "lucide-react";

interface ComingSoonPageProps {
  title: string;
  icon: LucideIcon;
  description: string;
}

export function ComingSoonPage({ title, icon: Icon, description }: ComingSoonPageProps) {
  return (
    <div className="flex h-full min-h-[70vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
        <Icon className="h-6 w-6" />
      </span>
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      <p className="max-w-sm text-sm text-slate-500">{description}</p>
      <span className="mt-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
        Coming soon
      </span>
    </div>
  );
}
