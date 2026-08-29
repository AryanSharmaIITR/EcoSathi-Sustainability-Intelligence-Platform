import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "ecosathi.tenantId";
const listeners = new Set<() => void>();

function getSnapshot(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getCurrentTenantId(): string | null {
  return getSnapshot();
}

export function setCurrentTenantId(tenantId: string | null): void {
  if (tenantId) {
    localStorage.setItem(STORAGE_KEY, tenantId);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
  listeners.forEach((listener) => listener());
}

/**
 * Stand-in for real auth-derived tenant resolution (see Backend's
 * app/dependencies.py::get_current_tenant docstring) — there is no
 * auth/session system yet, so the tenant is just remembered per-browser.
 */
export function useCurrentTenantId(): [string | null, (id: string | null) => void] {
  const tenantId = useSyncExternalStore(subscribe, getSnapshot);
  const setTenantId = useCallback((id: string | null) => setCurrentTenantId(id), []);
  return [tenantId, setTenantId];
}
