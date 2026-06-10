# ZMetrics - STATUS

**Last updated:** 2026-06-10 (rev 9 — desktop pivot landed: web/mobile removed, working tree clean)
**Git HEAD:** `d3a5e22`

---

## TL;DR для следующей сессии

1. **Единственный клиент — десктоп (PySide6).** `frontend/` (React) и `mobile/` (Flutter)
   удалены из репозитория и из compose (`8d3a5fd`); финальное состояние заархивировано
   коммитом `0609afe`. Все экраны DESKTOP-1 написаны: дашборд, карьеры/участки, паспорта,
   съёмка+анализ, отчёты, рекомендации, админка.
2. **Незакоммиченный хвост 2026-06-08/09 разобран по коммитам:** ADMIN-USERS-1 (backend),
   M2-STEREO + SAM3 hardening + M5-b LLM (worker), bootstrap-фикс карьеров, capture E2E
   фиксы, инфра-обвязка флагов. Рабочее дерево чистое.
3. **Найден и закоммичен потерянный пакет моделей** `backend/app/db/models/` — его с
   2026-06-05 глотал незаякоренный паттерн `models/` в `.gitignore`; свежий клон до
   `61a2169` не запускался вовсе.
4. **ADMIN-USERS работает живьём.** 500 на `POST /admin/users` был из-за
   `KC_CLIENT_ID=zmetrics-frontend` в `infra/.env` (клиента нет в realm → отказ в
   сервис-токене). Исправлено на `zmetrics-backend`, проверено E2E: 201 + временный пароль.
5. **Следующее по плану:** юзертесты UT-D1 (smoke: логин/keyring/оффлайн-бар/дашборд) и
   UT-D2 (CRUD + workflow паспорта + ролевой гейтинг) — нужен Никита за живым приложением.
   Потом SAM3-метаданные в панели job, PyInstaller-сборка (UT-D6).

---

## Tests (последний прогон 2026-06-10, локальные venv)

| Suite | Result |
|---|---|
| backend (`backend/tests`) | 78 passed |
| worker (`worker/tests`) | 32 passed |
| desktop (`desktop/tests`) | 113 passed |

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
| **worker** | SAM3 (CUDA, за `ENABLE_SAM3`) + M2-STEREO (за `ENABLE_REAL_STEREO`) + M5-a/M5-b (LLM за флагом, дремлет без ключа) |
| **desktop** | Все экраны DESKTOP-1 готовы; юзертесты UT-D1..D5 не пройдены; PyInstaller не делался |
| **infra** | compose без frontend; GPU-оверлей; realm-export без web/mobile клиентов |

---

## Priority queue

| Pri | ID | Item | Notes |
|---|---|---|---|
| **P1** | UT-D1 | Smoke десктопа: логин (OIDC/keyring), статус-бар, дашборд | чек-лист в roadmap (DESKTOP-1) |
| **P1** | UT-D2 | CRUD + workflow паспорта + ролевой гейтинг | после UT-D1 |
| **P2** | UT-D3 | Capture E2E на веб-камере (mock-пайплайн, оффлайн-сценарий) | |
| **P2** | UT-D4/UT-2 | Отчёты + рекомендации (rule engine E2E через десктоп) | |
| **P2** | UT-D5 | Админка и роли (выдать/отозвать, AuditLog) | admin-фича уже включена и работает |
| **P3** | — | SAM3-метаданные в панели завершённого job + smoke на `rock-sample.png` без камеры | картинка теперь в `desktop/zmetrics_desktop/assets/` |
| **P3** | — | PyInstaller build + UT-D6 на чистой Windows | |
| later | DEPTH-2 | IGEV-Stereo вместо SGBM | после E2E на SGBM |

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
