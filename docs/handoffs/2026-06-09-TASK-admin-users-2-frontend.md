# ADMIN-USERS-2 — Admin user management UI (Frontend)

**Layer:** `frontend/` only (`src/api.ts`, `src/types.ts`, `src/App.tsx`)
**Depends on:** ADMIN-USERS-1 (backend) merged — endpoints live
**Backend changes:** none
**Review agent:** frontend reviewer (focus: admin-only UX, secret-handling in UI, error/empty states, `tsc --noEmit`)

---

## Goal

Replace the static `AdminPage` placeholder ([App.tsx:2590](../../frontend/src/App.tsx#L2590), which currently just says "manage users in Keycloak Admin Console") with a working admin screen:

1. **User list** — from `GET /admin/users`
2. **Create user** — email + ФИО → `POST /admin/users` → show the returned **temporary password once**
3. **Edit user** — ФИО, email, активность (`PATCH /admin/users/{id}`)
4. **Activate / deactivate** — toggle `is_active`; deactivate via `DELETE /admin/users/{id}` (self-deactivate is blocked by backend → show the 400 message)
5. **Reset password** — `POST /admin/users/{id}/reset-password` → show new temp password once
6. **Per-quarry roles** — list via `GET /admin/users/{id}/access`; grant via `POST /admin/quarries/{qid}/access`; revoke via `DELETE /admin/quarries/{qid}/access/{aid}`

**UX safety:** the temporary password is shown exactly once in a clearly-labelled box with a copy button and a warning «Пароль больше не будет показан». Do not persist it (no localStorage, no re-fetch). Clear it from component state when the dialog/box is dismissed.

The whole screen is admin-only. The `admin` nav item already exists ([App.tsx:65](../../frontend/src/App.tsx#L65)). On any `403` from these endpoints, show «Недостаточно прав» rather than a raw error.

---

## 1. `src/api.ts`

Only `get`/`post` helpers exist today. **Add `patch` and `del`** mirroring the existing `post` (auth header + JSON + `res.ok` check):

```ts
async function patch<T>(path: string, body: unknown): Promise<T> { /* method: "PATCH" */ }
async function del(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}/v1${path}`, { method: "DELETE", headers: { ...(await authHeader()) } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}
```

Add an `admin` group (alongside the existing `auditLogs` helper):
```ts
admin: {
  users: {
    list: () => get<Paginated<AdminUser>>("/admin/users").then((p) => p.items),
    create: (body: { email: string; full_name: string }) =>
      post<UserCreateResult>("/admin/users", body),
    update: (id: string, body: Partial<{ full_name: string; email: string; is_active: boolean }>) =>
      patch<AdminUser>(`/admin/users/${id}`, body),
    deactivate: (id: string) => del(`/admin/users/${id}`),
    resetPassword: (id: string) => post<PasswordResetResult>(`/admin/users/${id}/reset-password`, {}),
    listAccess: (id: string) => get<UserQuarryAccess[]>(`/admin/users/${id}/access`),
  },
  access: {
    grant: (quarryId: string, body: { user_id: string; quarry_id: string; role_name: string }) =>
      post<{ id: string }>(`/admin/quarries/${quarryId}/access`, body),
    revoke: (quarryId: string, accessId: string) =>
      del(`/admin/quarries/${quarryId}/access/${accessId}`),
  },
},
```
(`Paginated<T>` already imported in api.ts. Reuse `api.quarries.list()` for the quarry picker.)

---

## 2. `src/types.ts`

```ts
export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}
export interface UserCreateResult { user: AdminUser; temporary_password: string; }
export interface PasswordResetResult { temporary_password: string; }
export interface UserQuarryAccess {
  access_id: string;
  quarry_id: string;
  quarry_name: string;
  role_name: string;
  role_level: number;
}
```
(Confirm field names match ADMIN-USERS-1 response schemas exactly — `access_id`, not `id`.)

---

## 3. `src/App.tsx` — rewrite `AdminPage`

Replace the placeholder body. Suggested layout (reuse existing `data-panel` / `form-section` / `PanelTitle` styles already in the file):

**Left panel — Пользователи**
- Table/cards: ФИО, email, статус (Активен / Отключён badge), дата создания
- Кнопка «+ Создать пользователя» opens an inline form (email, ФИО) → `admin.users.create`
- On success: render the temp-password box (см. ниже) and refresh the list
- Row actions: «Редактировать», «Сбросить пароль», «Активен» toggle (deactivate/reactivate)
  - reactivate = `admin.users.update(id, { is_active: true })`; deactivate = `admin.users.deactivate(id)`

**Right panel — Роли выбранного пользователя**
- Appears when a user row is selected
- Lists `admin.users.listAccess(id)` → quarry name + role badge + «Отозвать» (`admin.access.revoke(quarry_id, access_id)`)
- «Назначить роль» form: quarry `<select>` (from `api.quarries.list()`) + role `<select>` (`user`/`surveyor`/`blaster`/`admin`) → `admin.access.grant(quarryId, { user_id, quarry_id: quarryId, role_name })` → refresh access list

**Temp-password box (create & reset)** — render only while a password is in state:
```
⚠ Временный пароль для <email>: <код-моноширинный>  [Копировать]
Передайте его пользователю безопасным способом. Пароль больше не будет показан.
[Скрыть]  ← clears it from state
```
The user must change it at next login (backend sets `temporary: true`).

**State (local to AdminPage):**
```ts
const [users, setUsers] = useState<AdminUser[]>([]);
const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
const [accesses, setAccesses] = useState<UserQuarryAccess[]>([]);
const [tempPassword, setTempPassword] = useState<{ email: string; password: string } | null>(null);
const [adminError, setAdminError] = useState<string | null>(null);
const [busy, setBusy] = useState(false);
```
- Load users in `useEffect` guarded by `kc.authenticated`. On `403` set a «Недостаточно прав» state and render nothing sensitive.
- Use `try/catch` around every mutation; surface `adminError`; clear it on the next action.
- After create/update/deactivate/grant/revoke → re-fetch the affected list (`users` and/or `accesses`).

---

## Acceptance criteria

1. `npm run build` / `tsc --noEmit` — 0 errors
2. AdminPage shows the real user list; «Создать пользователя» creates one and shows the temp password once
3. Editing ФИО/email/активность persists (reload shows the change)
4. Reset-password shows a new temp password once; copy button works
5. Per-quarry role grant/revoke updates the selected user's access list without reload
6. Non-admin (or 403): screen shows «Недостаточно прав», no crash, no leaked data
7. Temp password is never written to localStorage and disappears from the DOM after «Скрыть»

---

## Safety checklist for the executor

- [ ] Temp password: shown once, copy-only, cleared from state on dismiss, never persisted
- [ ] All admin calls handle `403` gracefully (no raw error dumps)
- [ ] `keycloak_sub` is not referenced anywhere (backend never sends it)
- [ ] No write-back of roles to passports or any blast-domain entity (identity/RBAC only)
- [ ] `tsc --noEmit` clean; no `as unknown as X`

---

## Explicitly out of scope

- Backend changes (done in ADMIN-USERS-1)
- Audit-log viewer UI (separate WEB-3 item — leave the existing audit panel note as-is or wire later)
- Bulk operations, search/pagination beyond the existing list (add only if trivial)
- Email delivery of passwords (admin conveys out-of-band)
