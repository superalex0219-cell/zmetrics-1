# WEB-2 — Passport Workflow in Web

**Layer:** `frontend/` only  
**Depends on:** WEB-1 done ✅, M5-a done ✅  
**Backend changes:** none — all endpoints already exist  
**Target:** `tsc --noEmit` clean; no new tests required (no test infra in frontend)

---

## Goal

`PassportsPage` currently has a list of passports and a create form. There is no way to:
- See full passport details
- Transition status (DRAFT → SUBMITTED → APPROVED → ACTIVE → COMPLETED)
- Create a blast event after approval
- See the audit history for a passport

WEB-2 wires all of this to the existing backend endpoints.

---

## Backend endpoints used (all exist, no changes needed)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/quarries/{q}/passports/{p}` | USER | Fetch full passport detail |
| `POST` | `/api/v1/quarries/{q}/passports/{p}/submit` | BLASTER | DRAFT → SUBMITTED |
| `POST` | `/api/v1/quarries/{q}/passports/{p}/approve` | ADMIN | SUBMITTED → APPROVED |
| `POST` | `/api/v1/quarries/{q}/passports/{p}/activate` | ADMIN | APPROVED → ACTIVE |
| `POST` | `/api/v1/quarries/{q}/passports/{p}/complete` | ADMIN | ACTIVE → COMPLETED |
| `GET` | `/api/v1/quarries/{q}/passports/{p}/blast-event` | USER | Fetch blast event (404 if none) |
| `POST` | `/api/v1/quarries/{q}/passports/{p}/blast-event` | BLASTER | Create blast event |
| `GET` | `/api/v1/admin/audit-logs?entity_type=blast_passport` | ADMIN | Audit log (403 for non-admin) |

---

## Files to modify

| File | Change |
|------|--------|
| `frontend/src/types.ts` | Add `BlastEvent`, `AuditLogEntry` |
| `frontend/src/api.ts` | Add `passports.get/submit/approve/activate/complete`, `blastEvents.get/create`, `auditLogs.forPassport` |
| `frontend/src/App.tsx` | Rewrite `PassportsPage` with detail panel; no other component changes |

---

## 1. `frontend/src/types.ts` — additions

Add two new interfaces:

```typescript
export interface BlastEvent {
  id: string;
  passport_id: string;
  executed_by_id: string;
  blast_datetime: string;       // ISO string
  actual_explosive_kg: number | null;
  weather_conditions: string | null;
  notes: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  occurred_at: string;          // ISO string
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
}
```

No changes to existing interfaces.

---

## 2. `frontend/src/api.ts` — additions

Import the two new types at the top.

### 2a. Extend `api.passports`

```typescript
passports: {
  // existing:
  list: (quarryId: string) => ...,
  create: (quarryId: string, body: ...) => ...,

  // new:
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
```

### 2b. New `api.blastEvents`

```typescript
blastEvents: {
  get: (quarryId: string, passportId: string) =>
    get<BlastEvent>(`/quarries/${quarryId}/passports/${passportId}/blast-event`),

  create: (
    quarryId: string,
    passportId: string,
    body: { blast_datetime: string; actual_explosive_kg?: number | null; weather_conditions?: string | null; notes?: string | null }
  ) =>
    post<BlastEvent>(`/quarries/${quarryId}/passports/${passportId}/blast-event`, body),
},
```

### 2c. New `api.auditLogs`

```typescript
auditLogs: {
  forPassport: async (passportId: string): Promise<AuditLogEntry[]> => {
    const all = await get<AuditLogEntry[]>("/admin/audit-logs?entity_type=blast_passport");
    return all.filter((e) => e.entity_id === passportId);
  },
},
```

Note: this will throw on 403 (non-admin). Callers must catch and treat as empty list.

---

## 3. `frontend/src/App.tsx` — `PassportsPage` rewrite

### 3a. Props unchanged

