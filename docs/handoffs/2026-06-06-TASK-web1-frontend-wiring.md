# WEB-1 — Web Frontend: wire reference UI to real backend

**Layer:** `frontend/` (new) + `infra/` (minor additions)
**Reference UI source:** `ZMetrics-test-webi-nterface/frontend/` — copy as base, do NOT import from there
**Design constraint:** visual design (styles.css, layout, component structure) stays 99% unchanged.
  Only data layer (types.ts, api.ts, App.tsx) and auth wiring change.

---

## Goal

Create `d:\zmetrics\frontend\` in the monorepo by copying the reference UI and wiring it to the
ZMetrics FastAPI backend via Keycloak OIDC browser redirect auth. All static mock data in `App.tsx`
must be replaced with real API calls.

---

## Files to create / modify

### New directory structure

```
frontend/
  index.html          ← copy from reference (update <title> to "ZMetrics — БВР контроль")
  tsconfig.json       ← copy from reference unchanged
  vite.config.ts      ← copy + add API proxy
  package.json        ← copy + add keycloak-js ^25.0.0
  .env.example        ← new (document VITE_ vars)
  src/
    main.tsx          ← new (init Keycloak, render App)
    vite-env.d.ts     ← copy from reference unchanged
    styles.css        ← copy from reference UNCHANGED
    types.ts          ← replace with ZMetrics API types (see below)
    api.ts            ← replace with auth-aware API helpers (see below)
    App.tsx           ← update screens to use real data (see below)
```

---

## 1. `package.json`

Copy from reference, add one dependency:

```json
"keycloak-js": "^25.0.0"
```

---

## 2. `vite.config.ts`

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
```

---

## 3. `.env.example`

```
VITE_KC_URL=http://localhost:8080
VITE_KC_REALM=zmetrics
VITE_KC_CLIENT_ID=zmetrics-web
VITE_API_URL=/api
```

Copy to `.env` for local dev (gitignored). The frontend reads these at build time via `import.meta.env`.

---

## 4. `src/types.ts` — ZMetrics API types

Replace the reference types entirely with these:

```ts
import type { LucideIcon } from "lucide-react";

export type NavKey =
  | "auth"
  | "dashboard"
  | "quarries"
  | "sites"
  | "passports"
  | "analyses"
  | "reports"
  | "recommendations"
  | "admin";

export interface NavItem {
  key: NavKey;
  label: string;
  icon: LucideIcon;
}

// ---- ZMetrics API response types (matching backend Pydantic schemas) ----

export interface Quarry {
  id: string;
  name: string;
  location_description: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface SiteSection {
  id: string;
  quarry_id: string;
  name: string;
  block_number: string | null;
  description: string | null;
}

export interface BlastPassport {
  id: string;
  site_section_id: string;
  status: string;           // DRAFT | SUBMITTED | APPROVED | ACTIVE | COMPLETED | SUPERSEDED
  revision_number: number;
  explosive_type: string | null;
  total_explosive_kg: number | null;
  number_of_holes: number | null;
  hole_diameter_mm: number | null;
  hole_depth_m: number | null;
  burden_m: number | null;
  spacing_m: number | null;
  target_p80_mm: number | null;
  created_at: string;
  updated_at: string;
}

export interface SizeBin {
  size_mm: number;
  cumulative_passing_pct: number;
}

export interface AnalysisResult {
  id: string;
  p10_mm: number | null;
  p50_mm: number | null;
  p80_mm: number | null;
  rosin_rammler_n: number | null;
  rosin_rammler_xc: number | null;
  oversize_percent: number | null;
  fines_percent: number | null;
  confidence_score: number | null;
  confidence_notes: string | null;
  size_distribution: SizeBin[] | null;
}

export interface Report {
  id: string;
  title: string;
  report_type: string;
  analysis_method: string; // "mock" | "real"
  analysis_result_id: string;
  confidence_score: number | null;
  model_version_tag: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  report_id: string;
  status: string;  // requires_human_review | reviewed | accepted | rejected
  recommendation_text: string;
  parameter_suggestions: Record<string, unknown> | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuthUser {
  sub: string;
  preferred_username?: string;
  name?: string;
  email?: string;
}
```

---

## 5. `src/api.ts` — auth-aware API client

