"""Sprint 1 — filings ingest unit tests.

Does NOT require Postgres: we exercise the pure-Python chunker and the
embedding function.
"""

from __future__ import annotations


SECTIONED_10K = """UNITED STATES SECURITIES AND EXCHANGE COMMISSION

ITEM 1. BUSINESS
We make phones and cloud services and software. This is a long paragraph
describing the business in enough detail that it beats the fallback
threshold for chunking. Repeat: business business business business.

ITEM 1A. RISK FACTORS
Macroeconomic risk, supply chain risk, regulatory risk, cybersecurity risk.
This section also has plenty of text to justify its own chunk boundary.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
Revenue grew year-over-year driven by services and wearables.
Operating margin expanded. Free cash flow rose.
"""

UNSECTIONED = ("lorem ipsum dolor sit amet " * 120).strip()  # ~3000 chars


def test_chunk_filing_section_based() -> None:
    from ria.ingest.filings import chunk_filing

    chunks = chunk_filing(SECTIONED_10K)
    # Three ITEM blocks → three section chunks
    assert len(chunks) == 3
    sections = [c["section"] for c in chunks]
    assert any("ITEM 1." in s for s in sections if s)
    assert any("ITEM 1A." in s for s in sections if s)
    assert any("ITEM 7." in s for s in sections if s)
    strategy = {c["strategy"] for c in chunks}
    assert strategy == {"section"}


def test_chunk_filing_falls_back_to_fixed512() -> None:
    from ria.ingest.filings import chunk_filing

    chunks = chunk_filing(UNSECTIONED)
    assert len(chunks) >= 5  # 3000 / 512 ≈ 6 chunks
    for c in chunks:
        assert c["strategy"] == "fixed512"
        assert len(c["text"]) <= 512
        assert c["section"] is None


def test_chunk_filing_empty_returns_empty() -> None:
    from ria.ingest.filings import chunk_filing

    assert chunk_filing("") == []
    assert chunk_filing("   \n  ") == []


def test_embed_texts_produces_384dim() -> None:
    from ria.ingest.filings import embed_texts

    vecs = embed_texts(["apple earnings beat", "tesla delivery miss"])
    assert len(vecs) == 2
    assert all(len(v) == 384 for v in vecs)
    # not identical vectors for different inputs
    assert vecs[0] != vecs[1]


def test_embed_texts_empty_input() -> None:
    from ria.ingest.filings import embed_texts

    assert embed_texts([]) == []


def test_accession_from_path_parses_real() -> None:
    from pathlib import Path
    from ria.ingest.filings import accession_from_path

    acc = accession_from_path(Path("AAPL_10-K_20251031.txt"))
    assert "AAPL" in acc
    assert "10-K" in acc
    assert "20251031" in acc


def test_accession_from_path_handles_stub() -> None:
    from pathlib import Path
    from ria.ingest.filings import accession_from_path

    acc = accession_from_path(Path("stub_META.txt"))
    assert "META" in acc
    assert "stub" in acc.lower()
