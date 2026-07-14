"""Password hashing and session-token generation -- Sprint 30.

Uses PBKDF2-HMAC-SHA256 via Python's stdlib `hashlib` -- no new dependency
(bcrypt/passlib) needed at this POC's recruiter count (a handful of
accounts, not a public-signup user base where bcrypt's tunable cost
factor and wide ecosystem support would matter more). 200,000 iterations
matches OWASP's current minimum recommendation for PBKDF2-SHA256.

Session tokens are opaque, high-entropy random strings (not JWTs) --
validity is checked by looking the token up in the `sessions` table (see
app/models/recruiter.py), so a session can be revoked by deleting its row.
No signature verification, no client-side decoding, nothing to get subtly
wrong -- simplicity is the point at this scale.
"""
from __future__ import annotations

import hashlib
import secrets

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Returns (password_hash, salt) as hex strings. Pass an existing salt
    to verify a password against a stored hash; omit it to hash a new
    password for the first time."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt)
    # Constant-time comparison -- a naive `==` leaks timing information
    # about how many leading bytes matched.
    return secrets.compare_digest(candidate_hash, password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
