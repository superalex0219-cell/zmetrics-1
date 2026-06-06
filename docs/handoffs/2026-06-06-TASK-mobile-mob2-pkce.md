# TASK (mobile): MOB-2 — OIDC PKCE via flutter_appauth

**Date:** 2026-06-06
**From:** curating chat (post BACK-SEC-2)
**Layer:** `mobile/` ONLY — DI wiring, AndroidManifest, auth repo restore, login screen
**Review agent:** `mobile-reviewer`
**Priority:** P1 — unblocks production deployment (ROPC breaks when Keycloak disables it)

---

## Context

`OidcService` (PKCE) and `OidcAuthRepository` are already fully implemented in
`mobile/lib/core/auth/oidc_service.dart` and `mobile/lib/core/auth/auth_repository.dart`.
The Keycloak `zmetrics-mobile` client already has `redirectUris: ["zmetrics://callback"]`.

The live DI path still wires `DevPasswordAuthRepository` (ROPC) instead of PKCE.
Three additional gaps prevent the existing PKCE code from working end-to-end.

---

## Deliverable 1 — `AndroidManifest.xml`: add redirect URI intent-filter

**File:** `mobile/android/app/src/main/AndroidManifest.xml`

**Bug:** `flutter_appauth` uses Chrome Custom Tabs and returns the auth code to the app via
the custom scheme. Without a registered `Activity` for `zmetrics://`, Android cannot route
the redirect back and the browser flow hangs.

**Fix:** Inside `<application>`, add after the existing `<activity>`:

```xml
<!-- flutter_appauth: handles Keycloak OIDC redirect URI zmetrics://callback -->
<activity
    android:name="com.linusu.flutter_web_auth_2.CallbackActivity"
    android:exported="true">
    <intent-filter android:label="flutter_web_auth_2">
        <action android:name="android.intent.action.VIEW"/>
        <category android:name="android.intent.category.DEFAULT"/>
        <category android:name="android.intent.category.BROWSABLE"/>
        <data android:scheme="zmetrics"/>
    </intent-filter>
</activity>
```

> Note: `flutter_appauth` 8.x uses `flutter_web_auth_2` internally for the callback.
> Verify the activity class name in `mobile/.dart_tool/package_config.json` or
> `flutter_appauth`'s README if the version differs. If it uses `net.openid.appauth`,
> replace with `net.openid.appauth.RedirectUriReceiverActivity`.

---

## Deliverable 2 — `di.dart`: wire OidcAuthRepository for live mode

**File:** `mobile/lib/core/di.dart`

**Bug:** Lines 86–87 create `DevPasswordAuthRepository` (ROPC) for the live backend path.
`OidcAuthRepository` + `OidcService` already exist and implement the correct interfaces.

**Current code (live branch, lines 85–94):**
```dart
// Live backend wiring. Auth is dev ROPC (web-friendly, public client) and
// also serves as the bearer-token provider for the Dio interceptor.
final auth = DevPasswordAuthRepository(config);
final TokenProvider tokens = auth;
final dio = ApiClient(
  config,
  tokens,
  onAuthFailure: authEventBus.notifySessionExpired,
).dio;
return AppDependencies._(
  config: config,
  authRepository: auth,
  ...
```

**Fix:** Replace with:
```dart
// Live backend wiring — OIDC PKCE via flutter_appauth.
// OidcService implements TokenProvider; OidcAuthRepository implements AuthRepository.
final oidcService = OidcService(config);
final auth = OidcAuthRepository(oidcService);
final TokenProvider tokens = oidcService;
final dio = ApiClient(
  config,
  tokens,
  onAuthFailure: authEventBus.notifySessionExpired,
).dio;
return AppDependencies._(
  config: config,
  authRepository: auth,
  ...
```

Add the necessary imports at the top:
```dart
import 'auth/oidc_service.dart';
```
(`OidcAuthRepository` is already imported from `auth_repository.dart`.)

`DevPasswordAuthRepository` import may remain — it is unused in the live path but the class
itself is not deleted (it may be useful for e2e test automation later).

---

## Deliverable 3 — `OidcAuthRepository.restore()`: decode stored token claims