```ts
import Keycloak from "keycloak-js";

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
    await kc.updateToken(30).catch(() => kc.login());
    return { Authorization: `Bearer ${kc.token}` };
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
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

// ---- Domain API helpers ----

import type {
  AnalysisResult,
  BlastPassport,
  Paginated,
  Quarry,
  Recommendation,
  Report,
  SiteSection,
} from "./types";

export const api = {
  quarries: {
    list: () => get<Quarry[]>("/quarries"),
  },
  sections: {
    list: (quarryId: string) =>
      get<Paginated<SiteSection>>(`/quarries/${quarryId}/sections`).then((p) => p.items),
  },
  passports: {
    list: (quarryId: string) =>
      get<Paginated<BlastPassport>>(`/quarries/${quarryId}/passports`).then((p) => p.items),
    create: (quarryId: string, body: Partial<BlastPassport>) =>
      post<BlastPassport>(`/quarries/${quarryId}/passports`, body),
  },
  reports: {
    list: (quarryId: string) =>
      get<Report[]>(`/quarries/${quarryId}/reports`),
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
```

---

## 6. `src/main.tsx`

Init Keycloak **before** ReactDOM renders. Use `check-sso` so the app renders even when not logged in (login is on-demand via the Auth page).

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { initKeycloak } from "./api";
import App from "./App";
import "./styles.css";

const kc = initKeycloak();

kc.init({
  onLoad: "check-sso",
  silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
  pkceMethod: "S256",
}).then(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
});
```

Add `public/silent-check-sso.html`:
```html
<!doctype html>
<html><body><script>parent.postMessage(location.href, location.origin);</script></body></html>
```

---

## 7. `src/App.tsx` — screen wiring

### Changes to `App.tsx` from the reference:

**Imports**: remove all static mock arrays (`quarries`, `sites`, `passports`, `baseFractions`, `initialAnalysis`, `recommendations`). Add `api`, `kc` imports and `useState`/`useEffect` hooks where needed.

**Top-level state additions**:
```tsx
const [quarries, setQuarries] = useState<Quarry[]>([]);
const [selectedQuarryId, setSelectedQuarryId] = useState<string | null>(null);
const [sections, setSections] = useState<SiteSection[]>([]);
const [passports, setPassports] = useState<BlastPassport[]>([]);
const [reports, setReports] = useState<Report[]>([]);
const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
const [authUser, setAuthUser] = useState<AuthUser | null>(null);
```

**Auth section** — instead of the ROPC login form, wire to Keycloak:
```tsx
// On mount
useEffect(() => {
  if (kc.authenticated && kc.tokenParsed) {
    setAuthUser({
      sub: kc.subject ?? "",
      preferred_username: kc.tokenParsed["preferred_username"],
      name: kc.tokenParsed["name"],
      email: kc.tokenParsed["email"],
    });
  }
}, []);

