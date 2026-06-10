# ZMetrics - STATUS

**Last updated:** 2026-06-10 (rev 11 — IGEV/ZED закоммичено; M3-PART: реальные particle_volumes + granulometry)
**Git HEAD:** см. `git log` (rev 10 закоммичен тремя коммитами + M3-PART этой сессией)

---

## TL;DR для следующей сессии

1. **M3-PART сделан (эта сессия): последний mock-участок реального контура закрыт.**
   `cv_particles.py` (`CVParticleVolumeStep`): SAM3-полигоны (координаты исходного
   кадра) → ректифицированное пространство через `cv2.undistortPoints(R=R1, P=P1)`
   (тот же `stereoRectify(alpha=0)`, что в rectification) → растеризация → медианная
   глубина по маске → метрические размеры. Юнит-агностичность по глубине:
   `unit_to_mm = baseline_mm / ‖T‖`. Размер = эквивалентный диаметр по площади
   проекции; объём = эллипсоид по осям minAreaRect (a×b×b). Фильтры: <64 px,
   depth coverage <0.3, вырожденные полигоны — всё в `n_skipped`.
   `cv_granulometry.py` (`CVGranulometryStep`): **объёмно**-взвешенный кумулятив
   (в моке был счётный), P10/P50/P80 интерполяцией по нему, RR-fit, честный
   confidence = mean_seg_conf × mean_depth_coverage × min(1, n/30); notes несут
   provenance (segmentation/depth backend/calibration_id). 0 камней → пустой
   результат с NULL P-значениями, **отчёт/рекомендация НЕ создаются** (гард в
   `_create_report_and_recommendation`); synthetic_fallback-маски → confidence ≤0.2
   + «⚠». Wiring: реальные шаги при `ENABLE_REAL_STEREO && ENABLE_SAM3`.
   Заголовок отчёта теперь честный: «real CV (SAM3 + stereo depth)» vs «⚠ Mock».
   Тесты: `worker/tests/test_cv_granulometry.py` (7 шт.).
   **Не проверено на железе** — нужен прогон `scripts/e2e_capture_smoke.py`
   с пересборкой образа воркера (`docker compose build worker`).
2. **E2E на реальном железе пройден (2026-06-10, до M3-PART):** ZED 2 (SN 21907252,
   2.2K SBS) → заводская калибровка → rectification → IGEV++ depth на RTX 5080 →
   2.74M точек → SAM3 (0 камней на столе — честно) → mock-грансостав. Прогон:
   `desktop\.venv\Scripts\python.exe scripts\e2e_capture_smoke.py --password changeme`.
   `DEPTH_BACKEND=igev` (+`ENABLE_REAL_STEREO=true`) включает IGEV++ вместо SGBM;
   веса `infra/models/igev/` (gitignore по `*.pth`), дефолт sceneflow.pth;
   инференс даунскейлится до `IGEV_MAX_INFERENCE_WIDTH=1536`.
3. **Калибровка ZED:** заводской conf качается по серийнику (`calib.stereolabs.com/?SN=…`),
   конвертация в `CalibrationCreate` — `zmetrics_desktop/capture/zed_calibration.py`
   (Rodrigues([RX,CV,RZ]), **T=[−Baseline,TY,TZ] мм** — конвенция zed-opencv-native).
   Глубина в **мм** (как T); метадата-ключ `median_depth_mm` (был мислейбл `_m`).
4. **Флаги НЕ в `infra/.env`** (файл закрыт для агента): в этой сессии передавались через
   process env. Добавить руками: `ENABLE_REAL_STEREO=true`, `ENABLE_SAM3=true`,
   `DEPTH_BACKEND=igev`. Иначе следующий `compose up` вернёт mock/SGBM.
5. **Docker Desktop чинился дважды:** крах на старте «file cannot be accessed by the
   system» = битые unix-сокеты; лечится `wsl -d docker-desktop -e rm -rf
   /mnt/host/c/Users/Nikita/AppData/Local/Docker/run` (+ `docker-secrets-engine`).
   Docker AI отключён. Данные WSL на **G:** (`wslDataFolder`), C: не забивается.
6. **Следующее:** реальные particle_volumes/granulometry из SAM3-масок × depth
   (последний mock-участок реального контура); съёмка реального развала; юзертесты
   UT-D1/UT-D2; PyInstaller (UT-D6).

---

## Tests (последний прогон 2026-06-10 вечер)

| Suite | Result |
|---|---|
| backend (`backend/tests`) | 78 passed (не перегонялись в этой сессии) |
| worker (`worker/tests`) | 39 passed (32 + 7 новых cv_particles/cv_granulometry; хостовый `worker\.venv` — досталлен sqlalchemy) |
| desktop (`desktop/tests`) | 121 passed (113 + 8 новых zed_calibration) |

---

## Runtime notes

- Docker Desktop на момент записи остановлен. Старт стека:
  `docker compose -f infra\docker-compose.yml up -d --remove-orphans`
  (`--remove-orphans` один раз — добьёт осиротевшие контейнеры `frontend`,
  `grafana`/`prometheus`/`celery-exporter` от старых экспериментов).
