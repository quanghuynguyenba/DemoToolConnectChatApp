"""CRUD for employee authentication tables (update_authen_v1.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.connection import get_connection


@dataclass
class Employee:
    id: UUID
    employee_code: str
    full_name: str
    phone_number: str
    email: str
    department: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class TelegramAccount:
    id: UUID
    telegram_user_id: int
    telegram_chat_id: int
    telegram_username: str | None
    phone_number: str | None
    created_at: datetime


@dataclass
class EmployeeTelegramLink:
    id: UUID
    employee_id: UUID
    telegram_account_id: UUID
    status: str
    verified_at: datetime | None
    linked_at: datetime | None
    revoked_at: datetime | None
    revoked_reason: str | None
    created_at: datetime


@dataclass
class AuthSession:
    id: UUID
    telegram_user_id: int
    telegram_chat_id: int
    employee_id: UUID | None
    phone_number: str | None
    otp_hash: str | None
    status: str
    expires_at: datetime
    attempts: int
    resend_count: int
    last_otp_sent_at: datetime | None
    created_at: datetime


@dataclass
class AuthLog:
    id: UUID
    telegram_user_id: int | None
    employee_id: UUID | None
    action: str
    result: str
    reason: str | None
    actor: str | None
    created_at: datetime


@dataclass
class AuthorizedRecipient:
    chat_id: int
    telegram_user_id: int
    username: str | None
    employee_code: str
    full_name: str
    department: str | None


def _employee(row: tuple[Any, ...]) -> Employee:
    return Employee(
        id=row[0],
        employee_code=row[1],
        full_name=row[2],
        phone_number=row[3],
        email=row[4],
        department=row[5],
        status=row[6],
        created_at=row[7],
        updated_at=row[8],
    )


def _account(row: tuple[Any, ...]) -> TelegramAccount:
    return TelegramAccount(
        id=row[0],
        telegram_user_id=row[1],
        telegram_chat_id=row[2],
        telegram_username=row[3],
        phone_number=row[4],
        created_at=row[5],
    )


def _link(row: tuple[Any, ...]) -> EmployeeTelegramLink:
    return EmployeeTelegramLink(
        id=row[0],
        employee_id=row[1],
        telegram_account_id=row[2],
        status=row[3],
        verified_at=row[4],
        linked_at=row[5],
        revoked_at=row[6],
        revoked_reason=row[7],
        created_at=row[8],
    )


def _session(row: tuple[Any, ...]) -> AuthSession:
    return AuthSession(
        id=row[0],
        telegram_user_id=row[1],
        telegram_chat_id=row[2],
        employee_id=row[3],
        phone_number=row[4],
        otp_hash=row[5],
        status=row[6],
        expires_at=row[7],
        attempts=row[8],
        resend_count=row[9],
        last_otp_sent_at=row[10],
        created_at=row[11],
    )


_EMPLOYEE_COLS = (
    "id, employee_code, full_name, phone_number, email, department, "
    "status, created_at, updated_at"
)
_ACCOUNT_COLS = (
    "id, telegram_user_id, telegram_chat_id, telegram_username, "
    "phone_number, created_at"
)
_LINK_COLS = (
    "id, employee_id, telegram_account_id, status, verified_at, "
    "linked_at, revoked_at, revoked_reason, created_at"
)
_LINK_COLS_L = (
    "l.id, l.employee_id, l.telegram_account_id, l.status, l.verified_at, "
    "l.linked_at, l.revoked_at, l.revoked_reason, l.created_at"
)
_SESSION_COLS = (
    "id, telegram_user_id, telegram_chat_id, employee_id, phone_number, "
    "otp_hash, status, expires_at, attempts, resend_count, "
    "last_otp_sent_at, created_at"
)


class EmployeeRepository:
    def list_all(self) -> list[Employee]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_EMPLOYEE_COLS}
                    FROM employees
                    ORDER BY employee_code
                    """
                )
                return [_employee(r) for r in cur.fetchall()]

    def get_by_id(self, employee_id: UUID) -> Employee | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_EMPLOYEE_COLS} FROM employees WHERE id = %s",
                    (str(employee_id),),
                )
                row = cur.fetchone()
                return _employee(row) if row else None

    def find_by_phone(self, phone_number: str) -> list[Employee]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_EMPLOYEE_COLS}
                    FROM employees
                    WHERE phone_number = %s
                    ORDER BY created_at
                    """,
                    (phone_number,),
                )
                return [_employee(r) for r in cur.fetchall()]

    def upsert(
        self,
        *,
        employee_code: str,
        full_name: str,
        phone_number: str,
        email: str,
        department: str | None = None,
        status: str = "active",
    ) -> Employee:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO employees (
                        employee_code, full_name, phone_number, email,
                        department, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (employee_code) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        phone_number = EXCLUDED.phone_number,
                        email = EXCLUDED.email,
                        department = EXCLUDED.department,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    RETURNING {_EMPLOYEE_COLS}
                    """,
                    (
                        employee_code,
                        full_name,
                        phone_number,
                        email,
                        department,
                        status,
                    ),
                )
                row = cur.fetchone()
                assert row is not None
                return _employee(row)

    def set_status(self, employee_id: UUID, status: str) -> Employee | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE employees
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING {_EMPLOYEE_COLS}
                    """,
                    (status, str(employee_id)),
                )
                row = cur.fetchone()
                return _employee(row) if row else None


class TelegramAccountRepository:
    def upsert(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None = None,
        phone_number: str | None = None,
    ) -> TelegramAccount:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO telegram_accounts (
                        telegram_user_id, telegram_chat_id,
                        telegram_username, phone_number
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (telegram_user_id) DO UPDATE SET
                        telegram_chat_id = EXCLUDED.telegram_chat_id,
                        telegram_username = COALESCE(
                            EXCLUDED.telegram_username,
                            telegram_accounts.telegram_username
                        ),
                        phone_number = COALESCE(
                            EXCLUDED.phone_number,
                            telegram_accounts.phone_number
                        )
                    RETURNING {_ACCOUNT_COLS}
                    """,
                    (
                        telegram_user_id,
                        telegram_chat_id,
                        telegram_username,
                        phone_number,
                    ),
                )
                row = cur.fetchone()
                assert row is not None
                return _account(row)

    def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramAccount | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_ACCOUNT_COLS}
                    FROM telegram_accounts
                    WHERE telegram_user_id = %s
                    """,
                    (telegram_user_id,),
                )
                row = cur.fetchone()
                return _account(row) if row else None


class LinkRepository:
    def get_active_by_telegram_user_id(
        self, telegram_user_id: int
    ) -> EmployeeTelegramLink | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_LINK_COLS_L}
                    FROM employee_telegram_links l
                    JOIN telegram_accounts a ON a.id = l.telegram_account_id
                    WHERE a.telegram_user_id = %s AND l.status = 'active'
                    """,
                    (telegram_user_id,),
                )
                row = cur.fetchone()
                return _link(row) if row else None

    def get_active_by_employee_id(
        self, employee_id: UUID
    ) -> EmployeeTelegramLink | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_LINK_COLS}
                    FROM employee_telegram_links
                    WHERE employee_id = %s AND status = 'active'
                    """,
                    (str(employee_id),),
                )
                row = cur.fetchone()
                return _link(row) if row else None

    def list_all_with_details(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        l.id, l.status, l.verified_at, l.linked_at,
                        l.revoked_at, l.revoked_reason,
                        e.employee_code, e.full_name, e.status AS employee_status,
                        a.telegram_user_id, a.telegram_chat_id, a.telegram_username
                    FROM employee_telegram_links l
                    JOIN employees e ON e.id = l.employee_id
                    JOIN telegram_accounts a ON a.id = l.telegram_account_id
                    ORDER BY COALESCE(l.linked_at, l.created_at) DESC
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "link_id": r[0],
                        "status": r[1],
                        "verified_at": r[2],
                        "linked_at": r[3],
                        "revoked_at": r[4],
                        "revoked_reason": r[5],
                        "employee_code": r[6],
                        "full_name": r[7],
                        "employee_status": r[8],
                        "telegram_user_id": r[9],
                        "telegram_chat_id": r[10],
                        "telegram_username": r[11],
                    }
                    for r in rows
                ]

    def create_active_link(
        self,
        *,
        employee_id: UUID,
        telegram_account_id: UUID,
    ) -> EmployeeTelegramLink:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO employee_telegram_links (
                        employee_id, telegram_account_id, status,
                        verified_at, linked_at
                    )
                    VALUES (%s, %s, 'active', NOW(), NOW())
                    RETURNING {_LINK_COLS}
                    """,
                    (str(employee_id), str(telegram_account_id)),
                )
                row = cur.fetchone()
                assert row is not None
                return _link(row)

    def revoke(
        self,
        *,
        link_id: UUID | None = None,
        employee_id: UUID | None = None,
        reason: str,
    ) -> int:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if link_id is not None:
                    cur.execute(
                        """
                        UPDATE employee_telegram_links
                        SET status = 'revoked',
                            revoked_at = NOW(),
                            revoked_reason = %s
                        WHERE id = %s AND status = 'active'
                        """,
                        (reason, str(link_id)),
                    )
                elif employee_id is not None:
                    cur.execute(
                        """
                        UPDATE employee_telegram_links
                        SET status = 'revoked',
                            revoked_at = NOW(),
                            revoked_reason = %s
                        WHERE employee_id = %s AND status = 'active'
                        """,
                        (reason, str(employee_id)),
                    )
                else:
                    return 0
                return cur.rowcount


