# ZMetrics — Roadmap

Last sync: 2026-06-07 | HEAD: `849e1f9`

---

## DONE

### M0 — Foundation (`d7a1983`)
- [x] Monorepo structure (backend / worker / mobile / infra / docs)
- [x] Docker Compose: Postgres 16, Redis 7, MinIO, Keycloak 24, backend, worker
- [x] SQLAlchemy 2.0 async models for all domain entities
- [x] Alembic migrations with async env
- [x] FastAPI skeleton: JWT auth, CRUD endpoints, health
- [x] Mock CV pipeline: 7 steps via `PipelineStep` interface
- [x] `AnalysisResult` computed from synthetic data (Rosin-Rammler)
- [x] Pytest smoke tests

### M1 — Backend MVP + Security (`d162899` → `aa4c42f`)
- [x] Keycloak JWT validation (RS256, JWKS fetch at runtime, issuer check)
- [x] Per-quarry RBAC (`QuarryUserAccess`, `RoleLevel` USER/SURVEYOR/BLASTER/ADMIN)
- [x] Full CRUD: quarries, site_sections, blast_passports (7-state machine)
- [x] BlastEvent creation + CaptureSession + Artifact upload (MinIO presigned)
- [x] AnalysisJob enqueue → Celery → AnalysisResult → Report → Recommendation
- [x] AuditLog written on passport/recommendation/role/access state changes
- [x] `GET /api/v1/analysis-results/{id}` (GAP-1)
- [x] `ReportRead.analysis_method` derived from `ModelVersion.model_type` (GAP-2)
- [x] Integration test suite: 53 tests against real Postgres
- [x] SEC-1: IDOR in `add_comment` fixed
- [x] SEC-2: `keycloak_sub` removed from API responses
- [x] SEC-3: `dev-seed` gated behind `ENABLE_DEV_SEED` flag
- [x] DB-1: `AnalysisJob.model_version_id` index + migration
- [x] BACK-SEC-2: IDOR batch — `capture_sessions`, `blast_events`, `analysis` + magic-byte validation + AuditLog in dev_seed

### M4 — Flutter Mobile (`796823a` → `ebb28e5`)
- [x] Per-quarry RBAC: `AccessCubit`, `RoleLevel`, role-gated UI actions
- [x] Quarry / section / passport list + create screens
- [x] Passport state-machine UI (all 5 transitions, human-driven only)
- [x] Offline queue: `SyncManager` (SQLite backend), idempotency keys, retry ×5
- [x] Report screen: P10/P50/P80, Rosin-Rammler, cumulative passing table, mock badge
- [x] Recommendation review (ACCEPT / REJECT / REVIEWED) + inline comments
- [x] MOB-1: `getAnalysisResult` wired to live backend
- [x] MOB-2: OIDC PKCE via `flutter_appauth` (Keycloak `zmetrics-mobile` client)
- [x] MOB-3: Capture flow — device/calibration picker, SyncProcessor, job polling, navigate to reports
- [x] MOB-4: Report JSON export via Android share sheet (`share_plus`)
- [x] MOB-DESIGN: Teal theme `0xFF0F766E`, dark AppBar `0xFF17202A`, Russian labels, `StatCard` widget
- [x] 63 tests total

### WEB-1 — React Web Frontend (`09ca465`)
- [x] React + Vite + TypeScript + Lucide + plain CSS (matches reference design)
- [x] Keycloak OIDC browser redirect (check-sso + PKCE, `zmetrics-web` Keycloak client)
- [x] Auth screen: Keycloak redirect, display name in topbar, logout
- [x] Dashboard: live quarry/section/report counts, latest analysis P80, fraction histogram
- [x] Карьеры: real quarry cards from `GET /api/v1/quarries`
- [x] Участки: quarry selector → `GET /api/v1/quarries/{id}/sections`
- [x] Паспорта БВР: list + create form → `POST /api/v1/quarries/{id}/passports`
- [x] Отчёты: list + JSON export (Bearer auth download), `⚠ Синтетические данные` mock badge
- [x] Рекомендации: list + review (принять/отклонить/ознакомлен); `parameter_suggestions` read-only
- [x] `frontend` service in docker-compose, nginx proxy, Dockerfile
- [x] `tsc --noEmit` passes

### M5-a — Rule-based recommendations · `worker/` (`4435f28`)
- [x] `evaluate_fragmentation()` pure function — oversize (`p80 > target × 1.1`), excessive fines (`> 15%`), on_target
- [x] `parameter_suggestions` JSONB: `observed_p80_mm`, `target_p80_mm`, `deviation_pct`, `basis`; `None` when target unknown
- [x] `BlastEvent` + `BlastPassport` read-only stubs in `worker/app/db_models.py`
- [x] Join chain `CaptureSession → BlastEvent → BlastPassport` in `_create_report_and_recommendation`
- [x] `confidence_notes` auto-populated when `confidence_score < 0.8`
- [x] 15 unit tests for rule logic

