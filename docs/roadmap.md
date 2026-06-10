# ZMetrics — Roadmap

Last sync: 2026-06-10 | HEAD: `4aa677b`

> **⚠ Архитектурный пивот 2026-06-10:** React-веб (`frontend/`) и Flutter-mobile (`mobile/`)
> упраздняются в пользу единого десктоп-клиента **Python + PySide6** (`desktop/`, Windows-first).
> CV остаётся на сервере; backend/worker не меняются. Завершённые WEB-*/M4-вехи в DONE —
> исторический архив. См. DESKTOP-1 ниже.

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
- [x] Keycloak OIDC browser redirect (login-required + PKCE, `zmetrics-web` Keycloak client)
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

### M5-b — LLM explanation layer · `worker/` (working tree)
- [x] `app/llm.py`: `enhance_recommendation_text()` — Anthropic API turns rule facts into advisory Russian prose
- [x] Gated behind `ENABLE_LLM_RECOMMENDATIONS` + `ANTHROPIC_API_KEY`; default off
- [x] Lazy SDK import — `import app.llm` works even without `anthropic` installed (verified in running container)
- [x] Fallback-safe: disabled / no key / missing SDK / API error / empty response → deterministic M5-a rule text; no exception escapes
- [x] `MOCK_BADGE` + `REVIEW_FOOTER` enforced in code via `_wrap_with_safety` (single source = `app.rules`)
- [x] Safety: `parameter_suggestions` + `confidence_notes` stay rule-engine-driven; `status=REQUIRES_HUMAN_REVIEW` untouched; prompt forbids numeric BVR params; `max_retries=0`
- [x] 9 unit tests (Anthropic client fully mocked); worker suite 23 → 32 green
- [ ] *Activate:* rebuild worker image with `anthropic`, set flag + key — feature dormant until then

### SAM3 — Real segmentation step · `worker/` (`2079e0b` → `faac5a6`)
- [x] `Sam3SegmentationStep` replaces `MockSegmentationStep` in the pipeline
- [x] Model: `bodhicitta/sam3` (SAM3 Video, `model.safetensors` 3.28 GB) — weights at `models/sam3/`
- [x] Inference via `transformers` `Sam3Model` + `Sam3Processor`; runs on CUDA if available
- [x] Output format (masks.json: `bbox_normalized`, `polygon_normalized`, `confidence`) identical to mock
- [x] Idempotency: skips if `masks.json` already in MinIO
- [x] Graceful fallback to synthetic masks when no `left_frame` artifact found (no ZED 2 hardware)
- [x] Thread-safe singleton: model loaded once per worker process
- [x] GPU deploy section in `docker-compose.yml`; SAM3 volume mount `models/sam3:/models/sam3:ro`
- [x] `infra/.env.example` updated with `SAM3_WEIGHTS_DIR`, `SAM3_MODEL_PATH`, `SAM3_TEXT_PROMPT`
- [x] Worker image rebuilt and running with CUDA PyTorch cu128 (`torch 2.11.0+cu128`, `torchvision 0.26.0+cu128`)
- [x] Local GPU smoke: `rock-sample.png` -> 77 SAM3 masks
- [x] Container GPU smoke: `rock-sample.png` -> 77 SAM3 masks, CUDA, ~5.9s

### WEB-2 — Passport workflow in web · `frontend/` (`849e1f9`)
- [x] Passport detail panel: all fields, colored status badge, click-to-open from list
- [x] State transitions: DRAFT→SUBMITTED→APPROVED→ACTIVE→COMPLETED (one button per status, one POST each)
- [x] Blast event registration form (APPROVED/ACTIVE only; `blast_datetime` required)
- [x] AuditLog display (hidden silently on 403; hidden when empty)
- [x] `Promise.allSettled` — 404 blast event and 403 audit log are silent, never shown as errors
- [x] `onUpdated` prop wired: status changes reflected immediately in passport list
- [x] `tsc --noEmit` — 0 errors