class AuthSessionRepository:
    def create(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        employee_id: UUID,
        phone_number: str,
        otp_hash: str,
        expires_at: datetime,
    ) -> AuthSession:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Invalidate prior open sessions for this Telegram user
                cur.execute(
                    """
                    UPDATE authentication_sessions
                    SET status = 'expired'
                    WHERE telegram_user_id = %s
                      AND status IN ('pending_otp', 'verified')
                    """,
                    (telegram_user_id,),
                )
                cur.execute(
                    f"""
                    INSERT INTO authentication_sessions (
                        telegram_user_id, telegram_chat_id, employee_id,
                        phone_number, otp_hash, status, expires_at,
                        last_otp_sent_at
                    )
                    VALUES (%s, %s, %s, %s, %s, 'pending_otp', %s, NOW())
                    RETURNING {_SESSION_COLS}
                    """,
                    (
                        telegram_user_id,
                        telegram_chat_id,
                        str(employee_id),
                        phone_number,
                        otp_hash,
                        expires_at,
                    ),
                )
                row = cur.fetchone()
                assert row is not None
                return _session(row)

    def get_open_for_telegram(self, telegram_user_id: int) -> AuthSession | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {_SESSION_COLS}
                    FROM authentication_sessions
                    WHERE telegram_user_id = %s
                      AND status = 'pending_otp'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (telegram_user_id,),
                )
                row = cur.fetchone()
                return _session(row) if row else None

    def get_by_id(self, session_id: UUID) -> AuthSession | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_SESSION_COLS} FROM authentication_sessions WHERE id = %s",
                    (str(session_id),),
                )
                row = cur.fetchone()
                return _session(row) if row else None

    def update_after_failed_attempt(
        self, session_id: UUID, *, attempts: int, lock: bool
    ) -> AuthSession | None:
        status = "locked" if lock else "pending_otp"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE authentication_sessions
                    SET attempts = %s, status = %s
                    WHERE id = %s
                    RETURNING {_SESSION_COLS}
                    """,
                    (attempts, status, str(session_id)),
                )
                row = cur.fetchone()
                return _session(row) if row else None

    def mark_completed(self, session_id: UUID) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE authentication_sessions
                    SET status = 'completed', otp_hash = NULL
                    WHERE id = %s
                    """,
                    (str(session_id),),
                )

    def mark_expired(self, session_id: UUID) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE authentication_sessions
                    SET status = 'expired', otp_hash = NULL
                    WHERE id = %s
                    """,
                    (str(session_id),),
                )

    def refresh_otp(
        self,
        session_id: UUID,
        *,
        otp_hash: str,
        expires_at: datetime,
        resend_count: int,
    ) -> AuthSession | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE authentication_sessions
                    SET otp_hash = %s,
                        expires_at = %s,
                        resend_count = %s,
                        last_otp_sent_at = NOW(),
                        attempts = 0,
                        status = 'pending_otp'
                    WHERE id = %s
                    RETURNING {_SESSION_COLS}
                    """,
                    (otp_hash, expires_at, resend_count, str(session_id)),
                )
                row = cur.fetchone()
                return _session(row) if row else None


