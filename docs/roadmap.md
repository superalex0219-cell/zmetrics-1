# ZMetrics — Roadmap

Last sync: 2026-06-11 (вечер) | HEAD: см. git log (CAP-MULTI + AUTH-2 + EDIT-1)

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

### DEPTH-2 — IGEV++ neural stereo depth · `worker/` (`411ece0`, 2026-06-10)
- [x] Vendored IGEV++ (MIT) + `IGEVDepthStep` (`cv_depth_igev.py`), тот же контракт артефактов, что SGBM
- [x] `DEPTH_BACKEND=sgbm|igev` (default sgbm); веса `infra/models/igev/` (gitignore), compose mount, GPU overlay
- [x] Даунскейл инференса до `IGEV_MAX_INFERENCE_WIDTH=1536`, диспаритет рескейлится обратно
- [x] Проверен на RTX 5080: 2.2K кадр → 2.74M валидных точек, 100% покрытие
- [ ] *Follow-up (DEPTH-3):* left-right consistency → occlusion mask + честный confidence шага;
      валидация по эталонному объекту (~200мм маркер) SGBM vs IGEV

### M2 — Real CV stereo · `worker/` + `desktop/` (validated 2026-06-10 on ZED 2)
- [x] `cv_calibration` / `cv_rectification` / `cv_depth` (SGBM) / `cv_pointcloud` за `ENABLE_REAL_STEREO`
- [x] Заводская калибровка ZED по серийнику: `desktop/.../capture/zed_calibration.py` + кнопка
      «Зарегистрировать ZED» на экране съёмки (`2925d7d`); conf SN21907252 в репо
- [x] E2E на железе: `scripts/e2e_capture_smoke.py` (ZED 2 → rectify → depth → SAM3 → результат)

### M3-PART — Реальные particle volumes + granulometry · `worker/` (`0a4d5dc`, 2026-06-11)
- [x] `CVParticleVolumeStep`: SAM3-полигоны → ректифицированное пространство (`undistortPoints(R1,P1)`),
      медианная глубина по маске, метрические размеры; юнит-агностичность `baseline_mm/‖T‖`
- [x] `CVGranulometryStep`: объёмно-взвешенный кумулятив, P10/P50/P80, RR-fit, вычисляемый confidence,
      provenance в notes (segmentation/depth/calibration_id)
- [x] SAFETY: 0 камней → NULL-результат, отчёт/рекомендация не создаются; заголовок отчёта различает real CV/mock
- [x] Отказ от заглушечной калибровки с понятной ошибкой; reshape плоских матриц (`0d9388f`)
- [ ] Прогон на железе (пересборка worker сделана; нужен снимок реального развала)

### CAPTURE-UX — Удобная съёмка · `desktop/` (`2925d7d` → `0d9388f`, 2026-06-11)
- [x] Авто-старт превью, авто-выбор ZED; чек-лист готовности вместо молча серой кнопки
- [x] «Зарегистрировать ZED»: заводская калибровка по серийнику прямо из UI (409 → reuse устройства)
- [x] Предупреждение при съёмке стерео с TEST-устройством
- [x] Фиксы: non-contiguous буфер превью; stale карта доступов (`/me/access` ретраи + refresh после
      создания карьера/смены ролей); grant поверх роли = смена роли (upsert, без 500)

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

### CAP-MULTI — Несколько фотографий к одному взрыву · `backend/` + `worker/` + `desktop/` (2026-06-11)
- [x] Backend: `AnalysisJob.frame_index` (+миграция `75bb00d854b1`); `POST /captures/{id}/jobs`
      принимает `frame_index`, валидирует наличие left_frame пары (409 иначе)
- [x] Backend: `GET .../blast-event/capture-summary` — сессии взрыва с агрегатами
      (пары кадров, статус последнего джоба по паре, имя снявшего, ✓/✗ по джобам)
- [x] Worker: джоб обрабатывает СВОЮ пару кадров (`frame_index` в `PipelineContext.config`);
      артефакты пайплайна пары N>0 живут в `sessions/{id}/pipeline/f{N:04d}/` —
      пары не затирают друг друга (helper `pipeline_prefix`, все 15 шагов переведены)
- [x] Desktop: серия в одну сессию — «Снять ещё (в серию)», галерея превью с удалением,
      «Загрузить с диска…» (multi-select, SBS-автодетект), «Отправить серию (N)»