### WEB-UI-1 — Bootstrap + responsive redesign · `frontend/` + `backend/` (working tree)
- [x] Empty DB bootstrap: first authenticated user can create the first quarry
- [x] Quarry creator receives admin access automatically
- [x] Quarry creation fixed for users with multiple admin accesses
- [x] Web UI can create quarries and site sections without dev-seed
- [x] Responsive app shell: fixed topbar, desktop sidebar, mobile drawer, breadcrumbs
- [x] UI feedback: toast notifications, loading banner, clearer empty/error states
- [x] Dashboard rebuilt as operational workflow screen with quick actions and latest reports
- [x] Quarries/Sites rebuilt as management layouts
- [x] Reports search/sort added
- [x] Docker frontend build passes; nginx serves latest redesigned assets

### WEB-ANALYSIS-1 — Browser capture + analysis launcher · `frontend/` + `worker/` + `backend/` (working tree)
- [x] `Анализы` page: live `getUserMedia` preview, photo gallery, passport selector (APPROVED/ACTIVE only)
- [x] ZED 2 SBS auto-detect (aspect ratio > 1.8 → split left/right at width/2)
- [x] Capture → upload `left_frame`/`right_frame` artifacts → create capture session → enqueue job → poll → show P80
- [x] M2-STEREO: real OpenCV `StereoSGBM` pipeline (`cv_calibration`/`rectification`/`depth`/`pointcloud`), `ENABLE_REAL_STEREO` flag
- [x] WORKER-FIX-1: `Artifact.storage_bucket`/`storage_key`, `CaptureSession.calibration_id`/`device_id`, `Calibration` stub
- [x] E2E live-test fixes (rev 6):
  - [x] Device/calibration self-heal inside `handleLaunch` (auto-creates default ZED 2 if none) — no separate setup step
  - [x] `POST /devices` returns 409 (not 500) on duplicate serial_number
  - [x] **Fixed 422 on `POST /captures/{id}/jobs`** — removed redundant required `capture_session_id` from `AnalysisJobCreate` body (it comes from the URL path); body now optional
- [ ] Show SAM3 artifact metadata (`masks.json` source, mask count, confidence) in completed-job panel — *deferred*
- [ ] Bundled `rock-sample.png` smoke option (no camera) — *deferred*

---

## QA & USER TESTING

User testing is done by the product owner in the desktop client (ранее — browser UI).
Bug hunts are periodic code-review tasks run by an executor agent (no UI needed).

---

### UT-1 — Web UI smoke test · browser @ http://localhost:5173 (`b29b725`) ✅
*Completed 2026-06-08. 3 bugs found and fixed during test.*

- [x] Войти через Keycloak → имя пользователя появилось в топбаре
- [x] Dashboard: карточки карьеров/участков/отчётов показывают числа (не "—")
- [x] Карьеры: карточки с названиями и локацией
- [x] Участки: выбор карьера → список участков обновляется
- [x] Паспорта — список: строки кликабельны; выбранная строка подсвечена
- [x] Паспорта — деталь: поля заполнены (статус, ревизия, скважины, цель P80)
- [x] Паспорта — переход DRAFT → SUBMITTED: нажать "Подать на проверку" → статус обновился
- [x] Паспорта — переход SUBMITTED → APPROVED: кнопка "Утвердить" → APPROVED
- [x] Паспорта — APPROVED: видна секция "Зарегистрировать взрыв"
- [x] Взрыв: заполнить дату → "Зарегистрировать" → форма скрылась, данные взрыва показаны
- [x] Взрыв: кнопка "Зарегистрировать" без даты — ничего не происходит
- [x] "← К списку" — деталь закрылась
- [x] Отчёты: кнопка "JSON" скачивает файл; кнопка "Рекомендации" → переход
- [x] Рекомендации: `parameter_suggestions` отображаются как read-only
- [x] Рекомендации: кнопки "Принять / Отклонить / Ознакомлен" работают
- [x] Выйти: кнопка Выйти → редирект на Keycloak login

---

### UT-2 — Rule engine E2E · desktop + API
*Verify M5-a output is visible in the client UI. Blocked until DESKTOP-1 screens (reports/recommendations) exist.*

