"""Filings ingest — chunk + embed + write to pgvector.

Chunking strategy (v1, locked):
1. Try section-based split on 10-K `ITEM N.` / `ITEM NA.` headers.
2. If the document has fewer than 2 recognised sections, fall back to
   fixed 512-character chunks (whitespace-trimmed, empty chunks dropped).

Embeddings: sentence-transformers `all-MiniLM-L6-v2` (384-dim).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict

from ria.fixtures import FilingRef, iter_filings

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_FIXED_WIDTH = 512
# `ITEM 1.` / `ITEM 1A.` / `ITEM 7.` etc. — case-insensitive, start of line.
_ITEM_RE = re.compile(
    r"(?im)^\s*(ITEM\s+\d+[A-Z]?\.)(.*)$"
)

_model = None  # lazy singleton — first embed call triggers load + cache.


class Chunk(TypedDict):
    section: str | None
    text: str
    strategy: str  # "section" | "fixed512"


# ---------- chunking ----------------------------------------------------------


def _fixed_chunks(text: str) -> list[Chunk]:
    stripped = text.strip()
    if not stripped:
        return []
    out: list[Chunk] = []
    for i in range(0, len(stripped), _FIXED_WIDTH):
        piece = stripped[i : i + _FIXED_WIDTH].strip()
        if piece:
            out.append({"section": None, "text": piece, "strategy": "fixed512"})
    return out


def chunk_filing(text: str) -> list[Chunk]:
    """Split a filing's raw text into ordered chunks."""
    if not text or not text.strip():
        return []

    matches = list(_ITEM_RE.finditer(text))
    if len(matches) < 2:
        return _fixed_chunks(text)

    chunks: list[Chunk] = []
    for i, m in enumerate(matches):
        header = m.group(1).strip().upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        chunks.append({"section": header, "text": body, "strategy": "section"})
    return chunks if chunks else _fixed_chunks(text)


# ---------- embedding ---------------------------------------------------------


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    arr = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [[float(x) for x in row] for row in arr]


# ---------- accession ---------------------------------------------------------


def accession_from_path(path: Path) -> str:
    """Synthetic accession key: filename stem (SEC accession IDs unavailable
    in fixture mode). Keeps the value human-readable for citations."""
    return path.stem


# ---------- main ingest loop --------------------------------------------------


def ingest_filing(path: Path, conn: Any) -> int:
    """Chunk+embed one file, insert into `filings_chunks`. Returns row count.

    The connection must already have pgvector registered (use
    `ria.db.conn.ensure_schema`).
    """
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    chunks = chunk_filing(text)
    if not chunks:
        return 0
    vectors = embed_texts([c["text"] for c in chunks])
    accession = accession_from_path(Path(path))
    rows = [
        (accession, c["section"], c["text"], v)
        for c, v in zip(chunks, vectors, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO filings_chunks (accession, section, text, embedding)"
            " VALUES (%s, %s, %s, %s)",
            rows,
        )
    conn.commit()
    return len(rows)


def ingest_all(
    conn: Any, *, root: Path | None = None, reset: bool = True
) -> dict[str, int]:
    """Ingest every filing fixture; returns {strategy: count, "rows": total}."""
    if reset:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM filings_chunks")
        conn.commit()

    totals = {"rows": 0, "section": 0, "fixed512": 0, "files": 0}
    for ref in iter_filings(root=root):
        ref: FilingRef
        text = ref.path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_filing(text)
        if not chunks:
            continue
        vectors = embed_texts([c["text"] for c in chunks])
        rows = [
            (accession_from_path(ref.path), c["section"], c["text"], v)
            for c, v in zip(chunks, vectors, strict=True)
        ]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO filings_chunks (accession, section, text, embedding)"
                " VALUES (%s, %s, %s, %s)",
                rows,
            )
        conn.commit()
        totals["rows"] += len(rows)
        totals["files"] += 1
        for c in chunks:
            totals[c["strategy"]] = totals.get(c["strategy"], 0) + 1
    return totals
