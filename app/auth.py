from __future__ import annotations

import hashlib
import hmac
import secrets
import string


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return "Password must include at least one letter."
    if not any(c.isdigit() for c in password):
        return "Password must include at least one number."
    allowed = set(string.printable)
    if not set(password).issubset(allowed):
        return "Password contains unsupported characters."
    return None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
    return hmac.compare_digest(digest.hex(), expected_hex)