- [x] Desktop: отдельный джоб на каждую пару; сводный поллинг «серия: завершено k/n»,
      P80 по кадрам в панели результата; блок «Снимки взрыва» (кто/когда/кадры/статусы)
- [x] Оффлайн: серия уходит в SyncManager одной составной операцией (`frames: [...]`);
      легаси-элементы очереди (плоский payload) реплеятся
- [ ] *Остаток:* миниатюры в списке «Снимки взрыва» (сейчас текстовые строки; тянуть
      превью через presigned URL — отдельная мелкая задача)

### AUTH-2 — Токены на рабочую смену · `infra/` + `desktop/` (2026-06-11)
- [x] Логин формой в приложении (direct access grant) — было ранее
- [x] Realm: `accessTokenLifespan=900`, `ssoSessionIdleTimeout=43200` (12 ч),
      `ssoSessionMaxLifespan=46800` — и в realm-export.json, и применено kcadm'ом к живому realm
- [x] Desktop: проактивный refresh по таймеру (раз в минуту, за 3 мин до истечения access);
      сроки из `expires_in`/`refresh_expires_in` хранятся в keyring
- [x] Desktop: refresh различает `expired` (диалог «Сессия истекла» + форма логина)
      и `offline` (молча ретраит позже); 5xx Keycloak = offline, не разлогин
- [x] Тулбар: «Авторизован до HH:MM» (конец сессии = срок refresh-токена)

### EDIT-1 — Редактирование сущностей · `backend/` + `desktop/` (2026-06-11)
- [x] Backend PATCH + AuditLog (`action=entity_updated`, old/new только изменённые поля):
      quarry (admin), site_section (blaster), device (model/firmware/notes; серийник
      нередактируем), calibration (только is_active), blast_event (blaster, с passport_id
      в аудите), passport — PATCH только в DRAFT (409 иначе; дальше revise-flow)
- [x] Desktop: «Изменить выбранный…» на Карьерах (admin) и Участках (blaster);
      «Изменить черновик…» и «Изменить взрыв…» в деталях паспорта (blaster);
      общий `EditFormDialog` шлёт только изменённые поля
- [x] UI-запреты соблюдены: у не-DRAFT паспорта кнопки правки нет (только ревизия),
      результаты анализа/аудит/рекомендации форм правки не имеют
- [ ] *Остаток:* формы правки device/calibration появятся вместе с экраном «Устройства»
      (CAM-CUSTOM) — API-методы в `ZMetricsApi` уже готовы

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

### UT-7 — CAP-MULTI + AUTH-2 + EDIT-1 · desktop (2026-06-11, ожидает прогона)
*Проверка трёх фич этой сессии. Стек уже пересобран и запущен; логин `admin-user`/`changeme`.*

**A. AUTH-2 — сессия на смену**
- [ ] Запустить `desktop`: `python -m zmetrics_desktop` → Войти формой (без браузера)
- [ ] В тулбаре написано «Авторизован до HH:MM» (время ≈ +12 часов от логина)
- [ ] Подождать ≥1 минуту — приложение живёт, ошибок нет (тихий проактивный refresh)
- [ ] Остановить только Keycloak (`docker compose -f infra\docker-compose.yml stop keycloak`),
      подождать 2 минуты → разлогина НЕТ (offline ≠ expired); запустить Keycloak обратно
- [ ] (Опционально, разрушающе) Удалить refresh-токен из Windows Credential Manager
      (запись `zmetrics-desktop`/`refresh_token`) → в течение ~16 мин появится диалог
      «Сессия истекла» и форма логина

**B. CAP-MULTI — серия фото к взрыву**
- [ ] Экран «Съёмка»: выбрать карьер и паспорт со взрывом (или зафиксировать взрыв)
- [ ] Нажать «Снять ещё (в серию)» 2–3 раза → в галерее «Серия снимков» появились
      миниатюры `0: …`, `1: …`; кнопка стала «Отправить серию на анализ (N)»
- [ ] «Удалить выбранный» убирает кадр, нумерация пересчитывается
- [ ] «Загрузить с диска…» — выбрать JPEG/PNG (широкий файл должен определиться как стерео)
- [ ] Отправить серию → статус «серия: завершено k/n»; по завершении в «Примечаниях»
      P80 по каждому кадру
- [ ] Блок «Снимки взрыва» внизу: строка сессии с датой, вашим именем, числом кадров
      и статусами по кадрам («кадр 0: моно · завершён»)
