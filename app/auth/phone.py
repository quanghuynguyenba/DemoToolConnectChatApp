"""Phone number normalization (E.164)."""

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException


class PhoneNormalizationError(ValueError):
    """Raised when a phone number cannot be normalized."""


def normalize_phone(raw: str, default_region: str = "VN") -> str:
    """Normalize to E.164 (e.g. +84912345678)."""
    text = (raw or "").strip()
    if not text:
        raise PhoneNormalizationError("Phone number is empty.")
    try:
        parsed = phonenumbers.parse(text, default_region)
    except NumberParseException as exc:
        raise PhoneNormalizationError(f"Invalid phone number: {exc}") from exc
    if not phonenumbers.is_possible_number(parsed):
        raise PhoneNormalizationError("Phone number is not possible.")
    if not phonenumbers.is_valid_number(parsed):
        raise PhoneNormalizationError("Phone number is not valid.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_email(email: str) -> str:
    """Mask local part for user-facing messages."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = "*" * len(local)
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"
