"""copy-killer 6 indicators (PRD §3 D6) — pure functions, LLM-free.

Each function takes plain markdown text (post-scrubber) and returns a float in [0, 1].
Higher score = stronger AI tell signal for that indicator.

Code blocks (``` fenced ``` and `inline`) are stripped before scoring so that
identifier names and shell flags do not skew the metrics.
"""
from __future__ import annotations

import re
import statistics

# --- text helpers ------------------------------------------------------------

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|(?<=다\.)\s+|(?<=요\.)\s+|(?<=음\.)\s+")
_HANGUL_RE = re.compile(r"[가-힣]")
_NONWS_RE = re.compile(r"\S")


def strip_code(text: str) -> str:
    text = _FENCE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    return text


def strip_headings(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def split_sentences(text: str) -> list[str]:
    body = strip_code(text)
    body = strip_headings(body)
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", body)
    sentences: list[str] = []
    for p in parts:
        p = p.strip()
        if p:
            sentences.append(p)
    return sentences


# --- 1. sentence_length_variance --------------------------------------------

def sentence_length_variance(text: str) -> float:
    """std/mean of sentence char length, mapped so uniform → 1, varied → 0."""
    sents = split_sentences(text)
    if len(sents) < 2:
        return 0.0
    lengths = [len(s) for s in sents]
    mean = statistics.mean(lengths)
    if mean == 0:
        return 0.0
    std = statistics.pstdev(lengths)
    cv = std / mean  # coefficient of variation
    # Empirical mapping: cv ~= 0.0 (very uniform) → 1.0;
    # cv >= 0.6 (well-varied human prose) → 0.0.
    score = 1.0 - min(cv / 0.6, 1.0)
    return max(0.0, min(1.0, score))


# --- 2. avg_syllable_length --------------------------------------------------

def avg_syllable_length(text: str) -> float:
    """Hangul syllable density per 100 chars, normalized to [0, 1].

    Despite the spec name, this measures fraction of body chars that are Hangul.
    Pure-Hangul → 1.0. Pure-English → 0.0.
    """
    body = strip_code(text)
    body = strip_headings(body)
    nonws = _NONWS_RE.findall(body)
    if not nonws:
        return 0.0
    hangul = _HANGUL_RE.findall(body)
    return len(hangul) / len(nonws)


# --- 3. connector_frequency --------------------------------------------------

_CONNECTORS = ("그러나", "하지만", "따라서", "즉", "또한")


def connector_frequency(text: str) -> float:
    """Connectors per 1000 chars, normalized.

    >= 12 connectors / 1000 chars → 1.0.
    """
    body = strip_code(text)
    body = strip_headings(body)
    chars = len(body)
    if chars == 0:
        return 0.0
    count = 0
    for c in _CONNECTORS:
        count += len(re.findall(rf"(?<![가-힣]){re.escape(c)}(?![가-힣])", body))
    per_1000 = count * 1000.0 / chars
    return max(0.0, min(1.0, per_1000 / 12.0))


# --- 4. r1_r7_residual ------------------------------------------------------

R1_R7_PATTERNS = [
    # R1.b body anthropomorphism
    r"신경 쓰지 않는다",
    r"운명을 공유",
    r"숨을 쉰다",
    r"숨을 쉽니다",
    r"더 정중한지",
    # R2 drama / 평가어
    r"증발",
    r"악질인 이유",
    # R3 meta-closing
    r"이게 [A-Za-z가-힣]* 다",
    r"한 일은 그뿐",
    r"이것이 [A-Za-z가-힣 ]*의 전부",
    r"^\*\*결론\.\*\*",
    # R4 thesis labels
    r"^\*\*Thesis\.\*\*",
    # R7 em-dash, en-dash
    r"—",
    r"–",
    # R6 future-tense markers in summary regions
    r"Phase\s*[0-9]",
    r"다음 글",
]


def r1_r7_residual(text: str) -> float:
    """Match count of R1~R7 patterns outside code blocks, normalized.

    >= 5 matches → 1.0.
    """
    body = strip_code(text)
    count = 0
    for pat in R1_R7_PATTERNS:
        count += len(re.findall(pat, body, flags=re.MULTILINE))
    return max(0.0, min(1.0, count / 5.0))


# --- 5. monotone_ending_ratio ----------------------------------------------

_ENDING_TOKEN_RE = re.compile(r"([다요음음니까죠임])([\.\!\?])\s*$")


def _ending_class(sent: str) -> str | None:
    s = sent.strip()
    if not s:
        return None
    # Last 1-3 hangul chars before terminal punct
    m = re.search(r"([가-힣]{1,3})\s*[\.\?\!]?\s*$", s)
    if not m:
        return None
    tail = m.group(1)
    # collapse to last char as the class proxy
    return tail[-1]


def monotone_ending_ratio(text: str) -> float:
    """4-or-more consecutive sentences with the same ending class / total sentences."""
    sents = split_sentences(text)
    n = len(sents)
    if n == 0:
        return 0.0
    classes = [_ending_class(s) for s in sents]
    runs = 0
    streak = 1
    last = classes[0]
    for c in classes[1:]:
        if c is not None and c == last:
            streak += 1
        else:
            if streak >= 4 and last is not None:
                runs += streak
            streak = 1
            last = c
    if streak >= 4 and last is not None:
        runs += streak
    score = runs / n
    return max(0.0, min(1.0, score))


# --- 6. generic_modifier_density --------------------------------------------

_GENERIC_MODIFIERS = ("매우", "정말", "너무", "굉장히")


def generic_modifier_density(text: str) -> float:
    """매우/정말/너무/굉장히 per 1000 chars, normalized.

    >= 10 / 1000 chars → 1.0.
    """
    body = strip_code(text)
    body = strip_headings(body)
    chars = len(body)
    if chars == 0:
        return 0.0
    count = 0
    for w in _GENERIC_MODIFIERS:
        count += len(re.findall(re.escape(w), body))
    per_1000 = count * 1000.0 / chars
    return max(0.0, min(1.0, per_1000 / 10.0))


# --- registry ---------------------------------------------------------------

METRIC_FUNCS = {
    "sentence_length_variance": sentence_length_variance,
    "avg_syllable_length": avg_syllable_length,
    "connector_frequency": connector_frequency,
    "r1_r7_residual": r1_r7_residual,
    "monotone_ending_ratio": monotone_ending_ratio,
    "generic_modifier_density": generic_modifier_density,
}
