"""Apply sql/schema.sql using Neon's direct (unpooled) connection.

Usage (from project root, after `neon deploy`):

    python -m scripts.init_schema
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db.connection import DatabaseError, get_connection


def main() -> None:
    schema_path = _ROOT / "sql" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    try:
        # Migrations should use the direct endpoint, not the pooler
        with get_connection(unpooled=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        print(f"Applied schema from {schema_path} (unpooled Neon connection)")
    except DatabaseError as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
