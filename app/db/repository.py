"""CRUD helpers for telegram users and notification logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.db.connection import get_connection


@dataclass
class TelegramUser:
    id: int
    chat_id: int
    username: str | None
    display_name: str | None
    connected_at: datetime
    is_active: bool


@dataclass
class NotificationRecord:
    id: int
    content: str
    sent_at: datetime
    recipient_count: int
    status: str
    error_detail: str | None


def _row_to_user(row: tuple[Any, ...]) -> TelegramUser:
    return TelegramUser(
        id=row[0],
        chat_id=row[1],
        username=row[2],
        display_name=row[3],
        connected_at=row[4],
        is_active=row[5],
    )


class UserRepository:
    def list_active(self) -> list[TelegramUser]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chat_id, username, display_name, connected_at, is_active
                    FROM telegram_users
                    WHERE is_active = TRUE
                    ORDER BY connected_at DESC
                    """
                )
                return [_row_to_user(row) for row in cur.fetchall()]

    def list_all(self) -> list[TelegramUser]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chat_id, username, display_name, connected_at, is_active
                    FROM telegram_users
                    ORDER BY connected_at DESC
                    """
                )
                return [_row_to_user(row) for row in cur.fetchall()]

    def upsert(
        self,
        chat_id: int,
        username: str | None = None,
        display_name: str | None = None,
        is_active: bool = True,
    ) -> TelegramUser:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO telegram_users (chat_id, username, display_name, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (chat_id) DO UPDATE SET
                        username = COALESCE(EXCLUDED.username, telegram_users.username),
                        display_name = COALESCE(EXCLUDED.display_name, telegram_users.display_name),
                        is_active = EXCLUDED.is_active,
                        connected_at = CASE
                            WHEN EXCLUDED.is_active THEN NOW()
                            ELSE telegram_users.connected_at
                        END
                    RETURNING id, chat_id, username, display_name, connected_at, is_active
                    """,
                    (chat_id, username, display_name, is_active),
                )
                row = cur.fetchone()
                assert row is not None
                return _row_to_user(row)

    def deactivate(self, chat_id: int) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE telegram_users
                    SET is_active = FALSE
                    WHERE chat_id = %s
                    """,
                    (chat_id,),
                )
                return cur.rowcount > 0


class NotificationRepository:
    def insert(
        self,
        content: str,
        recipient_count: int,
        status: str,
        error_detail: str | None = None,
    ) -> NotificationRecord:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications (content, recipient_count, status, error_detail)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, content, sent_at, recipient_count, status, error_detail
                    """,
                    (content, recipient_count, status, error_detail),
                )
                row = cur.fetchone()
                assert row is not None
                return NotificationRecord(
                    id=row[0],
                    content=row[1],
                    sent_at=row[2],
                    recipient_count=row[3],
                    status=row[4],
                    error_detail=row[5],
                )

    def list_recent(self, limit: int = 20) -> list[NotificationRecord]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, sent_at, recipient_count, status, error_detail
                    FROM notifications
                    ORDER BY sent_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [
                    NotificationRecord(
                        id=row[0],
                        content=row[1],
                        sent_at=row[2],
                        recipient_count=row[3],
                        status=row[4],
                        error_detail=row[5],
                    )
                    for row in cur.fetchall()
                ]
