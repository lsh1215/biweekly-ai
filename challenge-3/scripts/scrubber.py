"""Deterministic scrubber implementation (LLM-free pipeline path).

The aiwriting-scrubber agent runs in the live plugin via Claude. For the
16-fixture deterministic pipeline, we do not call Claude - we apply the same
R1-R7 grep + substitution catalog from `aiwriting/skills/blog/ai-tell-rules.md`
in pure Python so the pipeline is reproducible byte-for-byte.

Substitutions are conservative: we only patch patterns the catalog explicitly
covers with a 1:1 substitution. Anything else is left alone but counted as a
residual for the copy-killer R1_R7 indicator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import copy_killer_metrics as km

ROOT = Path(__file__).resolve().parent.parent

# 1:1 substitutions from ai-tell-rules.md catalog tables.
SUBSTITUTIONS = [
    # 본문 의인화 카탈로그
    ("Payment 는 여전히 죽어 있다", "Payment 는 여전히 기동되지 않았다"),
    ("신경 쓰지 않는다", "영향을 받지 않는다"),
    ("헬스체크까지 죽었다", "헬스체크까지 응답을 멈췄다"),
    ("운명을 공유", "같은 트랜잭션에 묶여서"),
    ("무관한 API 도 함께 죽는다", "무관한 API 도 함께 응답을 멈춘다"),
    # drama 동사
    ("결제가 증발했다", "결제 이벤트가 사라졌다"),
    ("힙과 함께 증발한다", "힙과 함께 사라진다"),
    ("지연이 악질인 이유", "지연이 위험한 이유"),
    # generic drama
    ("증발했다", "사라졌다"),
    ("증발한다", "사라진다"),
]

# 금기 표현 카탈로그 (general 1:1)
BANNED_TOKEN_SUBS = [
    ("을 통하여", "으로"),
    ("를 통하여", "로"),
    ("함으로써", "해서"),
    ("매우 ", ""),
    ("정말로 ", ""),
    ("실제로 ", ""),
    ("굉장히 ", ""),
    ("제공합니다", "있습니다"),
    ("존재합니다", "있습니다"),
    ("활용하여", "써서"),
]

# Format-specific extra bans.
FORMAT_BANS: dict[str, list[str]] = {
    "blog": [],
    "cover-letter": [
        "최선을 다",
        "꾸준히",
        "열정",
        "시너지",
        "글로벌",
        "긴 글 읽어주셔서 감사",
        "잘 부탁드립니다",
    ],
    "paper": [
        "이 논문에서는 ~할 것이다",
        "을 다룰 예정",
    ],
    "letter": [
        "최선을 다",
        "꾸준히",
        "시너지",
    ],
}

# R7 em-dash / en-dash replacement
DASH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s—\s"), " - "),
    (re.compile(r"\s–\s"), " - "),
    (re.compile(r"—"), "-"),
    (re.compile(r"–"), "-"),
]


@dataclass
class ScrubReport:
    format: str
    applied: int  # number of 1:1 substitutions applied
    residual_matches: int  # remaining R1-R7 matches outside code blocks
    verdict: str  # "PASS" | "NEEDS_HUMAN_REVIEW" | "BLOCKED"
    notes: list[str]


def _split_code_blocks(text: str) -> list[tuple[bool, str]]:
    """Return list of (is_code_block, segment) chunks preserving order."""
    parts: list[tuple[bool, str]] = []
    pat = re.compile(r"(```.*?```)", re.DOTALL)
    last = 0
    for m in pat.finditer(text):
        if m.start() > last:
            parts.append((False, text[last:m.start()]))
        parts.append((True, m.group(0)))
        last = m.end()
    if last < len(text):
        parts.append((False, text[last:]))
    return parts


def _apply_to_prose(text: str, substitutions: list[tuple[str, str]]) -> tuple[str, int]:
    parts = _split_code_blocks(text)
    out_parts: list[str] = []
    count = 0
    for is_code, seg in parts:
        if is_code:
            out_parts.append(seg)
            continue
        for old, new in substitutions:
            occurrences = seg.count(old)
            if occurrences:
                count += occurrences
                seg = seg.replace(old, new)
        for pat, repl in DASH_PATTERNS:
            occurrences = len(pat.findall(seg))
            if occurrences:
                count += occurrences
                seg = pat.sub(repl, seg)
        out_parts.append(seg)
    return "".join(out_parts), count


def _format_ban_substitutions(fmt: str) -> list[tuple[str, str]]:
    return [(token, "") for token in FORMAT_BANS.get(fmt, [])]


def scrub(text: str, fmt: str) -> tuple[str, ScrubReport]:
    if fmt not in ("blog", "cover-letter", "paper", "letter"):
        raise ValueError(f"BAD_FORMAT: {fmt}")
    notes: list[str] = []
    subs = list(SUBSTITUTIONS) + list(BANNED_TOKEN_SUBS) + _format_ban_substitutions(fmt)
    out, applied = _apply_to_prose(text, subs)
    # Future-tense in summary section (blog/paper)
    if fmt in ("blog", "paper"):
        out, summary_count = _strip_summary_future_tense(out)
        applied += summary_count
        if summary_count:
            notes.append(f"summary future-tense markers stripped: {summary_count}")
    residual = _count_r1_r7_residual(out)
    if residual == 0:
        verdict = "PASS"
    elif residual <= 2:
        verdict = "NEEDS_HUMAN_REVIEW"
    else:
        verdict = "BLOCKED"
    return out, ScrubReport(
        format=fmt,
        applied=applied,
        residual_matches=residual,
        verdict=verdict,
        notes=notes,
    )


def _strip_summary_future_tense(text: str) -> tuple[str, int]:
    """Within a `## 요약` section, remove lines that contain future-tense markers."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_summary = False
    removed = 0
    pat = re.compile(r"Phase\s*[0-9]|다음 글|이후 [가-힣]|예정\.?$|곧 [가-힣]")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and stripped[3:].strip() in ("요약", "Conclusion", "결론"):
            in_summary = True
            out.append(line)
            continue
        if stripped.startswith("# ") or stripped.startswith("## "):
            in_summary = False
            out.append(line)
            continue
        if in_summary and pat.search(line):
            removed += 1
            continue
        out.append(line)
    return "".join(out), removed


def _count_r1_r7_residual(text: str) -> int:
    body = km.strip_code(text)
    count = 0
    for pat in km.R1_R7_PATTERNS:
        count += len(re.findall(pat, body, flags=re.MULTILINE))
    return count


def main() -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="markdown file")
    ap.add_argument("--format", required=True,
                    choices=("blog", "cover-letter", "paper", "letter"))
    ap.add_argument("--write", action="store_true",
                    help="overwrite the file with scrubbed content")
    ap.add_argument("--out", help="write scrubbed content to this path")
    args = ap.parse_args()

    text = Path(args.path).read_text()
    out_text, report = scrub(text, args.format)

    if args.write:
        Path(args.path).write_text(out_text)
    elif args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out_text)

    print(json.dumps({
        "format": report.format,
        "applied": report.applied,
        "residual_matches": report.residual_matches,
        "verdict": report.verdict,
        "notes": report.notes,
    }, ensure_ascii=False, indent=2))
    return 0 if report.verdict != "BLOCKED" else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
