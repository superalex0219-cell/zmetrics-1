import Keycloak from "keycloak-js";

import type {
  AnalysisResult,
  AuditLogEntry,
  BlastEvent,
  BlastPassport,
  Paginated,
  Quarry,
  Recommendation,
  Report,
  SiteSection,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

// Singleton Keycloak instance — initialised in main.tsx before React renders.
export let kc: Keycloak;

export function initKeycloak(): Keycloak {
  kc = new Keycloak({
    url: import.meta.env.VITE_KC_URL ?? "http://localhost:8080",
    realm: import.meta.env.VITE_KC_REALM ?? "zmetrics",
    clientId: import.meta.env.VITE_KC_CLIENT_ID ?? "zmetrics-web",
  });
  return kc;
}

/** Refresh token if it expires within 30 s, then return Bearer header. */
async function authHeader(): Promise<Record<string, string>> {
  if (kc?.authenticated) {
    await kc.updateToken(30).catch(() => {
      void kc.login();
    });
    return { Authorization: `Bearer ${kc.token ?? ""}` };
  }
  return {};
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/v1${path}`, {
    headers: { ...(await authHeader()), "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}/v1${path}`, {
    method: "POST",
    headers: { ...(await authHeader()), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function checkBackend(): Promise<boolean> {
  try {
    const res = await fetch("/health");
    return res.ok;
  } catch {
    return false;
  }
}

/** Authenticated file download — fetches with Bearer token, triggers browser save.
 *  Only attaches auth headers to same-origin API URLs to prevent token leakage. */
export async function downloadWithAuth(url: string, filename: string): Promise<void> {
  const isApiUrl = url.startsWith(API_BASE) || url.startsWith("/api");
  const headers = isApiUrl ? await authHeader() : {};
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Domain API helpers ----

export const api = {
  quarries: {
    list: () =>
      get<Paginated<Quarry>>("/quarries").then((p) => p.items),
  },
  sections: {
    list: (quarryId: string) =>
      get<Paginated<SiteSection>>(`/quarries/${quarryId}/sections`).then((p) => p.items),
  },
  passports: {
    list: (quarryId: string) =>
      get<Paginated<BlastPassport>>(`/quarries/${quarryId}/passports`).then((p) => p.items),
    create: (quarryId: string, body: Partial<BlastPassport> & { site_section_id: string }) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports`, body),
    get: (quarryId: string, passportId: string) =>
      get<BlastPassport>(`/quarries/${quarryId}/passports/${passportId}`),
    submit: (quarryId: string, passportId: string) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports/${passportId}/submit`, {}),
    approve: (quarryId: string, passportId: string) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports/${passportId}/approve`, {}),
    activate: (quarryId: string, passportId: string) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports/${passportId}/activate`, {}),
    complete: (quarryId: string, passportId: string) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports/${passportId}/complete`, {}),
  },
  blastEvents: {
    get: (quarryId: string, passportId: string) =>
      get<BlastEvent>(`/quarries/${quarryId}/passports/${passportId}/blast-event`),
    create: (
      quarryId: string,
      passportId: string,
      body: {
        blast_datetime: string;
        actual_explosive_kg?: number | null;
        weather_conditions?: string | null;
        notes?: string | null;
      },
    ) => post<BlastEvent>(`/quarries/${quarryId}/passports/${passportId}/blast-event`, body),
  },
  auditLogs: {
    // Throws on 403 (non-admin) — callers must catch and treat as an empty list.
    forPassport: (passportId: string): Promise<AuditLogEntry[]> =>
      get<AuditLogEntry[]>(
        `/admin/audit-logs?entity_type=blast_passport&entity_id=${encodeURIComponent(passportId)}&page_size=200`,
      ),
  },
  reports: {
    list: (quarryId: string) =>
      get<Paginated<Report>>(`/quarries/${quarryId}/reports`).then((p) => p.items),
    exportUrl: (reportId: string) => `${API_BASE}/v1/reports/${reportId}/export`,
  },
  recommendations: {
    list: (reportId: string) =>
      get<Paginated<Recommendation>>(`/reports/${reportId}/recommendations`).then(
        (p) => p.items,
      ),
    review: (reportId: string, recId: string, status: string, notes?: string) =>
      post<Recommendation>(`/reports/${reportId}/recommendations/${recId}/review`, {
        status,
        reviewer_notes: notes ?? null,
      }),
  },
  analysisResults: {
    get: (id: string) => get<AnalysisResult>(`/analysis-results/${id}`),
  },
};