**Pre-condition:** Паспорт с `target_p80_mm = 500` существует в БД. For real SAM3 verification, trigger an actual analysis job via API/desktop; `dev-seed` only proves seeded report/recommendation UI.

- [ ] Запустить анализ через десктоп-клиент (или через dev-seed/API)
- [ ] Открыть Отчёты → найти последний отчёт → открыть Рекомендации
- [ ] Текст рекомендации содержит "⚠ Синтетические данные"
- [ ] Если P80 > 550 мм: текст содержит "КРУПНЫЙ КЛАСС"
- [ ] Если `fines_percent > 15%`: текст содержит "ПЕРЕИЗМЕЛЬЧЕНИЕ"
- [ ] Блок "Справочные параметры" показывает `observed_p80_mm`, `target_p80_mm`, `deviation_pct`
- [ ] Статус рекомендации = "требует проверки" (не принято автоматически)

---

## IN PROGRESS

### DESKTOP-1 — Python/PySide6 desktop client · `desktop/` (working tree)
*Pivot 2026-06-10: single client replaces React web + Flutter mobile. Plan:
`C:\Users\Nikita\.claude\plans\quizzical-spinning-backus.md`.*

- [x] Repo cleanup (`.tools/`, `artifacts/`, junk dirs) + `.gitignore`
- [x] `.claude` rules rewritten (merged duplicates, `desktop.md`, mobile rules removed)
- [x] Scaffold: pyproject, config (pydantic-settings), httpx ApiClient, sqlite SyncManager
      (idempotency_key, retry ×5), SBS-split (`capture/stereo.py`), nav shell — 10 tests green
- [x] OIDC PKCE loopback auth: ephemeral-port callback, system browser, state check,
      keyring token store, 401→refresh→retry; Keycloak client `zmetrics-desktop` added
      *(код готов; pytest прогон заблокирован недоступностью шелла)*
- [x] Capture: UVC device enumeration (pygrabber/MSMF) + `cv2.VideoCapture` full-SBS
      (`capture/camera.py`: ZED2 SBS-режимы, инжектируемый источник, 12 тестов)
      *(код готов; остаётся E2E на железе с `ENABLE_REAL_STEREO=true`)*
- [x] Offline queue wired to ApiClient: `SyncProcessor` (реестр хендлеров по `kind`,
      ApiError → попытка ×5, обрыв сети → стоп без попытки) + статус-бар с QTimer 30s
- [x] Dashboard screen: селектор карьера, карточки (карьеры/участки/отчёты/P80),
      гистограмма фракций (QPainter), последние отчёты с mock-бейджем; DTO-слой +
      типизированный `ZMetricsApi` (зеркало api.ts) — 57 tests green

**Юзертесты (UT-D\*):** Claude пишет в чат пошаговые действия → Никита выполняет на
живом приложении и отписывается, где баги. Чекпоинты стоят после блоков, где ручная
проверка реально нужна (auth/UI-поведение/железо — то, что юнит-тесты не ловят).

- [ ] **UT-D1 — smoke того, что уже есть:** запуск `python -m zmetrics_desktop`,
      OIDC-логин через браузер (+ повторный запуск без логина — токен из keyring),
      выход, статус-бар Онлайн/Оффлайн (стоп backend → ⚠ Оффлайн), дашборд на
      dev-seed данных (карточки, гистограмма, mock-бейдж)
- [x] Screens: карьеры + участки (list/create, общий выбор карьера через AppState,
      403 сервера показывается в форме) — 70 tests green
- [x] Screens: паспорта (list/detail/create, переходы статусов кнопками с
      подтверждением, взрыв); ролевой гейтинг кнопок по `/access`
      (`user<surveyor<blaster<admin`, fail closed) — 81 tests green
- [ ] **UT-D2 — CRUD и workflow паспорта:** создать карьер → участок → паспорт →
      Submit → Approve → Activate → взрыв; проверить, что под ролью `user` кнопки
      записи скрыты/задизейблены, а API всё равно отдаёт 403 при прямом вызове
