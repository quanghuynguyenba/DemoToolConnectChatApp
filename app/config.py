"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
# Prefer existing .env (neon deploy / neon env pull write here when present)
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / ".env.local", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    database_url: str
    database_url_unpooled: str
    neon_branch: str
    neon_branch_id: str
    dry_run: bool
    # Auth / OTP
    auth_dev_mode: bool
    otp_pepper: str
    otp_length: int
    otp_ttl_seconds: int
    otp_max_attempts: int
    otp_resend_cooldown_seconds: int
    otp_max_resends: int
    phone_default_region: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool

    @property
    def has_telegram_token(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def has_database_url(self) -> bool:
        return bool(self.database_url.strip())

    @property
    def has_smtp(self) -> bool:
        return bool(
            self.smtp_host.strip()
            and self.smtp_from.strip()
            and self.smtp_user.strip()
            and self.smtp_password.strip()
        )


def get_settings() -> Settings:
    pooled = os.getenv("DATABASE_URL", "").strip()
    unpooled = os.getenv("DATABASE_URL_UNPOOLED", "").strip() or pooled
    pepper = os.getenv("OTP_PEPPER", "").strip() or "dev-only-change-me"
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        database_url=pooled,
        database_url_unpooled=unpooled,
        neon_branch=os.getenv("NEON_BRANCH", "").strip(),
        neon_branch_id=os.getenv("NEON_BRANCH_ID", "").strip(),
        dry_run=_as_bool(os.getenv("DRY_RUN"), default=True),
        auth_dev_mode=_as_bool(os.getenv("AUTH_DEV_MODE"), default=False),
        otp_pepper=pepper,
        otp_length=_as_int(os.getenv("OTP_LENGTH"), 6),
        otp_ttl_seconds=_as_int(os.getenv("OTP_TTL_SECONDS"), 300),
        otp_max_attempts=_as_int(os.getenv("OTP_MAX_ATTEMPTS"), 5),
        otp_resend_cooldown_seconds=_as_int(
            os.getenv("OTP_RESEND_COOLDOWN_SECONDS"), 60
        ),
        otp_max_resends=_as_int(os.getenv("OTP_MAX_RESENDS"), 5),
        phone_default_region=os.getenv("PHONE_DEFAULT_REGION", "VN").strip() or "VN",
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=_as_int(os.getenv("SMTP_PORT"), 587),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_from=os.getenv("SMTP_FROM", "").strip(),
        smtp_use_tls=_as_bool(os.getenv("SMTP_USE_TLS"), default=True),
    )
