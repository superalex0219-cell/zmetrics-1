---
paths:
  - "mobile/**/*.dart"
---

# Flutter Mobile Rules

## Stack
- Flutter 3.x, Dart null safety required
- State management: `flutter_bloc`
- Auth: `flutter_appauth` (OIDC PKCE flow to Keycloak `zmetrics-mobile` client)
- Offline queue: SQLite via `sqflite`
- HTTP: `dio`
- Domain models: `freezed` + `json_serializable`
- Routing: `go_router`
- Connectivity: `connectivity_plus`

## Architecture
- Feature-first folder structure: `lib/features/{feature}/data|domain|presentation/`
- Core services in `lib/core/`
- Shared widgets and utilities in `lib/shared/`

## Offline-First Rules
- All write operations (create capture_session, create passport, upload frames) go through `SyncManager`
- `SyncManager` stores pending operations in SQLite table `pending_uploads`
- Queue is processed when `connectivity_plus` reports network available
- Each queued item must have an `idempotency_key` (UUID, generated client-side) to prevent duplicate server-side records

## Android
- Minimum SDK: 26 (required for USB-C connectivity with ZED 2)
- Target SDK: 34
- Permissions needed: `CAMERA`, `READ_EXTERNAL_STORAGE`, `INTERNET`, `ACCESS_NETWORK_STATE`
- ZED 2 USB integration is a later milestone (M2+); for now, use Camera2 API for placeholder capture

## Security
- Store tokens in `flutter_secure_storage`, never in SharedPreferences
- Never log access tokens or refresh tokens
