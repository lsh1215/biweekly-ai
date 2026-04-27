"""5 hard-evidence regex patterns for the fact-checker (LLM-free).

PRD §3 D3 spec, deterministic. Pure functions, no I/O.

Types:
  (a) numbers - integer / decimal / percent / currency
  (b) semver  - vX.Y.Z (with optional prerelease/build)
  (c) quotes  - "..." (≥ 8 chars) or 「...」
  (d) dates   - YYYY / YYYY-MM / YYYY-MM-DD
  (e) proper nouns - capitalized alpha-numeric tokens (length ≥ 3) that
      are not common English stopwords. Heuristic only.
"""
from __future__ import annotations

import re
from typing import Iterable

# (a) numbers --------------------------------------------------------------
# percent first so 0.03% is captured as a unit.
NUMBER_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?%")
# currency: $1.5M / ₩1000 / €99 (allow K/M/B suffix).
CURRENCY_RE = re.compile(r"[\$₩€]\d+(?:\.\d+)?[KMB]?")
# bare numbers - any integer or decimal (≥ 1 digit). Last so it does not
# steal currency/percent matches.
NUMBER_PLAIN_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.%])")

# (b) semver ----------------------------------------------------------------
# X.Y.Z (with optional v prefix and optional prerelease/build chunks).
SEMVER_RE = re.compile(r"\bv?\d+\.\d+\.\d+(?:[.-][a-zA-Z0-9]+)*\b")

# (c) quotes ----------------------------------------------------------------
DOUBLE_QUOTE_RE = re.compile(r'"([^"]{8,})"')
KR_BRACKET_QUOTE_RE = re.compile(r"「([^」]{8,})」")

# (d) dates -----------------------------------------------------------------
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
YEAR_MONTH_RE = re.compile(r"\b\d{4}-\d{2}\b")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

# (e) proper nouns ----------------------------------------------------------
# A "proper-noun candidate" is an ALL-or-Mixed-case alpha-numeric token of
# length >= 3. Pure-uppercase 2-letter acronyms (AI, ML) are too noisy to
# whitelist by hand, so we drop length-2 tokens.
PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}(?:[-./][A-Za-z0-9]+)*\b")

# Stopword list - common English / programming nouns we always allow.
STOPWORDS = {
    "API", "APIs", "CLI", "CPU", "GPU", "RAM", "SSD", "URL", "URLs", "JSON",
    "YAML", "HTML", "CSS", "SQL", "NoSQL", "REST", "GraphQL", "TCP", "UDP",
    "HTTP", "HTTPS", "DNS", "TLS", "SSL", "OS", "VM", "VMs", "DB", "OS",
    "TODO", "FIXME", "OK", "PASS", "BLOCKED", "WARNING", "ERROR", "INFO",
    "DEBUG", "AI", "ML", "IO", "ID", "UI", "UX", "PR", "QA", "RFC", "WIP",
    "NOTE", "TIP", "Q", "A", "I", "Hello", "World", "Yes", "No",
}


def find_numbers(text: str) -> list[str]:
    """All number-like tokens, in document order, no de-dup."""
    out: list[tuple[int, str]] = []
    seen_spans: set[tuple[int, int]] = set()

    def add(match):
        span = (match.start(), match.end())
        if span in seen_spans:
            return
        seen_spans.add(span)
        out.append((match.start(), match.group(0)))

    # 1. percent
    for m in NUMBER_PERCENT_RE.finditer(text):
        add(m)
    # 2. currency
    for m in CURRENCY_RE.finditer(text):
        add(m)
    # 3. plain numbers (don't double-count if already covered)
    for m in NUMBER_PLAIN_RE.finditer(text):
        s, e = m.start(), m.end()
        # skip if overlaps with a percent / currency span
        overlaps = any(s < ee and e > ss for (ss, ee) in seen_spans)
        if overlaps:
            continue
        add(m)

    out.sort(key=lambda p: p[0])
    return [s for _, s in out]


def find_semver(text: str) -> list[str]:
    return [m.group(0) for m in SEMVER_RE.finditer(text)]


def find_quotes(text: str) -> list[str]:
    out: list[str] = []
    for m in DOUBLE_QUOTE_RE.finditer(text):
        out.append(m.group(1))
    for m in KR_BRACKET_QUOTE_RE.finditer(text):
        out.append(m.group(1))
    return out


def find_dates(text: str) -> list[str]:
    out: list[str] = []
    consumed_spans: list[tuple[int, int]] = []

    def add_unless_overlap(match):
        s, e = match.start(), match.end()
        for ss, ee in consumed_spans:
            if s < ee and e > ss:
                return
        consumed_spans.append((s, e))
        out.append(match.group(0))

    for m in ISO_DATE_RE.finditer(text):
        add_unless_overlap(m)
    for m in YEAR_MONTH_RE.finditer(text):
        add_unless_overlap(m)
    for m in YEAR_RE.finditer(text):
        add_unless_overlap(m)
    return out


def find_proper_nouns(text: str) -> list[str]:
    out: list[str] = []
    for m in PROPER_NOUN_RE.finditer(text):
        token = m.group(0)
        if token in STOPWORDS:
            continue
        # heading / list markers (e.g., "Sprint" at line start) do not get
        # whitelisted unless meaningful. We keep them; user yaml is the
        # authoritative whitelist.
        out.append(token)
    return out


def extract_all(text: str) -> dict[str, list[str]]:
    return {
        "numbers": find_numbers(text),
        "semver": find_semver(text),
        "quotes": find_quotes(text),
        "dates": find_dates(text),
        "proper_nouns": find_proper_nouns(text),
    }


__all__ = [
    "find_numbers",
    "find_semver",
    "find_quotes",
    "find_dates",
    "find_proper_nouns",
    "extract_all",
]
