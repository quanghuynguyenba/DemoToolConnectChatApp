"""Employee Telegram authentication flow (update_authen_v1.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.auth import messages as msg
from app.auth.otp import OtpConfig, generate_otp, hash_otp, otp_expiry, verify_otp
from app.auth.phone import PhoneNormalizationError, mask_email, normalize_phone
from app.config import get_settings
from app.db.auth_repository import (
    AuthSessionRepository,
    EmployeeRepository,
    LinkRepository,
    TelegramAccountRepository,
)
from app.db.repository import UserRepository
from app.services.audit import audit
from app.services.email_otp import EmailDeliveryError, send_otp_email


@dataclass
class AuthReply:
    text: str
    request_contact: bool = False
    remove_keyboard: bool = False


class AuthenticationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.otp_cfg = OtpConfig(
            length=self.settings.otp_length,
            ttl_seconds=self.settings.otp_ttl_seconds,
            max_attempts=self.settings.otp_max_attempts,
            resend_cooldown_seconds=self.settings.otp_resend_cooldown_seconds,
            max_resends=self.settings.otp_max_resends,
        )
        self.employees = EmployeeRepository()
        self.accounts = TelegramAccountRepository()
        self.links = LinkRepository()
        self.sessions = AuthSessionRepository()
        self.legacy_users = UserRepository()

    def handle_start(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        chat_type: str,
        username: str | None,
    ) -> AuthReply:
        audit("TELEGRAM_START", "ok", telegram_user_id=telegram_user_id)

        if chat_type != "private":
            audit(
                "TELEGRAM_START",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="PRIVATE_CHAT_REQUIRED",
            )
            return AuthReply(text=msg.PRIVATE_CHAT_REQUIRED)

        active = self.links.get_active_by_telegram_user_id(telegram_user_id)
        if active:
            return AuthReply(text=msg.ALREADY_LINKED)

        self.accounts.upsert(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=username,
        )
        return AuthReply(text=msg.WELCOME_START, request_contact=True)

    def handle_contact(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        chat_type: str,
        username: str | None,
        contact: dict,
    ) -> AuthReply:
        if chat_type != "private":
            audit(
                "CONTACT_RECEIVED",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="PRIVATE_CHAT_REQUIRED",
            )
            return AuthReply(text=msg.PRIVATE_CHAT_REQUIRED)

        audit("CONTACT_RECEIVED", "ok", telegram_user_id=telegram_user_id)

        contact_user_id = contact.get("user_id")
        phone_raw = contact.get("phone_number") or ""

        if contact_user_id is None:
            audit(
                "CONTACT_VERIFIED",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="CONTACT_REQUIRED",
            )
            return AuthReply(text=msg.CONTACT_REQUIRED, request_contact=True)

        if int(contact_user_id) != int(telegram_user_id):
            audit(
                "CONTACT_VERIFIED",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="CONTACT_NOT_OWNED_BY_SENDER",
            )
            return AuthReply(text=msg.CONTACT_NOT_OWNED, remove_keyboard=True)

        try:
            phone = normalize_phone(phone_raw, self.settings.phone_default_region)
        except PhoneNormalizationError:
            audit(
                "CONTACT_VERIFIED",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="INVALID_PHONE",
            )
            return AuthReply(text=msg.GENERIC_AUTH_FAILED, remove_keyboard=True)

        audit("CONTACT_VERIFIED", "ok", telegram_user_id=telegram_user_id)

        matches = self.employees.find_by_phone(phone)
        if not matches:
            audit(
                "EMPLOYEE_FOUND",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="EMPLOYEE_NOT_FOUND",
            )
            return AuthReply(text=msg.GENERIC_AUTH_FAILED, remove_keyboard=True)

        active_matches = [e for e in matches if e.status == "active"]
        if len(matches) > 1 and len(active_matches) != 1:
            audit(
                "EMPLOYEE_FOUND",
                "rejected",
                telegram_user_id=telegram_user_id,
                reason="DUPLICATE_PHONE",
            )
            return AuthReply(text=msg.DUPLICATE_PHONE, remove_keyboard=True)

        if not active_matches:
            employee = matches[0]
            audit(
                "EMPLOYEE_FOUND",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=employee.id,
                reason="EMPLOYEE_INACTIVE",
            )
            return AuthReply(text=msg.GENERIC_AUTH_FAILED, remove_keyboard=True)

        employee = active_matches[0]
        audit(
            "EMPLOYEE_FOUND",
            "ok",
            telegram_user_id=telegram_user_id,
            employee_id=employee.id,
        )

        if self.links.get_active_by_employee_id(employee.id):
            audit(
                "ACCOUNT_LINKED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=employee.id,
                reason="EMPLOYEE_ALREADY_LINKED",
            )
            return AuthReply(text=msg.EMPLOYEE_ALREADY_LINKED, remove_keyboard=True)

        existing_tg_link = self.links.get_active_by_telegram_user_id(telegram_user_id)
        if existing_tg_link:
            audit(
                "ACCOUNT_LINKED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=employee.id,
                reason="TELEGRAM_ALREADY_LINKED",
            )
            return AuthReply(text=msg.TELEGRAM_ALREADY_LINKED, remove_keyboard=True)

        self.accounts.upsert(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=username,
            phone_number=phone,
        )

        otp = generate_otp(self.otp_cfg.length)
        otp_digest = hash_otp(otp, pepper=self.settings.otp_pepper)
        expires = otp_expiry(self.otp_cfg.ttl_seconds)
        session = self.sessions.create(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            employee_id=employee.id,
            phone_number=phone,
            otp_hash=otp_digest,
            expires_at=expires,
        )

        try:
            send_otp_email(
                to_email=employee.email,
                otp=otp,
                settings=self.settings,
            )
        except EmailDeliveryError:
            self.sessions.mark_expired(session.id)
            audit(
                "OTP_SENT",
                "failed",
                telegram_user_id=telegram_user_id,
                employee_id=employee.id,
                reason="EMAIL_DELIVERY_FAILED",
            )
            return AuthReply(text=msg.OTP_SEND_FAILED, remove_keyboard=True)

        audit(
            "OTP_SENT",
            "ok",
            telegram_user_id=telegram_user_id,
            employee_id=employee.id,
        )
        return AuthReply(
            text=msg.OTP_PROMPT.format(masked_email=mask_email(employee.email)),
            remove_keyboard=True,
        )

    def handle_otp_text(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        text: str,
        username: str | None,
    ) -> AuthReply | None:
        candidate = text.strip()
        if not candidate.isdigit() or len(candidate) != self.otp_cfg.length:
            return None

        session = self.sessions.get_open_for_telegram(telegram_user_id)
        if session is None:
            return AuthReply(text=msg.OTP_EXPIRED)

        now = datetime.now(timezone.utc)
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            self.sessions.mark_expired(session.id)
            audit(
                "OTP_FAILED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=session.employee_id,
                reason="OTP_EXPIRED",
            )
            return AuthReply(text=msg.OTP_EXPIRED)

        if not session.otp_hash or not verify_otp(
            candidate, session.otp_hash, pepper=self.settings.otp_pepper
        ):
            attempts = session.attempts + 1
            locked = attempts >= self.otp_cfg.max_attempts
            self.sessions.update_after_failed_attempt(
                session.id, attempts=attempts, lock=locked
            )
            audit(
                "OTP_FAILED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=session.employee_id,
                reason="OTP_LOCKED" if locked else "OTP_INVALID",
            )
            return AuthReply(text=msg.OTP_LOCKED if locked else msg.OTP_INVALID)

        assert session.employee_id is not None
        return self._complete_link(
            session_id=session.id,
            employee_id=session.employee_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            username=username,
            phone_number=session.phone_number,
        )

    def revoke_employee_link(
        self,
        *,
        employee_id: UUID,
        reason: str,
        actor: str = "admin",
    ) -> int:
        count = self.links.revoke(employee_id=employee_id, reason=reason)
        if count:
            audit(
                "ACCOUNT_REVOKED",
                "ok",
                employee_id=employee_id,
                reason=reason,
                actor=actor,
            )
        return count

    def revoke_link_by_id(
        self,
        *,
        link_id: UUID,
        reason: str,
        actor: str = "admin",
        telegram_user_id: int | None = None,
        employee_id: UUID | None = None,
        chat_id: int | None = None,
    ) -> int:
        count = self.links.revoke(link_id=link_id, reason=reason)
        if count:
            audit(
                "ACCOUNT_REVOKED",
                "ok",
                telegram_user_id=telegram_user_id,
                employee_id=employee_id,
                reason=reason,
                actor=actor,
            )
            if chat_id is not None:
                self.legacy_users.deactivate(chat_id)
        return count

    def _complete_link(
        self,
        *,
        session_id: UUID,
        employee_id: UUID,
        telegram_user_id: int,
        telegram_chat_id: int,
        username: str | None,
        phone_number: str | None,
    ) -> AuthReply:
        if self.links.get_active_by_employee_id(employee_id):
            self.sessions.mark_expired(session_id)
            audit(
                "ACCOUNT_LINKED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=employee_id,
                reason="EMPLOYEE_ALREADY_LINKED",
            )
            return AuthReply(text=msg.EMPLOYEE_ALREADY_LINKED)

        if self.links.get_active_by_telegram_user_id(telegram_user_id):
            self.sessions.mark_expired(session_id)
            audit(
                "ACCOUNT_LINKED",
                "rejected",
                telegram_user_id=telegram_user_id,
                employee_id=employee_id,
                reason="TELEGRAM_ALREADY_LINKED",
            )
            return AuthReply(text=msg.TELEGRAM_ALREADY_LINKED)

        account = self.accounts.upsert(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=username,
            phone_number=phone_number,
        )
        self.links.create_active_link(
            employee_id=employee_id,
            telegram_account_id=account.id,
        )
        self.sessions.mark_completed(session_id)

        # Sync Phase-1 telegram_users so admin UI remains consistent
        self.legacy_users.upsert(
            chat_id=telegram_chat_id,
            username=username,
            display_name=None,
            is_active=True,
        )

        audit(
            "OTP_SUCCESS",
            "ok",
            telegram_user_id=telegram_user_id,
            employee_id=employee_id,
        )
        audit(
            "ACCOUNT_LINKED",
            "ok",
            telegram_user_id=telegram_user_id,
            employee_id=employee_id,
        )
        return AuthReply(text=msg.AUTH_SUCCESS)