### WEB-2 — Passport workflow in web · `frontend/` (`849e1f9`)
- [x] Passport detail panel: all fields, colored status badge, click-to-open from list
- [x] State transitions: DRAFT→SUBMITTED→APPROVED→ACTIVE→COMPLETED (one button per status, one POST each)
- [x] Blast event registration form (APPROVED/ACTIVE only; `blast_datetime` required)
- [x] AuditLog display (hidden silently on 403; hidden when empty)
- [x] `Promise.allSettled` — 404 blast event and 403 audit log are silent, never shown as errors
- [x] `onUpdated` prop wired: status changes reflected immediately in passport list
- [x] `tsc --noEmit` — 0 errors

---

## QA & USER TESTING

User testing is done by the product owner directly in the browser UI.
Bug hunts are periodic code-review tasks run by an executor agent (no UI needed).

---

### UT-1 — Web UI smoke test · browser @ http://localhost:5173
*Run after Docker rebuild following WEB-2.*

**Pre-condition:** `docker compose -f infra\docker-compose.yml up -d` + `ENABLE_DEV_SEED=true` seed ran.

- [ ] Войти через Keycloak → имя пользователя появилось в топбаре
- [ ] Dashboard: карточки карьеров/участков/отчётов показывают числа (не "—")
- [ ] Карьеры: карточки с названиями и локацией
- [ ] Участки: выбор карьера → список участков обновляется
- [ ] Паспорта — список: строки кликабельны; выбранная строка подсвечена
- [ ] Паспорта — деталь: поля заполнены (статус, ревизия, скважины, цель P80)
- [ ] Паспорта — переход DRAFT → SUBMITTED: нажать "Подать на проверку" → статус обновился в списке и детали
- [ ] Паспорта — переход SUBMITTED → APPROVED (от admin-пользователя): кнопка "Утвердить" → APPROVED
- [ ] Паспорта — APPROVED: видна кнопка "Зарегистрировать взрыв"
- [ ] Взрыв: заполнить дату → "Зарегистрировать" → форма скрылась, данные взрыва показаны
- [ ] Взрыв: кнопка "Зарегистрировать" без даты — ничего не происходит
- [ ] "← К списку" — деталь закрылась
- [ ] Отчёты: кнопка "JSON" скачивает файл; кнопка "Рекомендации" → переход на экран рекомендаций
- [ ] Рекомендации: `parameter_suggestions` отображаются как read-only (заголовок "Справочные параметры")
- [ ] Рекомендации: кнопки "Принять / Отклонить / Ознакомлен" работают (статус меняется)
- [ ] Выйти: кнопка Выйти → редирект на Keycloak login

---

### UT-2 — Rule engine E2E · browser + API
*Verify M5-a output is visible in the web UI.*

**Pre-condition:** UT-1 прошёл. Паспорт с `target_p80_mm = 500` существует в БД.

- [ ] Запустить анализ через мобильное приложение (или через dev-seed)
- [ ] Открыть Отчёты → найти последний отчёт → открыть Рекомендации
- [ ] Текст рекомендации содержит "⚠ Синтетические данные"
- [ ] Если P80 > 550 мм: текст содержит "КРУПНЫЙ КЛАСС"
- [ ] Если `fines_percent > 15%`: текст содержит "ПЕРЕИЗМЕЛЬЧЕНИЕ"
- [ ] Блок "Справочные параметры" показывает `observed_p80_mm`, `target_p80_mm`, `deviation_pct`
- [ ] Статус рекомендации = "требует проверки" (не принято автоматически)

---

### UT-3 — Mobile smoke test · Android device / emulator
*Run after rebuilding the app. Matches M4 acceptance criteria.*

- [ ] Войти через PKCE (Keycloak login в браузере) → вернуться в приложение авторизованным
- [ ] Список карьеров загружается
- [ ] Создать паспорт → статус DRAFT
- [ ] Подать паспорт → SUBMITTED
- [ ] Запустить capture flow: выбрать device + calibration → идёт polling → переход на отчёт
- [ ] Отчёт: P10/P50/P80 показаны, mock badge "⚠ Синтетические данные" виден
- [ ] Кнопка Export → Android share sheet открылся

---

## BACKLOG

### BUG-HUNT-1 — Frontend error states & edge cases · `frontend/`
*Periodic. Run whenever ≥2 new frontend features land. No UI access needed — code review only.*