**File:** `mobile/lib/core/auth/auth_repository.dart`

**Bug:** `OidcAuthRepository.restore()` (lines 56–63) checks for a stored token but returns
a hardcoded dummy user:
```dart
return const AuthUser(id: 'restored', displayName: 'Signed-in user');
```

After app restart the UI shows "Signed-in user" instead of the real username, and `id` is
wrong — downstream role checks that key off `AuthUser.id` will fail.

**Fix:** Import `jwt_decode.dart` (already in the project at `core/auth/jwt_decode.dart`)
and decode the stored access token:

```dart
import 'jwt_decode.dart';

// inside OidcAuthRepository:
@override
Future<AuthUser?> restore() async {
  final token = await _oidc.currentAccessToken();
  if (token == null || token.isEmpty) return null;
  final claims = decodeJwtClaims(token);
  final sub = (claims['sub'] as String?) ?? '';
  if (sub.isEmpty) return null;
  return AuthUser(
    id: sub,
    displayName: (claims['name'] ??
            claims['preferred_username'] ??
            claims['email'] ??
            sub) as String,
    email: claims['email'] as String?,
  );
}
```

This mirrors the exact pattern in `DevPasswordAuthRepository._userFromToken()`.

---

## Deliverable 4 — `login_screen.dart`: remove ROPC form for live mode

**File:** `mobile/lib/features/auth/presentation/login_screen.dart`

**Bug:** The screen shows username/password `TextField`s when `!mock` (live backend mode).
These fields feed `DevPasswordAuthRepository.signIn(username, password)`.
With PKCE, `OidcAuthRepository.signIn()` ignores those arguments and opens a browser.
Showing the fields confuses users and implies password entry is needed.

**Fix:**
- Remove `_username` and `_password` `TextEditingController` fields entirely.
- Remove the `if (!mock) ...[ TextField(...), TextField(...) ]` block.
- Keep the subtitle: change `'Connected to backend'` → `'Sign in via Keycloak'` for live mode.
- Change the button label to `'Sign in'` for both modes (already is).
- The `_signIn` method simplifies to always call `cubit.signIn()` without credentials:

```dart
void _signIn(BuildContext context) {
  context.read<AuthCubit>().signIn();
}
```

The mock path works unchanged (one-tap, `signIn()` with no args).

---

## Tests to add / update

1. **`test/core/auth/oidc_auth_repository_test.dart`** (new file):
   - `restore_returns_null_when_no_token`: mock `OidcService.currentAccessToken` → null → restore returns null
   - `restore_decodes_claims_from_stored_token`: mock token with known sub/name claims → restore returns correct `AuthUser`

2. **`test/features/auth/login_screen_test.dart`** (update or new):
   - In mock mode: single "Sign in" button, no text fields
   - In live mode: single "Sign in" button, no username/password text fields visible

---

## Boundaries / guardrails

- Touch `mobile/` only. No backend changes.
- Do NOT delete `DevPasswordAuthRepository` — keep it for possible test automation use.
- Do NOT add a new `--dart-define` flag; the existing `ZM_USE_MOCKS` split is sufficient.
- `flutter_secure_storage` stays as the token store — never `SharedPreferences`.
- Never log token values (security.md).
- The Keycloak realm-export already has `"redirectUris": ["zmetrics://callback"]` — no infra change needed.

---

## Acceptance

```bash
cd mobile

# Unit tests pass
flutter test test/core/auth/
flutter test test/features/auth/

# Build compiles (emulator not required for acceptance)
flutter build apk --debug \
  --dart-define=ZM_USE_MOCKS=false \
  --dart-define=ZM_API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ZM_KC_ISSUER=http://10.0.2.2:8080/realms/zmetrics

# Manual smoke (if emulator available):
# 1. flutter run with above defines
# 2. App shows "Sign in via Keycloak" button — NO username/password fields
# 3. Tap Sign in → Chrome Custom Tab opens Keycloak login page
# 4. Log in as admin-user / changeme
# 5. Redirects back to app, user lands on quarry list
# 6. Kill + reopen app → session restores, user sees real display name
```

## When done

Report: files changed, test count (flutter test), confirm each deliverable.