- [ ] Оффлайн: остановить backend → снять серию → «⚠ Оффлайн — съёмка в очереди»;
      запустить backend → в течение 30 с очередь слита, в «Снимках взрыва» новая сессия,
      дублей нет
- [ ] Отчёты: на каждую пару серии появился свой отчёт

**C. EDIT-1 — редактирование с аудитом**
- [ ] Карьеры: выбрать строку → «Изменить выбранный…» (виден только админу) →
      поменять «Расположение» → таблица обновилась
- [ ] Участки: «Изменить выбранный…» (от blaster) → поменять № блока → обновилось
- [ ] Паспорта: у DRAFT-паспорта есть «Изменить черновик…»; поменять целевой P80 →
      деталь обновилась. У SUBMITTED/APPROVED/ACTIVE кнопки правки НЕТ
- [ ] Паспорт со взрывом: «Изменить взрыв…» → поправить фактический заряд → обновилось
- [ ] Под ролью `user` ни одна кнопка «Изменить…» не видна
- [ ] (API) `GET /api/v1/admin/audit-logs?entity_type=quarry&...` содержит
      `entity_updated` с old/new только изменённых полей

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
- [x] Screens: админка (ADMIN-USERS-2 спека → desktop): пользователи, роли по карьерам,
      временный пароль один раз (copy + hide, не персистится), 403 → «Недостаточно
      прав» — 112 tests green
- [ ] **UT-D5 — админка и роли:** выдать/отозвать доступ к карьеру, сменить роль;
      отозванный пользователь теряет карьер из списка; AuditLog пишется
- [ ] SAM3 artifact metadata в панели завершённого job + `rock-sample.png` smoke без камеры
      *(перенесено из WEB-ANALYSIS-2)*
- [x] Remove `frontend/` + `mobile/`; drop `frontend` service from compose; prune
      `zmetrics-web`/`zmetrics-mobile` Keycloak clients. Dev ROPC token flow moved to
      `zmetrics-desktop` (`directAccessGrantsEnabled=true`); `rock-sample.png` saved to
      `desktop/zmetrics_desktop/assets/`. ⚠ Running Keycloak still holds the old clients
      until realm re-import (or delete them once via the admin console)
- [ ] PyInstaller build (+ опц. инсталлятор); backend URL на первом запуске
- [ ] **UT-D6 — сборка:** поставить .exe на чистую Windows (без Python/venv),
      подключиться к backend, пройти логин и один capture-цикл
- [ ] Docs: STATUS/roadmap reconcile + handoff

*Позже, при наличии железа: UT-D7 — ZED 2 по USB (SBS-режимы, left/right split) и
`ENABLE_REAL_STEREO=true` — уже учтён в M2 (BLOCKED) ниже.*

---

## PRODUCT BACKLOG — запрос владельца продукта 2026-06-11

*CAP-MULTI, AUTH-2 и EDIT-1 выполнены 2026-06-11 (см. DONE). Остаток порядка:
REPORT-X → CAM-CUSTOM → UI-2; M5-d — параллельная исследовательская ветка;
STORE-1 закрывается по ходу REPORT-X.*

### REPORT-X — Отчёты в PDF / DOCX / XLSX / CSV · `worker/` + `backend/` + `desktop/`
*Сейчас: JSON-экспорт из десктопа. Состав отчёта: сегментация (оверлей масок),
паспорт БВР, рекомендации, карта глубины (превью), исходные/обработанные снимки,
параметры карьера и взрыва.*

- [ ] Worker: шаг рендера отчёта (HTML-шаблон → PDF через WeasyPrint; DOCX через
      python-docx; XLSX через openpyxl — грансостав таблицей; CSV — size_distribution)
- [ ] Визуальные артефакты для отчёта: маски поверх кадра (PNG), колоризованная карта
      глубины (PNG) — складывать в MinIO рядом с result.json
- [ ] Backend: `GET /reports/{id}/export?format=pdf|docx|xlsx|csv|json` (стрим из MinIO,
      генерация лениво при первом запросе)
- [ ] Desktop: кнопки экспорта на экране отчёта; SAFETY: метод анализа (real CV / mock)
      и статус рекомендации «требует проверки» — на видном месте каждого формата
- [ ] В отчёт: блок паспорта БВР (параметры бурения/заряда), блок рекомендации
      (текст + parameter_suggestions read-only)

