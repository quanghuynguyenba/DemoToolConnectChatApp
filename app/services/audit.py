"""Security audit logging helpers."""

from __future__ import annotations

from uuid import UUID

from app.db.auth_repository import AuthLogRepository


def audit(
    action: str,
    result: str,
    *,
    telegram_user_id: int | None = None,
    employee_id: UUID | None = None,
    reason: str | None = None,
    actor: str | None = None,
) -> None:
    AuthLogRepository().insert(
        action=action,
        result=result,
        telegram_user_id=telegram_user_id,
        employee_id=employee_id,
        reason=reason,
        actor=actor,
    )
