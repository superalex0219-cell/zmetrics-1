import 'dart:convert';

/// Decodes a JWT payload **without verifying the signature** — for display
/// claims only (name/email/sub). Signature + issuer verification is the
/// backend's job on every API call. Returns `{}` on any parse error.
Map<String, dynamic> decodeJwtClaims(String jwt) {
  try {
    final parts = jwt.split('.');
    if (parts.length != 3) return const {};
    final normalized = base64Url.normalize(parts[1]);
    final decoded = utf8.decode(base64Url.decode(normalized));
    final claims = jsonDecode(decoded);
    return claims is Map<String, dynamic> ? claims : const {};
  } catch (_) {
    return const {};
  }
}