class AuthLogRepository:
    def insert(
        self,
        *,
        action: str,
        result: str,
        telegram_user_id: int | None = None,
        employee_id: UUID | None = None,
        reason: str | None = None,
        actor: str | None = None,
    ) -> AuthLog:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO authentication_logs (
                        telegram_user_id, employee_id, action, result, reason, actor
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, telegram_user_id, employee_id, action, result,
                              reason, actor, created_at
                    """,
                    (
                        telegram_user_id,
                        str(employee_id) if employee_id else None,
                        action,
                        result,
                        reason,
                        actor,
                    ),
                )
                row = cur.fetchone()
                assert row is not None
                return AuthLog(
                    id=row[0],
                    telegram_user_id=row[1],
                    employee_id=row[2],
                    action=row[3],
                    result=row[4],
                    reason=row[5],
                    actor=row[6],
                    created_at=row[7],
                )

    def list_recent(self, limit: int = 30) -> list[AuthLog]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, telegram_user_id, employee_id, action, result,
                           reason, actor, created_at
                    FROM authentication_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [
                    AuthLog(
                        id=r[0],
                        telegram_user_id=r[1],
                        employee_id=r[2],
                        action=r[3],
                        result=r[4],
                        reason=r[5],
                        actor=r[6],
                        created_at=r[7],
                    )
                    for r in cur.fetchall()
                ]


class AuthorizationRepository:
    def list_active_recipients(self) -> list[AuthorizedRecipient]:
        """Only Active employee + Active telegram link may receive notifications."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        a.telegram_chat_id,
                        a.telegram_user_id,
                        a.telegram_username,
                        e.employee_code,
                        e.full_name,
                        e.department
                    FROM employee_telegram_links l
                    JOIN employees e ON e.id = l.employee_id
                    JOIN telegram_accounts a ON a.id = l.telegram_account_id
                    WHERE l.status = 'active'
                      AND e.status = 'active'
                    ORDER BY e.employee_code
                    """
                )
                return [
                    AuthorizedRecipient(
                        chat_id=r[0],
                        telegram_user_id=r[1],
                        username=r[2],
                        employee_code=r[3],
                        full_name=r[4],
                        department=r[5],
                    )
                    for r in cur.fetchall()
                ]
