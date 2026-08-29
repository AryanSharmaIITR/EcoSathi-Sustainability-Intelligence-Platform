import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getTenant } from "../lib/apiClient";
import { useCurrentTenantId } from "../lib/tenant";

export function TenantSelector() {
  const [tenantId, setTenantId] = useCurrentTenantId();
  const [draft, setDraft] = useState(tenantId ?? "");

  const tenantQuery = useQuery({
    queryKey: ["tenant", tenantId],
    queryFn: () => getTenant(tenantId as string),
    enabled: Boolean(tenantId),
    retry: false,
  });

  return (
    <form
      className="flex flex-wrap items-center gap-2 text-sm"
      onSubmit={(event) => {
        event.preventDefault();
        setTenantId(draft.trim() || null);
      }}
    >
      <label htmlFor="tenant-id" className="text-slate-600">
        Tenant ID
      </label>
      <input
        id="tenant-id"
        type="text"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="paste tenant UUID"
        className="w-72 rounded border border-slate-300 px-2 py-1 font-mono text-xs"
      />
      <button
        type="submit"
        className="rounded bg-slate-800 px-3 py-1 text-white hover:bg-slate-700"
      >
        Set
      </button>
      {tenantId && tenantQuery.isLoading && (
        <span className="text-slate-500">checking...</span>
      )}
      {tenantId && tenantQuery.isError && (
        <span className="text-red-600">tenant not found</span>
      )}
      {tenantQuery.data && (
        <span className="text-emerald-600">
          {tenantQuery.data.name} ({tenantQuery.data.slug})
        </span>
      )}
    </form>
  );
}