- [ ] Empty states: каждый список имеет fallback (нет данных / не вошли)
- [ ] Loading states: не мигают, нет двойного fetch
- [ ] Network error: fetch в `useEffect` не проглатывает ошибки молча (`.catch(console.error)` — минимум)
- [ ] `Promise.allSettled` usage: все блоки используют `allSettled` там, где 404/403 ожидаемы
- [ ] Типизация: `tsc --noEmit` чистый, нет `as unknown as X`
- [ ] `parameter_suggestions` — проверить что нет кода, записывающего значения обратно в паспорт
- [ ] Audit log: проверить что нет кнопки "удалить запись"

### BUG-HUNT-2 — Backend security & data integrity · `backend/`
*Periodic. Run whenever ≥2 новых endpoint-а добавлено. Read-only code review.*

- [ ] IDOR: каждый endpoint, принимающий UUID ресурса, проверяет принадлежность карьеру
- [ ] Все `/api/v1/` пути имеют `Depends(get_current_user)` или `require_quarry_role`
- [ ] Нет `text()` с f-string в SQLAlchemy запросах
- [ ] Нет `allow_origins=["*"]` в CORS конфигурации
- [ ] AuditLog: нет `DELETE` или `UPDATE` на таблице `audit_log`
- [ ] `Recommendation` creation: нет пути создания без `REQUIRES_HUMAN_REVIEW`
- [ ] MinIO keys: конструируются только server-side, не из user input напрямую
- [ ] Presigned URL expires: не больше 3600 секунд

### BUG-HUNT-3 — Worker pipeline integrity · `worker/`
*Periodic. Run после каждого изменения worker/.*

- [ ] `evaluate_fragmentation` — нет импортов SQLAlchemy/Celery/asyncio в `rules.py`
- [ ] `db_models.py` стабы в синхронизированы с `backend/app/db/models/` (ключевые поля)
- [ ] Провальный pipeline шаг → `AnalysisJob.status = "failed"`, нет частичного `AnalysisResult`
- [ ] `confidence_notes` аппенд, не перезапись (сохраняется mock-note)
- [ ] `parameter_suggestions` нигде не читается и не записывается в `BlastPassport`
- [ ] `asyncio.set_event_loop_policy` присутствует для Windows в Celery task

### M5-b — LLM explanation layer · `worker/` or `backend/`
*Depends on M5-a rules being stable. Adds human-readable text to structured suggestions.*

- [ ] Claude API call with structured output for `recommendation_text`
- [ ] `confidence_notes` auto-generated from model output
- [ ] Fallback to rule-text if LLM unavailable
- [ ] Safety: `requires_human_review` enforced, no auto-apply

### M5-c — Historical P80 trends · `backend/` + `frontend/` + `mobile/`
- [ ] `GET /api/v1/quarries/{id}/sections/{sid}/trend` — P80 over last N blasts per section
- [ ] Web dashboard: sparkline chart in section/passport context
- [ ] Mobile: sparkline widget on reports list screen

### WEB-3 — Admin panel + audit log · `frontend/`
*Low urgency — admin ops currently via direct API calls or dev-seed endpoint.*

- [ ] Wire Admin screen: real user list from `GET /api/v1/quarry-users`
- [ ] Audit log table: `GET /api/v1/audit-log` (paginated, admin only)
- [ ] Role assignment UI (admin only — calls `POST /api/v1/quarries/{id}/users`)

---

## BLOCKED (requires ZED 2 hardware)

### M2 — Real CV Stereo (≈8 weeks after hardware)
- [ ] OpenCV stereo calibration step (replace mock `StereoCalibrationStep`)
- [ ] Stereo rectification (replace mock)
- [ ] StereoSGBM depth estimation (replace mock)
- [ ] Open3D point cloud generation (replace mock)
- [ ] Calibration import from ZED SDK `.conf` file

### M3 — Segmentation + Particle Volumes (≈12 weeks, requires training data)
- [ ] YOLO-seg adapter (`SegmentationAdapter` interface)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle measurements
- [ ] Report PDF generation (WeasyPrint) — web download button already wired to export endpoint
- [ ] Ground truth validation (sieve analysis comparison)

---

## M6+ — Production & Scale

- [ ] ZED SDK direct USB integration (replace Camera2 placeholder)
- [ ] Multi-quarry SaaS deployment (tenant isolation, billing)
- [ ] PostGIS for quarry/section geospatial boundaries
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
- [ ] Replace worker `db_models.py` hand-sync with shared package import
- [ ] Keycloak user deactivation sync (revoked access not propagated on JWT refresh)
- [ ] Web: real-time job status via WebSocket (currently no live updates in web)
- [ ] Mobile: push notifications for completed analysis jobs
