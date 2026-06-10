# ZMetrics - STATUS

**Last updated:** 2026-06-11 (rev 13 — CAP-MULTI + AUTH-2 + EDIT-1 реализованы; стек пересобран и работает на новом коде)
**Git HEAD:** см. git log (коммит сессии rev 13)

---

## TL;DR для следующей сессии

0. **Сессия 2026-06-11, часть 3 — закрыты три задачи продуктового бэклога:**
   - **CAP-MULTI** (серия фото к взрыву): `AnalysisJob.frame_index` + миграция
     `75bb00d854b1` (применена); job анализирует свою пару, артефакты пары N>0 —
     в `pipeline/f{N:04d}/` (helper `pipeline_prefix`, все 15 шагов); эндпоинт
     `GET .../blast-event/capture-summary` (агрегаты по сессиям взрыва); desktop:
     «Снять ещё (в серию)» + галерея + «Загрузить с диска…» + сводный поллинг +
     блок «Снимки взрыва»; оффлайн-серия одной операцией (легаси-payload реплеится).
     Остаток: миниатюры в списке снимков (текст пока).
   - **AUTH-2** (токены на смену): realm `accessTokenLifespan=900`,
     `ssoSessionIdleTimeout=43200`, `ssoSessionMaxLifespan=46800` — в realm-export
     И применено kcadm к живому realm; desktop: проактивный refresh (раз в минуту,
     за 3 мин до истечения), `refresh_outcome()` ok/expired/offline (5xx=offline!),
     диалог «Сессия истекла» + форма логина, тулбар «Авторизован до HH:MM»
     (срок refresh-токена из keyring).
   - **EDIT-1** (редактирование): PATCH quarry/section/device/calibration/blast-event
     (+ passport только DRAFT, 409 иначе) — все с AuditLog `entity_updated`
     (old/new только изменённые поля; helper `app/services/audit.py`); desktop:
     «Изменить выбранный…» (карьеры — admin, участки — blaster), «Изменить черновик…»/
     «Изменить взрыв…» в деталях паспорта; общий `EditFormDialog` шлёт только diff.
     Остаток: формы device/calibration — вместе с экраном «Устройства» (CAM-CUSTOM).
   - **Юзертест UT-7 написан в roadmap** (секция QA) — ждёт прогона владельцем.
1. **Остаток продуктового бэклога:** REPORT-X (PDF/DOCX/XLSX/CSV) → CAM-CUSTOM →
   UI-2; M5-d — исследовательская ветка; STORE-1 по ходу REPORT-X.
2. **Сессия 2026-06-11, часть 2 — съёмка и фиксы** (`2925d7d`…`0d9388f`):
   - Экран съёмки: авто-превью + авто-выбор ZED, кнопка «Зарегистрировать ZED»
     (заводская калибровка по серийнику из UI), чек-лист готовности.
   - Починен «Client not found» при логине: в работающем Keycloak не было клиента
     `zmetrics-desktop` (realm старше realm-export.json) — добавлен kcadm'ом.
     Туда же: сервис-аккаунту `zmetrics-backend` выданы `manage-users`/`view-users`
     (это был корень «опять 500 при создании пользователей»). Файл realm-export
     уже содержит и то и другое; при переимпорте realm всё будет из коробки.
   - Смена роли поверх существующей = upsert (revoke+grant с аудитом), не 500.
   - Stale карта доступов в десктопе (после неудачного `/me/access` или создания
     карьера админ «без прав») — ретраи + refresh по событиям.
   - Превью камеры падало на каждом кадре (non-contiguous buffer) — починено.
   - Калибровка-заглушка валила rectification криптичной ошибкой Rodrigues [1x9]:
     worker терпим к плоским матрицам, заглушка (fx<50px) отклоняется с понятным
     сообщением, UI предупреждает при стерео-кадре с TEST-устройством.
2. **M3-PART сделан: последний mock-участок реального контура закрыт.**
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
   **Не проверено на железе** — worker уже пересобран и запущен с флагами;
   остался сам прогон (камера + желательно реальные камни).
3. **E2E на реальном железе пройден (2026-06-10, до M3-PART):** ZED 2 (SN 21907252,
   2.2K SBS) → заводская калибровка → rectification → IGEV++ depth на RTX 5080 →
   2.74M точек → SAM3 (0 камней на столе — честно) → mock-грансостав. Прогон:
   `desktop\.venv\Scripts\python.exe scripts\e2e_capture_smoke.py --password changeme`.
   `DEPTH_BACKEND=igev` (+`ENABLE_REAL_STEREO=true`) включает IGEV++ вместо SGBM;
   веса `infra/models/igev/` (gitignore по `*.pth`), дефолт sceneflow.pth;
   инференс даунскейлится до `IGEV_MAX_INFERENCE_WIDTH=1536`.
4. **Калибровка ZED:** заводской conf качается по серийнику (`calib.stereolabs.com/?SN=…`),
   конвертация в `CalibrationCreate` — `zmetrics_desktop/capture/zed_calibration.py`
   (Rodrigues([RX,CV,RZ]), **T=[−Baseline,TY,TZ] мм** — конвенция zed-opencv-native).
   Глубина в **мм** (как T); регистрация теперь из UI («Зарегистрировать ZED»).
5. **Флаги НЕ в `infra/.env`** (файл закрыт для агента): передаются через process env
   при `compose up`. Добавить руками: `ENABLE_REAL_STEREO=true`, `ENABLE_SAM3=true`,
   `DEPTH_BACKEND=igev`. Иначе следующий `compose up` вернёт mock/SGBM.