- [x] Screens: съёмка + анализ (превью камеры, capture → upload → job polling → P80);
      оффлайн: кадры на диск + составной `capture_upload` в очереди SyncManager;
      кнопка-хелпер «тестовое устройство» (веб-камера + калибровка-заглушка) — 95 tests
- [ ] **UT-D3 — capture E2E на веб-камере ноутбука (без ZED, без GPU):** снять кадр →
      моно-режим (только left_frame) → mock-пайплайн (`ENABLE_SAM3=false`) → P80 в UI;
      оффлайн-сценарий: стоп backend → снять кадр → очередь в статус-баре → старт
      backend → автослив ≤30 c, без дублей
- [x] Screens: отчёты (детали анализа + гистограмма, JSON export с blaster+, крупный
      mock badge) + рекомендации (read-only suggestions, Принять/Отклонить/Рассмотрена
      только кликом с подтверждением) — 105 tests green
- [ ] **UT-D4 — отчёты и рекомендации** *(совмещён с UT-2 ниже — выполнить его
      чек-лист через десктоп)*: бейдж «⚠ Синтетические данные», экспорт JSON,
      suggestions нередактируемы, статус меняется только кнопками
- [ ] Screens: админка (ADMIN-USERS-2 спека → desktop)
- [ ] **UT-D5 — админка и роли:** выдать/отозвать доступ к карьеру, сменить роль;
      отозванный пользователь теряет карьер из списка; AuditLog пишется
- [ ] SAM3 artifact metadata в панели завершённого job + `rock-sample.png` smoke без камеры
      *(перенесено из WEB-ANALYSIS-2)*
- [ ] Remove `frontend/` + `mobile/`; drop `frontend` service from compose; prune
      `zmetrics-web`/`zmetrics-mobile` Keycloak clients
- [ ] PyInstaller build (+ опц. инсталлятор); backend URL на первом запуске
- [ ] **UT-D6 — сборка:** поставить .exe на чистую Windows (без Python/venv),
      подключиться к backend, пройти логин и один capture-цикл
- [ ] Docs: STATUS/roadmap reconcile + handoff

*Позже, при наличии железа: UT-D7 — ZED 2 по USB (SBS-режимы, left/right split) и
`ENABLE_REAL_STEREO=true` — уже учтён в M2 (BLOCKED) ниже.*

---

## BACKLOG

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

### DEPTH-2 — IGEV-Stereo depth backend · `worker/`
*Decided 2026-06-10. Replace SGBM disparity with a learned stereo network for metric accuracy.
Depth error grows as `z²·Δd/(f·B)`: with ZED 2 (B=120mm, HD720) 1px disparity error ≈ 1.2m
depth error at 10m — subpixel quality of disparity directly drives P10/P50/P80 accuracy.
Do AFTER desktop E2E works with SGBM (pipe first, then quality).*

- [ ] `worker/app/pipeline/igev_depth.py` — `PipelineStep`, same artifact contract as
      `cv_depth.py` (reads `rectified_left/right.jpg` + `Q_matrix.json`; writes
      `depth_map.npy` + `disparity.npy`); only disparity computation changes (SGBM → IGEV inference)
- [ ] Backend selection via env `DEPTH_BACKEND=sgbm|igev` (default `sgbm`); SGBM stays as fallback/baseline
- [ ] Weights mounted `models/igev:/models/igev:ro` (same pattern as SAM3); verify repo license (MIT expected)
- [ ] Register as `ModelVersion`; step metadata must include model version (real-CV labeling rule)
- [ ] Confidence: left-right consistency check → occlusion mask + `confidence_score`
      (IGEV has no native uncertainty; rules require confidence fields)
- [ ] Inference at rectified resolution (≤720p is enough: max disparity ~28px at 3–15m range)
- [ ] Validation protocol: scene with known-size reference object (~200mm marker),
      compare SGBM vs IGEV measured sizes; record results in `StepResult.metadata`
- [ ] Fallback alternative if IGEV underperforms on quarry scenes: RAFT-Stereo (MIT)