`PassportsPage` keeps its existing props signature:
```typescript
{
  quarries: Quarry[];
  sections: SiteSection[];
  selectedQuarryId: string | null;
  onSelectQuarry: (id: string) => void;
  passports: BlastPassport[];
  onCreated: (p: BlastPassport) => void;
}
```

`onCreated` is also extended to handle updates: add `onUpdated: (p: BlastPassport) => void` to the props so that when a status transition or blast event creation changes the passport, `App` state is updated too.

In `App.tsx` pass `onUpdated={(p) => setPassports(prev => prev.map(x => x.id === p.id ? p : x))}`.

### 3b. Local state inside `PassportsPage`

```typescript
const [showCreate, setShowCreate] = useState(false);
const [detailId, setDetailId] = useState<string | null>(null);
const [detail, setDetail] = useState<BlastPassport | null>(null);
const [blastEvent, setBlastEvent] = useState<BlastEvent | null>(null);
const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
const [detailLoading, setDetailLoading] = useState(false);
const [detailError, setDetailError] = useState<string | null>(null);
const [transitioning, setTransitioning] = useState(false);
const [showBlastEventForm, setShowBlastEventForm] = useState(false);
```

### 3c. Layout

Retain the `content-grid two` layout. Left column: list. Right column: switches between three states:
- **No selection and not creating**: prompt "Выберите паспорт или создайте новый" + "Создать паспорт" button
- **Creating** (`showCreate`): existing create form (unchanged)
- **Detail open** (`detailId !== null`): `<PassportDetail>` component (see below)

Passport list rows become clickable:
```tsx
<article
  className={`passport-row ${detailId === passport.id ? "selected" : ""}`}
  key={passport.id}
  onClick={() => void handleSelectPassport(passport)}
  style={{ cursor: "pointer" }}
>
```

Add a "Создать паспорт" button above the list that sets `showCreate = true` and `detailId = null`.

### 3d. `handleSelectPassport(passport: BlastPassport)`

```typescript
const handleSelectPassport = async (passport: BlastPassport) => {
  setShowCreate(false);
  setDetailId(passport.id);
  setDetailLoading(true);
  setDetailError(null);
  setBlastEvent(null);
  setAuditLog([]);
  setShowBlastEventForm(false);

  try {
    const [fullPassport, ...rest] = await Promise.allSettled([
      api.passports.get(selectedQuarryId!, passport.id),
      api.blastEvents.get(selectedQuarryId!, passport.id),
      api.auditLogs.forPassport(passport.id),
    ]);

    if (fullPassport.status === "fulfilled") {
      setDetail(fullPassport.value);
    }
    if (rest[0].status === "fulfilled") {
      setBlastEvent(rest[0].value);
    }
    // rest[0] rejected = 404 (no blast event yet) — leave blastEvent as null
    // rest[1] rejected = 403 (not admin) — leave auditLog as []
    if (rest[1].status === "fulfilled") {
      setAuditLog(rest[1].value);
    }
  } catch (err) {
    setDetailError(err instanceof Error ? err.message : "Ошибка загрузки");
  } finally {
    setDetailLoading(false);
  }
};
```

Use `Promise.allSettled` — blast event 404 and audit log 403 must NOT surface as errors.

### 3e. `handleTransition(action: "submit" | "approve" | "activate" | "complete")`

```typescript
const handleTransition = async (action: "submit" | "approve" | "activate" | "complete") => {
  if (!detail || !selectedQuarryId) return;
  setTransitioning(true);
  setDetailError(null);
  try {
    const updated = await api.passports[action](selectedQuarryId, detail.id);
    setDetail(updated);
    onUpdated(updated);
  } catch (err) {
    setDetailError(err instanceof Error ? err.message : `Ошибка: ${action}`);
  } finally {
    setTransitioning(false);
  }
};
```

### 3f. `handleCreateBlastEvent(form: BlastEventFormData)`