6. **Docker Desktop чинился дважды:** крах на старте «file cannot be accessed by the
   system» = битые unix-сокеты; лечится `wsl -d docker-desktop -e rm -rf
   /mnt/host/c/Users/Nikita/AppData/Local/Docker/run` (+ `docker-secrets-engine`).
   Docker AI отключён. Данные WSL на **G:** (`wslDataFolder`), C: не забивается.
7. **Следующее:** старт продуктового бэклога (см. п.0 — предлагаю CAP-MULTI + AUTH-2);
   съёмка реального развала с реальной калибровкой ZED; юзертесты UT-D1/UT-D2;
   PyInstaller (UT-D6).

---

## Tests (последний прогон 2026-06-11)

| Suite | Result |
|---|---|
| backend (`backend/tests`, в контейнере) | 89 passed (79 + 3 CAP-MULTI + 7 EDIT-1) |
| worker (`worker/tests`, хостовый `worker\.venv`) | 42 passed (pipeline_prefix/frame_index — без регрессий) |
| desktop (`desktop/tests`) | 139 passed (121 + серия/оффлайн-серия + AUTH-2 + EditFormDialog/гейтинг) |

---

## Runtime notes

- Стек работает на коде rev 13: backend/worker пересобраны и перезапущены 2026-06-11
  (вечер) с GPU-оверлеем и флагами через process env; миграция `75bb00d854b1`
  (analysis_job.frame_index) применена. Живой realm уже несёт таймауты AUTH-2
  (применено kcadm). Холодный старт:
  `docker compose -f infra\docker-compose.yml -f infra\docker-compose.gpu.yml up -d --remove-orphans`
  с выставленными `ENABLE_REAL_STEREO/ENABLE_SAM3/DEPTH_BACKEND` в окружении.
- **Работающий Keycloak realm старше realm-export.json**, добито kcadm'ом по живому:
  клиент `zmetrics-desktop` (PKCE) создан; сервис-аккаунту `zmetrics-backend` выданы
  `manage-users`/`view-users`. Старые клиенты `zmetrics-web`/`zmetrics-mobile` всё ещё
  в realm (ROPC-смоук через `zmetrics-mobile` работает). Полная синхронизация = снести
  realm и дать переимпортироваться (потеряются ручные пользователи/пароли).
- ⚠ `infra/docker-compose.yml` всё ещё хардкодит `ENABLE_DEV_SEED: "true"` — для общих
  стендов поменять на `${ENABLE_DEV_SEED:-false}`.

---

## Layer status

| Layer | State |
|---|---|
| **backend** | M1 + SEC + ADMIN-USERS-1 + grant-upsert + CAP-MULTI (frame_index, capture-summary) + EDIT-1 (PATCH×6 с AuditLog) |
| **worker** | SAM3 (CUDA) + M2-STEREO + IGEV++ depth + M5-a/M5-b + M3-PART + per-frame pipeline prefix (CAP-MULTI); mock-шагов в реальном контуре больше нет |
| **desktop** | Все экраны DESKTOP-1 + capture UX + серия снимков/загрузка с диска/«Снимки взрыва» (CAP-MULTI) + проактивный refresh и «Авторизован до» (AUTH-2) + формы «Изменить» (EDIT-1); юзертесты UT-7, UT-D1..D5 не пройдены; PyInstaller не делался |
| **infra** | compose: IGEV env+volume; GPU-оверлей; realm-export: клиенты + AUTH-2 таймауты (12 ч сессии); живой realm допатчен kcadm'ом (клиенты, роли SA, таймауты) |

---

## Priority queue

| Pri | ID | Item | Notes |
|---|---|---|---|
| **P1** | UT-7 | Юзертест CAP-MULTI/AUTH-2/EDIT-1 | чек-лист в roadmap (QA) |
| **P1** | — | Съёмка через UI с реальной калибровкой ZED («Зарегистрировать ZED» → снять) | проверит M3-PART на железе; на столе ждём «0 камней → нет отчёта» |
| **P2** | REPORT-X | Отчёты PDF/DOCX/XLSX/CSV с сегментацией/паспортом/рекомендациями | тянет за собой STORE-1 |
| **P2** | CAM-CUSTOM | Нестандартные стереокамеры + редактирование калибровки | ручной ввод + импорт .conf/.yml; экран «Устройства» доберёт UI для EDIT-1 device/calibration |
| **P2** | UT-D1..D5 | Юзертесты десктопа (логин, CRUD, capture, отчёты, админка) | чек-листы в roadmap (DESKTOP-1) |
| **P3** | M5-d | ML-модель рекомендаций + синтетические обучающие данные (Kuz-Ram) | исследовательская ветка |
| **P3** | UI-2 | Современный интерфейс (QSS-тема, иконки, тосты) | |
| **P3** | — | PyInstaller build + UT-D6 на чистой Windows | |
| ~~done~~ | CAP-MULTI | ~~Серия фото к взрыву + загрузка с диска + capture-summary~~ | 2026-06-11 |
| ~~done~~ | AUTH-2 | ~~Токены на смену + проактивный refresh + «Авторизован до»~~ | 2026-06-11 |
| ~~done~~ | EDIT-1 | ~~PATCH-редактирование + AuditLog + формы в десктопе~~ | 2026-06-11 |
| ~~done~~ | DEPTH-2 | ~~IGEV++ вместо SGBM~~ | 2026-06-10 |
| ~~done~~ | M3-PART | ~~Реальные particle_volumes + granulometry~~ | 2026-06-11, нужен прогон на железе |
| ~~done~~ | — | ~~Capture UX + фикс-пачка (realm/roles/превью/заглушка)~~ | 2026-06-11 |

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
