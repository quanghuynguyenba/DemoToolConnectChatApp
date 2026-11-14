"""PostgreSQL connection helpers for Neon (pooled app traffic)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import psycopg2
from psycopg2.extensions import connection as PgConnection

from app.config import get_settings


class DatabaseError(Exception):
    """Raised when the database is unavailable or misconfigured."""


_PLACEHOLDER_MARKERS = (
    "user:password@",
    "ep-xxxxx",
    "YOUR_PASSWORD",
)


def _is_placeholder(url: str) -> bool:
    lowered = url.lower()
    return any(marker.lower() in lowered for marker in _PLACEHOLDER_MARKERS)


def ensure_sslmode(url: str) -> str:
    """Neon requires TLS; append sslmode=require when missing."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if "sslmode" not in query:
        query["sslmode"] = ["require"]
    new_query = urlencode({k: v[0] for k, v in query.items()})
    return urlunparse(parsed._replace(query=new_query))


def _resolve_url(*, unpooled: bool = False) -> str:
    settings = get_settings()
    url = (
        settings.database_url_unpooled if unpooled else settings.database_url
    ).strip()
    if not url:
        raise DatabaseError(
            "DATABASE_URL is empty. Run `neon deploy` (or `neon env pull`) "
            "after `neon login`, or paste a Neon URI into .env."
        )
    if _is_placeholder(url):
        raise DatabaseError(
            "DATABASE_URL still looks like a placeholder. Run `neon deploy` "
            "to pull the real Neon connection string."
        )
    return ensure_sslmode(url)


@contextmanager
def get_connection(*, unpooled: bool = False) -> Generator[PgConnection, None, None]:
    """Yield a psycopg2 connection.

    App queries use the pooled DATABASE_URL (default).
    Schema/migrations should pass unpooled=True (DATABASE_URL_UNPOOLED).
    """
    url = _resolve_url(unpooled=unpooled)
    try:
        conn = psycopg2.connect(url, connect_timeout=30)
    except psycopg2.Error as exc:
        raise DatabaseError(
            f"Cannot connect to Neon PostgreSQL. Check DATABASE_URL. Detail: {exc}"
        ) from exc
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_connection() -> tuple[bool, str]:
    """Return (ok, message) for UI status display."""
    settings = get_settings()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), version()")
                db_name, version = cur.fetchone()
        branch = settings.neon_branch or "unknown"
        short_ver = str(version).split(",")[0]
        return True, f"Neon connected · db={db_name} · branch={branch} · {short_ver}"
    except DatabaseError as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, f"Database check failed: {exc}"
