"""One-shot RAG ingest: chunk every filing fixture → embed → pgvector.

Idempotent: wipes `filings_chunks` before inserting. Safe to re-run.
Exit code is 0 on success; non-zero on DB/schema failure.

Usage:
    python scripts/run_ingest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# src/ lives next to scripts/ — keep this script runnable without `pip install -e .`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ria.db.conn import connect, ensure_schema  # noqa: E402
from ria.ingest.filings import ingest_all  # noqa: E402


def main() -> int:
    conn = connect()
    try:
        ensure_schema(conn)
        totals = ingest_all(conn, reset=True)
    finally:
        conn.close()
    print(
        f"ingested files={totals['files']} rows={totals['rows']} "
        f"section={totals.get('section', 0)} fixed512={totals.get('fixed512', 0)}"
    )
    if totals["rows"] < 10:
        print(f"FAIL: filings_chunks rows={totals['rows']} < 10", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