```typescript
const handleCreateBlastEvent = async (form: BlastEventFormData) => {
  if (!detail || !selectedQuarryId) return;
  setTransitioning(true);
  setDetailError(null);
  try {
    const event = await api.blastEvents.create(selectedQuarryId, detail.id, {
      blast_datetime: form.blast_datetime,
      actual_explosive_kg: form.actual_explosive_kg || null,
      weather_conditions: form.weather_conditions || null,
      notes: form.notes || null,
    });
    setBlastEvent(event);
    setShowBlastEventForm(false);
  } catch (err) {
    setDetailError(err instanceof Error ? err.message : "Ошибка создания взрыва");
  } finally {
    setTransitioning(false);
  }
};
```

---

## 4. `PassportDetail` sub-component

Extract into a function component inside `App.tsx` (no new file needed). Props:

```typescript
{
  passport: BlastPassport;
  blastEvent: BlastEvent | null;
  auditLog: AuditLogEntry[];
  loading: boolean;
  error: string | null;
  transitioning: boolean;
  showBlastEventForm: boolean;
  onTransition: (action: "submit" | "approve" | "activate" | "complete") => void;
  onShowBlastEventForm: () => void;
  onCreateBlastEvent: (form: BlastEventFormData) => void;
  onClose: () => void;
}
```

### 4a. Passport fields section

Show all fields as a `<dl>` grid:

| Field | Value |
|-------|-------|
| Статус | `<PassportStatusBadge status={passport.status} />` |
| Ревизия | `passport.revision_number` |
| Участок | `passport.site_section_id` (show just last 8 chars if section name not in scope) |
| Тип ВВ | `passport.explosive_type ?? "—"` |
| Количество скважин | `passport.number_of_holes ?? "—"` |
| Диаметр скв. | `passport.hole_diameter_mm ? "${value} мм" : "—"` |
| Глубина скв. | `passport.hole_depth_m ? "${value} м" : "—"` |
| Сетка (ширина × ряд) | `${passport.burden_m ?? "—"} × ${passport.spacing_m ?? "—"} м` |
| Масса ВВ | `passport.total_explosive_kg ? "${value} кг" : "—"` |
| Цель P80 | `passport.target_p80_mm ? "${value} мм" : "не задан"` |
| Создан | `new Date(passport.created_at).toLocaleDateString("ru-RU")` |

### 4b. `PassportStatusBadge`

Small helper component — styled `<span>` with status-specific color:

| Status | Color | Russian label |
|--------|-------|---------------|
| `DRAFT` | grey | Черновик |
| `SUBMITTED` | amber | На проверке |
| `APPROVED` | blue | Утверждён |
| `ACTIVE` | teal | Активен |
| `COMPLETED` | green | Завершён |
| `SUPERSEDED` | muted | Заменён |

Use inline `style` consistent with existing `status-pill` class where possible.

### 4c. State transition buttons section

Show only the button that applies to the **current status**. Use the existing button styling. Disable while `transitioning`.

```
DRAFT      → "Подать на проверку"  (submit)
SUBMITTED  → "Утвердить"           (approve)
APPROVED   → "Активировать"        (activate)
ACTIVE     → "Завершить"           (complete)
COMPLETED  → (no button, show "Паспорт завершён")
SUPERSEDED → (no button, show "Паспорт заменён")
```

**Safety note in spec:** These buttons trigger one HTTP POST each. The server enforces role requirements. If the user lacks permission, the server returns 403 and `detailError` is shown. **No client-side role bypass.** **No auto-transitions.**

### 4d. Blast event section

Show after the status buttons, only when `passport.status === "APPROVED" || passport.status === "ACTIVE"`.

**If blast event exists** (`blastEvent !== null`):
```
section heading "Взрыв проведён"
  Дата/время: {new Date(blastEvent.blast_datetime).toLocaleString("ru-RU")}
  Фактич. ВВ: {blastEvent.actual_explosive_kg ? "${v} кг" : "—"}
  Погода:     {blastEvent.weather_conditions ?? "—"}
  Заметки:    {blastEvent.notes ?? "—"}
```

