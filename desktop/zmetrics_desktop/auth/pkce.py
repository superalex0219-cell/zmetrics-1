"""PKCE helpers (RFC 7636, S256)."""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PkcePair:
    verifier: str
    challenge: str
    method: str = "S256"


def generate_pkce_pair() -> PkcePair:
    """Generate a code_verifier and its S256 code_challenge.

    The verifier is 43–128 chars of unreserved characters (RFC 7636 §4.1);
    ``token_urlsafe(64)`` yields ~86 chars, well within range.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return PkcePair(verifier=verifier, challenge=challenge)
