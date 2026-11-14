"""Broadcast notification content to authorized Active Telegram links only."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings
from app.db.auth_repository import AuthorizationRepository
from app.db.repository import NotificationRepository
from app.services.audit import audit
from app.telegram.client import SendResult, TelegramClient, TelegramClientError


@dataclass
class BroadcastResult:
    status: str
    recipient_count: int
    success_count: int
    failure_count: int
    dry_run: bool
    results: list[SendResult] = field(default_factory=list)
    error_detail: str | None = None
    notification_id: int | None = None


def broadcast_notification(content: str) -> BroadcastResult:
    text = content.strip()
    if not text:
        return BroadcastResult(
            status="failed",
            recipient_count=0,
            success_count=0,
            failure_count=0,
            dry_run=False,
            error_detail="Notification content is empty.",
        )

    settings = get_settings()
    recipients = AuthorizationRepository().list_active_recipients()
    chat_ids = [r.chat_id for r in recipients]
    recipient_count = len(chat_ids)

    if recipient_count == 0:
        record = NotificationRepository().insert(
            content=text,
            recipient_count=0,
            status="failed",
            error_detail="No Active authenticated Telegram links.",
        )
        return BroadcastResult(
            status="failed",
            recipient_count=0,
            success_count=0,
            failure_count=0,
            dry_run=False,
            error_detail=(
                "No Active authenticated Telegram links. "
                "Users must complete contact + OTP authentication."
            ),
            notification_id=record.id,
        )

    # Dry-run when explicitly enabled OR when token is missing
    use_dry_run = settings.dry_run or not settings.has_telegram_token
    if use_dry_run:
        reason = (
            "DRY_RUN=true"
            if settings.dry_run
            else "TELEGRAM_BOT_TOKEN missing — forced dry-run"
        )
        fake_results = [
            SendResult(chat_id=cid, ok=True, detail=f"dry-run ({reason})")
            for cid in chat_ids
        ]
        record = NotificationRepository().insert(
            content=text,
            recipient_count=recipient_count,
            status="dry_run",
            error_detail=reason,
        )
        audit(
            "NOTIFICATION_SENT",
            "ok",
            reason=f"dry_run recipients={recipient_count}",
            actor="admin",
        )
        return BroadcastResult(
            status="dry_run",
            recipient_count=recipient_count,
            success_count=recipient_count,
            failure_count=0,
            dry_run=True,
            results=fake_results,
            error_detail=reason,
            notification_id=record.id,
        )

    try:
        client = TelegramClient()
        results = client.broadcast(text, chat_ids)
    except TelegramClientError as exc:
        record = NotificationRepository().insert(
            content=text,
            recipient_count=recipient_count,
            status="failed",
            error_detail=str(exc),
        )
        audit(
            "NOTIFICATION_SENT",
            "failed",
            reason=str(exc),
            actor="admin",
        )
        return BroadcastResult(
            status="failed",
            recipient_count=recipient_count,
            success_count=0,
            failure_count=recipient_count,
            dry_run=False,
            error_detail=str(exc),
            notification_id=record.id,
        )

    success_count = sum(1 for r in results if r.ok)
    failure_count = recipient_count - success_count
    if failure_count == 0:
        status = "sent"
        error_detail = None
    elif success_count == 0:
        status = "failed"
        error_detail = "; ".join(f"{r.chat_id}: {r.detail}" for r in results if not r.ok)
    else:
        status = "partial"
        error_detail = "; ".join(f"{r.chat_id}: {r.detail}" for r in results if not r.ok)

    record = NotificationRepository().insert(
        content=text,
        recipient_count=recipient_count,
        status=status,
        error_detail=error_detail,
    )
    audit(
        "NOTIFICATION_SENT",
        "ok" if status in {"sent", "partial", "dry_run"} else "failed",
        reason=f"status={status} success={success_count}/{recipient_count}",
        actor="admin",
    )
    return BroadcastResult(
        status=status,
        recipient_count=recipient_count,
        success_count=success_count,
        failure_count=failure_count,
        dry_run=False,
        results=results,
        error_detail=error_detail,
        notification_id=record.id,
    )
