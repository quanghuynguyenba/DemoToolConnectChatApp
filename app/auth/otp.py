"""Cryptographically secure OTP generation and hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class OtpConfig:
    length: int = 6
    ttl_seconds: int = 300
    max_attempts: int = 5
    resend_cooldown_seconds: int = 60
    max_resends: int = 5


def generate_otp(length: int = 6) -> str:
    """Return a numeric OTP using CSPRNG. Never log this value."""
    upper = 10**length
    value = secrets.randbelow(upper)
    return str(value).zfill(length)


def hash_otp(otp: str, *, pepper: str) -> str:
    """Hash OTP with HMAC-SHA256; store only the digest."""
    return hmac.new(
        pepper.encode("utf-8"),
        otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(otp: str, otp_hash: str, *, pepper: str) -> bool:
    expected = hash_otp(otp, pepper=pepper)
    return hmac.compare_digest(expected, otp_hash)


def otp_expiry(ttl_seconds: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