**If no blast event and `!showBlastEventForm`**:
```
<button onClick={onShowBlastEventForm}>Зарегистрировать взрыв</button>
```

**If `showBlastEventForm`** — inline form with:
- `blast_datetime`: `<input type="datetime-local">` — **required**
- `actual_explosive_kg`: `<input type="number">` — optional
- `weather_conditions`: `<input type="text">` — optional
- `notes`: `<textarea>` — optional
- Submit button: "Зарегистрировать" (disabled while `transitioning`)
- Cancel button: hides form

Form `onSubmit` calls `onCreateBlastEvent(formData)`. Validate that `blast_datetime` is non-empty before calling.

### 4e. Audit log section

Always rendered when `auditLog.length > 0`. If empty (either 403 or no entries), section is hidden entirely.

```
section heading "История изменений"
<table>
  <thead>
    <tr>
      <th>Дата</th>
      <th>Действие</th>
      <th>Было</th>
      <th>Стало</th>
    </tr>
  </thead>
  <tbody>
    {auditLog.map(entry => (
      <tr key={entry.id}>
        <td>{new Date(entry.occurred_at).toLocaleString("ru-RU")}</td>
        <td>{entry.action}</td>
        <td>{entry.old_value ? JSON.stringify(entry.old_value) : "—"}</td>
        <td>{entry.new_value ? JSON.stringify(entry.new_value) : "—"}</td>
      </tr>
    ))}
  </tbody>
</table>
```

### 4f. Error display

Show `detailError` as a red paragraph below the status buttons (same pattern as existing `saveError`).

### 4g. Close / back button

A "← К списку" button at the top of the detail panel sets `setDetailId(null)` + `setDetail(null)`.

---

## 5. `BlastEventFormData` type (local to `PassportsPage`)

```typescript
type BlastEventFormData = {
  blast_datetime: string;
  actual_explosive_kg: string;
  weather_conditions: string;
  notes: string;
};
```

Converted to numbers/nulls in `handleCreateBlastEvent` before the API call.

---

## Safety checklist for executor

Before marking done:

- [ ] State transition buttons: each button triggers exactly one `POST`, no chaining
- [ ] No button auto-clicks or auto-submits — every transition is an explicit user click
- [ ] `blast_datetime` is required in the blast event form — no submission without it
- [ ] `parameter_suggestions` display is unchanged (read-only, WEB-1 already correct)
- [ ] `blastEvent` 404 response is caught silently — shows "Зарегистрировать взрыв" button, not an error
- [ ] Audit log 403 response is caught silently — section hidden, not an error
- [ ] `tsc --noEmit` passes with zero errors after changes

---

## Acceptance criteria

1. `tsc --noEmit` — 0 errors
2. Clicking a passport row in the list opens a detail panel on the right with all fields
3. A DRAFT passport shows "Подать на проверку" button; clicking it → status changes to SUBMITTED in list and detail
4. A SUBMITTED passport shows "Утвердить" button; clicking it → status changes to APPROVED (will fail with 403 if user is not ADMIN — error shown, no crash)
5. An APPROVED passport shows "Активировать" button AND "Зарегистрировать взрыв" button
6. Blast event form: filling `blast_datetime` and clicking "Зарегистрировать" creates the event; form hides; event details shown read-only
7. Blast event form: clicking without filling `blast_datetime` does nothing (HTML required or manual guard)
8. After creating a blast event, clicking the same passport again shows the event data, not the create form
9. "← К списку" button returns to list view (no passport selected)
10. `detailError` shown on 409 or 403 response without crashing

---

## Explicitly out of scope

- No role detection on the client — server enforces roles, client shows 403 error
- No revision workflow (revise button) — M6+
- No CaptureSession creation from web — mobile only
- No WEB-3 admin panel (user list, role assignment) — separate task
- No audit log filtering by date or actor — simple table is sufficient
- No passport field editing (PUT endpoint) — detail is read-only for existing passports