- GPU для SAM3 — отдельный оверлей: `... -f infra\docker-compose.gpu.yml up -d`
  плюс `ENABLE_SAM3=true`. Базовый стек стартует без GPU (mock-сегментация).
- **Работающий Keycloak ещё держит старых клиентов** `zmetrics-web`/`zmetrics-mobile`
  и `directAccessGrantsEnabled=false` у `zmetrics-desktop` — realm импортируется только
  при первом старте. Прибрать вручную в консоли (8080) или переимпортировать realm.
  Пока ROPC-смоук через `zmetrics-mobile` продолжает работать.
- ⚠ `infra/docker-compose.yml` всё ещё хардкодит `ENABLE_DEV_SEED: "true"` — для общих
  стендов поменять на `${ENABLE_DEV_SEED:-false}`.

---

## Layer status

| Layer | State |
|---|---|
| **backend** | M1 + SEC + ADMIN-USERS-1 (включён, проверен E2E) + bootstrap/capture фиксы |
| **worker** | SAM3 (CUDA) + M2-STEREO + IGEV++ depth + M5-a/M5-b + **M3-PART: реальные particle_volumes/granulometry (юнит-тесты ок, на железе не гонялись)**; mock-шагов в реальном контуре больше нет |
| **desktop** | Все экраны DESKTOP-1 готовы; + `capture/zed_calibration.py` (заводская калибровка ZED); юзертесты UT-D1..D5 не пройдены; PyInstaller не делался |
| **infra** | compose: IGEV env+volume; GPU-оверлей (SAM3+IGEV); `infra/models/igev/` веса; conf ZED SN21907252 в репо |

---

## Priority queue

| Pri | ID | Item | Notes |
|---|---|---|---|
| **P1** | — | E2E смоук M3-PART на железе | `docker compose build worker` + флаги + `scripts/e2e_capture_smoke.py`; на столе ждём «0 камней → нет отчёта» |
| **P1** | — | Съёмка реального развала ZED 2 + прогон IGEV+SAM3+M3-PART | смоук на столе прошёл (до M3-PART), нужны камни |
| **P2** | UT-D1 | Smoke десктопа: логин (OIDC/keyring), статус-бар, дашборд | чек-лист в roadmap (DESKTOP-1) |
| **P2** | UT-D2 | CRUD + workflow паспорта + ролевой гейтинг | после UT-D1 |
| **P2** | UT-D3 | Capture E2E через UI десктопа на ZED 2 | headless-вариант уже есть: `scripts/e2e_capture_smoke.py`; в UI кнопка «Подготовить тестовое устройство» создаёт заглушку — добавить путь «зарегистрировать ZED по серийнику» |
| **P2** | UT-D4/UT-2 | Отчёты + рекомендации (rule engine E2E через десктоп) | |
| **P2** | UT-D5 | Админка и роли (выдать/отозвать, AuditLog) | admin-фича уже включена и работает |
| **P3** | — | SAM3-метаданные в панели завершённого job + smoke на `rock-sample.png` без камеры | картинка теперь в `desktop/zmetrics_desktop/assets/` |
| **P3** | — | PyInstaller build + UT-D6 на чистой Windows | |
| ~~done~~ | DEPTH-2 | ~~IGEV-Stereo вместо SGBM~~ | сделано 2026-06-10, IGEV++ за `DEPTH_BACKEND=igev` |
| ~~done~~ | M3-PART | ~~Реальные particle_volumes + granulometry~~ | сделано 2026-06-11, требуется прогон на железе |

---

## Dev credentials

- Keycloak admin UI: `http://localhost:8080` → `admin` / см. `infra/.env`
- App login: `admin-user` / `changeme`
- Password-grant для API-смоука (пока realm не переимпортирован):
  `POST http://localhost:8080/realms/zmetrics/protocol/openid-connect/token`
  с `client_id=zmetrics-mobile`, `grant_type=password`, `username=admin-user`,
  `password=changeme`. После переимпорта realm — `client_id=zmetrics-desktop`.
- Dev seed: `POST /api/v1/admin/dev-seed` (нужен `ENABLE_DEV_SEED=true` + Bearer).
- Админ-фичи пользователей: `ENABLE_ADMIN_USER_MANAGEMENT=true` и
  `KC_CLIENT_ID=zmetrics-backend` в `infra/.env` (уже сделано на этой машине).

---

## Safety invariants

- `Recommendation` всегда создаётся со `status = requires_human_review`.
- Нет auto-approve / bulk-approve путей; переходы паспорта — явные действия человека.
- AuditLog append-only; пишется на статусы паспортов, ревизии, роли, доступы.
- Mock-выводы помечены `⚠ Синтетические данные`; LLM-текст — только пояснение,
  `parameter_suggestions` и статус рекомендации остаются от rule engine.
- Временные пароли возвращаются один раз, не сохраняются и не логируются.

---

## Active handoffs

| File | Task | Status |
|---|---|---|
| `2026-06-09-TASK-admin-users-2-frontend.md` | спека админ-экрана | реализовано в десктопе (`8c530d1`); спека — справочник по flows |
| остальные в `docs/handoffs/` | web/mobile-эпоха | исторический архив |