### CAM-CUSTOM — Нестандартные стереокамеры · `desktop/` + `backend/`
*Свободная конфигурация: своя стереокамера (две UVC или одна SBS), ручной ввод/импорт
калибровки, редактирование конфигурации камеры.*

- [ ] Desktop: экран «Устройства»: список устройств/калибровок, создание устройства
      с произвольной моделью, редактирование (EDIT-1)
- [ ] Форма калибровки: ручной ввод fx/fy/cx/cy, дисторсий, R/T, baseline + валидация
      правдоподобия (fx>50px и т.п. — worker уже отклоняет заглушки)
- [ ] Импорт калибровки из файла: ZED .conf (есть), OpenCV .yml/.json (добавить)
- [ ] Настройка SBS-раскладки: side-by-side / two-devices / top-bottom; порог аспекта
      и индексы устройств в конфиге камеры
- [ ] (Опционально) мастер калибровки шахматной доской через OpenCV — отдельная веха,
      если ручного ввода/импорта не хватит

### M5-d — ML-модель рекомендаций по паспорту БВР · `worker/` + `docs/`
*Сейчас: rule engine (M5-a) + LLM-пояснения (M5-b). Цель: модель, связывающая параметры
паспорта (burden/spacing/заряд/сетка) с прогнозом грансостава и рекомендациями.
SAFETY: модель только предлагает; статус всегда requires_human_review; параметры
никогда не применяются автоматически.*

- [ ] Структура данных для обучения: датасет-схема «паспорт БВР (фичи) → измеренный
      грансостав (P10/P50/P80, RR)» + экспорт исторических пар из БД (JSON/parquet)
- [ ] Генератор синтетических обучающих данных для демо: Kuz-Ram / SveDeFo-based
      симулятор (физически правдоподобные пары паспорт→фрагментация, с шумом)
- [ ] Бейзлайн-модель: предсказание P80 по параметрам паспорта (gradient boosting /
      регрессия; sklearn), метрики качества, сериализация как `ModelVersion`
- [ ] Инференс в worker: рекомендация = rule engine + прогноз модели («при burden −0.3м
      ожидаемый P80 ↓ на X%» — как справка), confidence + пометка «модель, демо-данные»
- [ ] Вывод в UI (экран рекомендаций) и в REPORT-X отчётах

### UI-2 — Современный интерфейс десктопа · `desktop/`
- [ ] Единая тема (палитра, типографика, отступы) через QSS; тёмная/светлая
- [ ] Иконки (Material/Lucide), консистентные кнопки/формы/таблицы
- [ ] Карточная вёрстка дашборда, пустые состояния с подсказками-действиями
- [ ] Тосты вместо красных строк ошибок; индикаторы загрузки
- [ ] Ревизия навигации: группировка экранов, хлебные крошки в заголовке

### STORE-1 — MinIO: полнота хранения · `backend/` + `worker/` *(почти готово)*
*Уже в MinIO: исходные кадры (`zmetrics-frames`), обработанные артефакты — depth/disparity/
point cloud/masks/result.json (`zmetrics-artifacts`). Остаток:*

- [ ] Файлы отчётов (PDF/DOCX/XLSX из REPORT-X) → `zmetrics-artifacts` (`reports/`)
- [ ] Рендеры для отчётов (mask overlay, цветная depth map) → артефакты сессии
- [ ] «Дополнительные файлы проекта»: `Attachment` к карьеру/паспорту (произвольный файл
      + описание), bucket-префикс `attachments/`, валидация magic bytes
- [ ] Ретеншн-политика/очистка осиротевших объектов (отложено — после REPORT-X)

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

## BLOCKED (requires field data)

### M3 — Segmentation quality (remainder; requires training data)
*Particle volumes + granulometry реализованы (M3-PART, см. DONE); остаток — качество
сегментации и наземная валидация.*

- [x] SAM3 segmentation step — text-prompted instance segmentation (`Sam3SegmentationStep`)
- [x] Particle mask → 3D volume projection *(M3-PART)*
- [x] Granulometry from real particle measurements *(M3-PART)*
- [ ] YOLO-seg fine-tuning adapter (alternative to SAM3 for embedded/edge deployment)
- [ ] Training data collection and labeling pipeline
- [ ] Ground truth validation (sieve analysis comparison)
- [ ] Report PDF generation — поглощено REPORT-X ниже

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