### M5-c — Historical P80 trends · `backend/` + `desktop/`
- [ ] `GET /api/v1/quarries/{id}/sections/{sid}/trend` — P80 over last N blasts per section
- [ ] Desktop dashboard: sparkline chart in section/passport context

### ADMIN-USERS — Admin user management (Keycloak Admin API) · `backend/` + `infra/` + `desktop/`
*User-requested 2026-06-09. Specced — supersedes the "user list / role assignment" parts of WEB-3.*

- [x] **ADMIN-USERS-1** (backend+infra, working tree) → `docs/handoffs/2026-06-09-TASK-admin-users-1-backend.md`
  - [x] `services/keycloak_admin.py` — service-account token (cached) + user create/update/reset-password
  - [x] `POST /admin/users`, `POST /admin/users/{id}/reset-password`, `GET /admin/users/{id}/access`; KC sync on PATCH/DELETE
  - [x] Realm: `zmetrics-backend` service account granted `realm-management` roles; `KC_CLIENT_SECRET` wired
  - [x] Safety: admin-gated, temp-pw once / never stored or logged, no `keycloak_sub` leakage, AuditLog, savepoint orphan-rollback
  - [x] 78 backend tests (executor-local) + curator code review. ⚠ Activate: rebuild backend + fix `.env` (see STATUS Deploy notes)
- [ ] **ADMIN-USERS-2** (UI) — реализуется как экран «Администрирование» в DESKTOP-1;
      функциональная спека (поля, flows, ошибки) остаётся актуальной:
      `docs/handoffs/2026-06-09-TASK-admin-users-2-frontend.md`
  - [ ] User list, create, edit (ФИО/email/активность), reset-password, per-quarry roles

### ADMIN-AUDIT — Audit-log viewer · `desktop/` *(ex-WEB-3)*
*Remainder after ADMIN-USERS. Low urgency.*

- [ ] Audit log table: `GET /api/v1/admin/audit-logs` (paginated, admin only)

---

## BLOCKED (requires ZED 2 hardware)

### M2 — Real CV Stereo — implementation done, validation blocked
*Код шагов готов (M2-STEREO, см. DONE): `cv_calibration` / `cv_rectification` /
`cv_depth` (SGBM) / `cv_pointcloud`, за флагом `ENABLE_REAL_STEREO`. Блокирована
только проверка на реальной камере.*

- [x] OpenCV stereo calibration step (`cv_calibration.py`)
- [x] Stereo rectification (`cv_rectification.py`)
- [x] StereoSGBM depth estimation (`cv_depth.py`)
- [x] Open3D point cloud generation (`cv_pointcloud.py`)
- [ ] Calibration import from ZED SDK `.conf` file → записать в `Calibration` по серийнику
- [ ] E2E validation on real ZED 2 captures (через DESKTOP-1 capture)

### M3 — Segmentation + Particle Volumes (≈12 weeks, requires training data)
- [x] SAM3 segmentation step — text-prompted instance segmentation (`Sam3SegmentationStep`)
- [ ] YOLO-seg fine-tuning adapter (alternative to SAM3 for embedded/edge deployment)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle measurements
- [ ] Report PDF generation (WeasyPrint) — export endpoint уже есть; кнопка скачивания → desktop
- [ ] Ground truth validation (sieve analysis comparison)

---

## M6+ — Production & Scale

- [ ] ZED SDK (`pyzed`) on the capture PC — optional local neural depth / quality preview
      (десктоп сейчас работает с ZED как UVC; SDK не требуется, пока CV на сервере)
- [ ] Multi-quarry SaaS deployment (tenant isolation, billing)
- [ ] PostGIS for quarry/section geospatial boundaries
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
- [ ] Replace worker `db_models.py` hand-sync with shared package import
- [ ] Keycloak user deactivation sync (revoked access not propagated on JWT refresh)
- [ ] Desktop: real-time job status via WebSocket (сейчас — поллинг)
- [ ] Android companion app (просмотр отчётов / съёмка камерой телефона — НЕ ZED-захват;
      см. обоснование пивота)
