"""Send company-email OTP via SMTP (Gmail App Password supported)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when OTP email cannot be delivered."""


def smtp_configured(settings: Settings) -> bool:
    return bool(
        settings.smtp_host.strip()
        and settings.smtp_from.strip()
        and settings.smtp_user.strip()
        and settings.smtp_password.strip()
    )


def _gmail_app_password(raw: str) -> str:
    """Gmail App Passwords are 16 chars; spaces are optional in UI copy/paste."""
    return "".join(raw.split())


def send_otp_email(*, to_email: str, otp: str, settings: Settings) -> None:
    """Email a one-time code. Never log the OTP plaintext."""
    if not smtp_configured(settings):
        raise EmailDeliveryError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_FROM, SMTP_USER, "
            "and SMTP_PASSWORD in .env (Gmail: smtp.gmail.com + App Password)."
        )

    ttl_min = max(1, settings.otp_ttl_seconds // 60)
    message = EmailMessage()
    message["Subject"] = "Mã xác thực Telegram Bot (OTP)"
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(
        "Xin chào,\n\n"
        "Mã OTP để liên kết Telegram với hệ thống thông báo nội bộ:\n\n"
        f"    {otp}\n\n"
        f"Mã có hiệu lực trong {ttl_min} phút.\n"
        "Hãy quay lại chat Telegram với bot và nhập đúng 6 chữ số này.\n\n"
        "Không chia sẻ mã này với người khác.\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này.\n"
    )
    message.add_alternative(
        "<html><body>"
        "<p>Xin chào,</p>"
        "<p>Mã OTP để liên kết Telegram với hệ thống thông báo nội bộ:</p>"
        f"<p style='font-size:28px;letter-spacing:4px;'><strong>{otp}</strong></p>"
        f"<p>Mã có hiệu lực trong <strong>{ttl_min} phút</strong>.</p>"
        "<p>Quay lại chat Telegram với bot và <strong>nhập đúng 6 chữ số</strong> này.</p>"
        "<p>Không chia sẻ mã với người khác.</p>"
        "</body></html>",
        subtype="html",
    )

    password = _gmail_app_password(settings.smtp_password)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(settings.smtp_user, password)
            smtp.send_message(message)
        logger.info("OTP email accepted by SMTP for recipient domain=%s", to_email.split("@")[-1])
    except Exception as exc:  # noqa: BLE001
        logger.exception("SMTP send failed for OTP email")
        raise EmailDeliveryError(
            "Failed to send OTP email. Check Gmail App Password / SMTP settings."
        ) from exc
