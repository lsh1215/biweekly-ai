"""TDD: fact-checker 5 hard-evidence type regex (PRD §3 D3).

Patterns:
  (a) numbers: \\b\\d+(\\.\\d+)?\\b, \\b\\d+(\\.\\d+)?%\\b, [\\$₩€]\\d+...
  (b) semver:  \\bv?\\d+\\.\\d+\\.\\d+([.-][a-z0-9]+)*\\b
  (c) direct quote: "..." or 「...」 (≥ 8 chars inside)
  (d) date: \\b\\d{4}\\b, \\d{4}-\\d{2}, \\d{4}-\\d{2}-\\d{2}
  (e) proper noun: any non-yaml-listed token that scrutinizes a known proper-noun
      pattern (caps + alphanum, length ≥ 3, not a common English stopword).

The unit tests cover regex behavior only - pure pattern matching, no yaml diff.
"""
from __future__ import annotations

import importlib

import pytest

mod = importlib.import_module("fact_checker_patterns")


class TestNumbers:
    def test_integer(self):
        hits = mod.find_numbers("매월 처리량은 1,200,000 건이다")
        assert any("1,200,000" in h or "1200000" in h or h in {"1", "200", "000"} for h in hits)

    def test_decimal(self):
        hits = mod.find_numbers("p99 latency 47.5 ms")
        assert "47.5" in hits

    def test_percent(self):
        hits = mod.find_numbers("중복률 0.03%")
        assert "0.03%" in hits

    def test_currency(self):
        hits = mod.find_numbers("월 4500만 원 손실, $1.5M, ₩1000, €99")
        assert any("$1.5M" in h for h in hits)
        assert any("₩1000" in h for h in hits)
        assert any("€99" in h for h in hits)


class TestSemver:
    def test_basic(self):
        hits = mod.find_semver("Resilience4j 2.2.0 사용")
        assert "2.2.0" in hits

    def test_v_prefix(self):
        hits = mod.find_semver("v1.4.2-rc1 출시")
        assert any(h in {"v1.4.2-rc1", "v1.4.2"} for h in hits)

    def test_no_match_two_part(self):
        hits = mod.find_semver("Python 3.13 환경")
        assert hits == []  # 3.13 is two-part, not semver


class TestDirectQuote:
    def test_double_quoted(self):
        hits = mod.find_quotes('그는 "근거 먼저 묻기"라고 말했다')
        assert "근거 먼저 묻기" in hits

    def test_kr_bracket_quoted(self):
        hits = mod.find_quotes("「측정 없이 결론 없다」 원칙")
        assert "측정 없이 결론 없다" in hits

    def test_short_skipped(self):
        hits = mod.find_quotes('"hi" is too short')
        assert "hi" not in hits  # ≥ 8 char rule


class TestDates:
    def test_year(self):
        hits = mod.find_dates("2026 회고")
        assert "2026" in hits

    def test_year_month(self):
        hits = mod.find_dates("배포는 2025-10 진행")
        assert "2025-10" in hits

    def test_iso_full(self):
        hits = mod.find_dates("2026-04-28 결과")
        assert "2026-04-28" in hits


class TestProperNouns:
    def test_picks_caps_words(self):
        hits = mod.find_proper_nouns("PostgreSQL 와 PyTorch 비교")
        assert "PostgreSQL" in hits
        assert "PyTorch" in hits

    def test_skips_short_caps(self):
        hits = mod.find_proper_nouns("AI 와 ML 의 차이")
        # AI / ML are < 3 chars; we skip - reduces noise
        # at minimum no crash. Some implementations might keep them.
        # Spec says length >= 3.
        assert "AI" not in hits
        assert "ML" not in hits


class TestExtractAll:
    def test_returns_dict_with_5_keys(self):
        result = mod.extract_all('데이터: PostgreSQL 15.2 출시는 2025-10 이며 처리량은 1500건/s, 중복률 0.03%, 「측정 없이 결론 없다」.')
        assert set(result.keys()) == {"numbers", "semver", "quotes", "dates", "proper_nouns"}
        assert "0.03%" in result["numbers"]
        assert "15.2" not in result["semver"]  # two-part, not semver
        assert "2025-10" in result["dates"]
        assert "측정 없이 결론 없다" in result["quotes"]
        assert "PostgreSQL" in result["proper_nouns"]