// Quarry list load
useEffect(() => {
  if (!kc.authenticated) return;
  api.quarries.list().then(setQuarries).catch(console.error);
}, [kc.authenticated]);
```

**AuthPage** replaces the username/password form:
- If `kc.authenticated`: show `authUser.name ?? 'Пользователь'` and a "Выйти" button (`kc.logout()`)
- If not: show a single "Войти через Keycloak" `<button className="primary">` that calls `kc.login()`
- Keep the roles grid panel on the right unchanged

**QuarriesPage** — replace static `quarries` with `quarries` from state. Each card renders `quarry.name`, `quarry.location_description ?? '—'`.  Remove `rock`, `density`, `sites` fields (not in API) — show `id` last 8 chars and location instead.

**SitesPage** — add quarry selector `<select>` above the table. On change, load `api.sections.list(id)` into `sections` state. Table columns: Участок (`name`), Блок (`block_number ?? '—'`), Описание (`description ?? '—'`). Remove geology columns not in API.

**PassportsPage** — add quarry selector. Load `api.passports.list(quarryId)` into `passports`. Passport list shows: id (last 8 chars), status pill, `hole_diameter_mm ?? '—'`, `number_of_holes ?? '—'`, `total_explosive_kg ?? '—'`. Create form: `hole_diameter_mm`, `hole_depth_m`, `total_explosive_kg`, `target_p80_mm` inputs + "Сохранить" calls `api.passports.create()`.

**AnalysesPage** — keep as static placeholder (real capture flow is mobile-only in M4). Remove `onRun` prop and demo analysis mutation. Show a static info panel: "Запуск анализа выполняется через мобильное приложение ZMetrics. Результаты появятся в разделе Отчёты."

**ReportsPage** — add quarry selector. Load `api.reports.list(quarryId)`.  
- Show `report.title`, `report.report_type`, `report.analysis_method` pill  
- **SAFETY**: if `report.analysis_method === 'mock'`, show `⚠ Синтетические данные` badge (same rose color as priority-high border)  
- "Скачать JSON" button fetches `api.reports.exportUrl(report.id)` with auth header and triggers browser download (use `window.open` with token in query or programmatic fetch + Blob)  
- "Рекомендации" button loads `api.recommendations.list(reportId)` and navigates to recommendations tab

**RecommendationsPage** — show `recommendations` from state. Each card:
- Title: first 40 chars of `recommendation_text`
- Body: full `recommendation_text`
- Status chip: `status` value
- `parameter_suggestions` shown as read-only key/value list with label "Справочные параметры (только для просмотра):"
- Review buttons: "Принять" / "Отклонить" / "Ознакомлен" → call `api.recommendations.review()`
- **SAFETY**: never show a button that writes `parameter_suggestions` back to a passport

**Dashboard** — replace static values with computed from state:
- Quarry count card: `quarries.length`
- D80 card: from latest report's analysis result (fetch once on load)
- Fraction histogram: from latest `AnalysisResult.size_distribution` mapped to `{ label: bin.size_mm + ' мм', percent: bin.cumulative_passing_pct }`
- "Последние участки" table: use `sections` state (first quarry's sections)

**Topbar** — right side: replace static API badge with real `backendOnline` (keep); add `authUser?.preferred_username ?? authUser?.email ?? ''` next to it.

---

## 8. Keycloak realm — add `zmetrics-web` client

Edit `infra/keycloak/realm-export.json`. In the `clients` array, add after `zmetrics-mobile`:

```json
{
  "clientId": "zmetrics-web",
  "name": "ZMetrics Web",
  "enabled": true,
  "publicClient": true,
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "redirectUris": [
    "http://localhost:5173/*",
    "http://localhost:3000/*"
  ],
  "webOrigins": [
    "http://localhost:5173",
    "http://localhost:3000"
  ],
  "attributes": {
    "pkce.code.challenge.method": "S256"
  }
}
```

---

## 9. `infra/docker-compose.yml` — add frontend service

Add after the `worker` service:

```yaml
  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "5173:80"
    depends_on:
      - backend
    networks: [zmetrics]
```

Create `frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Create `frontend/nginx.conf`:
```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  location / {
    try_files $uri $uri/ /index.html;
  }
  location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_set_header Host $host;
  }
}
```

---

## 10. Backend CORS update

In `infra/docker-compose.yml`, `backend` service env, update:
```yaml
BACKEND_CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173","http://localhost:5173"]'
```
(already present — verify it includes `5173`)

---

## Safety invariants (must remain true in the web frontend)

- `parameter_suggestions` displayed read-only only — no form element writes them to a passport
- Reports with `analysis_method === 'mock'` MUST show the `⚠ Синтетические данные` badge
- Review buttons only offer: принять / отклонить / ознакомлен — no auto-approve
- Export button fetches with auth; no permanent public URLs
- No hardcoded Keycloak credentials in source files — all via `VITE_` env vars

---

## Acceptance criteria

- [ ] `cd frontend && npm run dev` starts without errors; opens at http://localhost:5173
- [ ] "Войти через Keycloak" redirects to Keycloak; successful login returns to app with user name in topbar
- [ ] Карьеры screen loads real quarries from backend
- [ ] Участки screen loads sections for selected quarry
- [ ] Паспорта БВР loads passports; create form POSTs successfully
- [ ] Отчёты loads reports; mock reports show `⚠ Синтетические данные`
- [ ] Рекомендации loads and review buttons work
- [ ] Dashboard shows live data
- [ ] `npm run build` produces a dist/ without TypeScript errors
- [ ] `docker compose ... up frontend` builds and serves on port 5173
- [ ] `tsc --noEmit` passes (no type errors)
