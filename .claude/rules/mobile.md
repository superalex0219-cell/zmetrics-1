---
paths:
  - "mobile/**/*.dart"
---

# Flutter Mobile Rules

## Architecture

Feature-first folder layout:
```
lib/
  core/         # auth, router, DI, config
  features/
    passport/   # data/ domain/ presentation/
    capture/
    report/
  shared/
    offline/    # SyncManager
    widgets/    # reusable UI components
```

One feature = one folder. Do not mix feature code.

## State management

- Use `flutter_bloc` (`Bloc` or `Cubit` per feature)
- Events and states are `freezed` sealed classes
- No business logic in `StatefulWidget` — keep widgets dumb

## Domain models

All domain models use `freezed` + `json_serializable`:
```dart
@freezed
class BlastPassport with _$BlastPassport {
  const factory BlastPassport({
    required String id,
    required String status,
    // ...
  }) = _BlastPassport;
  factory BlastPassport.fromJson(Map<String, dynamic> json) => _$BlastPassportFromJson(json);
}
```

## Auth

- OIDC via `flutter_appauth` (PKCE, `zmetrics-mobile` Keycloak client)
- Store tokens in `flutter_secure_storage` only — never `SharedPreferences`
- Never log access tokens or refresh tokens
- Token refresh: intercept 401 in `dio` interceptor, refresh, retry once

## Offline-first

- All write operations (passport create, capture session, frame upload) go through `SyncManager`
- Each queued operation has a client-generated `idempotency_key` (UUID v4)
- Queue is processed on `connectivity_plus` `ConnectivityResult.mobile` or `wifi` event
- Max retry: 5 attempts; after that, surface to user with error state

## HTTP

Use `dio` with:
- `AuthInterceptor`: adds `Authorization: Bearer <token>`, handles refresh
- `RetryInterceptor`: retries 503 up to 3 times with exponential backoff
- Base URL from `core/config.dart` (not hardcoded)

## Android

- Min SDK: 26
- Target SDK: 34
- Required permissions declared in `AndroidManifest.xml`: `CAMERA`, `INTERNET`, `ACCESS_NETWORK_STATE`
- ZED 2 integration: Camera2 API placeholder for now; ZED SDK at M2+
