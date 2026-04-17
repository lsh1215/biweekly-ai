"""RIA CLI entry points (Sprint 2+).

Commands:
    ria healthcheck --portfolio <yaml> [--as-of <YYYY-MM-DD>]
                    [--replay <json>] --out <dir>

The planner prompt lives in ``src/ria/agent/prompts/planner.md`` (read at
call time so test and production share one source). In replay mode no
Anthropic call is made — determinism is guaranteed by the committed fixture
plus deterministic tool fixtures on disk.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import typer
import yaml

from ria.agent.loop import LoopResult, run_agent
from ria.fixtures import DEFAULT_FIXTURE_ROOT, load_prices
from ria.models import Portfolio

app = typer.Typer(help="RIA — Reactive Investment Agent", no_args_is_help=True)


@app.callback()
def _main() -> None:
    """Root callback forces subcommand dispatch even with a single command."""
    # (keeps `python -m ria.cli healthcheck ...` working; Sprint 3 will add
    # more commands — no reshape needed.)
    pass


_PLANNER_PROMPT_PATH = (
    Path(__file__).resolve().parent / "agent" / "prompts" / "planner.md"
)


def _planner_system_prompt() -> str:
    return _PLANNER_PROMPT_PATH.read_text()


def _fixture_max_date(ticker: str = "AAPL") -> date:
    df = load_prices(ticker)
    if df.empty:
        raise RuntimeError(f"{ticker} price fixture is empty")
    return max(df["Date"])


def _summarize_portfolio(pf: Portfolio, as_of: date) -> str:
    lines = [f"기준일: {as_of.isoformat()}"]
    lines.append("포지션:")
    for p in pf.positions:
        lines.append(f"  - {p.ticker}: {p.quantity}주, cost basis ${p.cost_basis_usd:.2f}")
    lines.append(f"현금: ${pf.cash_usd:.2f}")
    weights = pf.weights()
    if weights:
        wtxt = ", ".join(f"{k}={v:.1%}" for k, v in weights.items())
        lines.append(f"가중치 (cost basis 기준): {wtxt}")
    lines.append(
        "위 포트폴리오에 대해 주간 헬스체크 리포트를 1개 생성하세요. "
        "title 첫 200자에 action verb 포함, citations ≥ 2, emit_report 1회."
    )
    return "\n".join(lines)


def _df_prices_to_json(df) -> list[dict]:
    out = []
    for _, row in df.iterrows():
        d = row.to_dict()
        if "Date" in d and hasattr(d["Date"], "isoformat"):
            d["Date"] = d["Date"].isoformat()
        out.append(d)
    return out


def _build_tools(out_dir: Path, as_of: date) -> dict[str, Callable]:
    """Return tool impls bound to the caller's output dir and as-of anchor."""
    from ria.tools.emit_report import emit_report
    from ria.tools.news import get_news
    from ria.tools.prices import get_prices

    def _prices(tickers: list[str], window_days: int) -> list[dict]:
        df = get_prices(tickers, window_days, as_of=as_of)
        return _df_prices_to_json(df)

    def _news(ticker: str, last_n_days: int) -> list[dict]:
        return list(get_news(ticker, last_n_days))

    def _rag(query: str, top_k: int = 5):
        # lazy import so replay mode without a live DB still runs
        try:
            from ria.tools.rag import rag_search
            return rag_search(query, top_k=top_k)
        except Exception as e:  # noqa: BLE001 — surfacing DB issues as tool-level error
            return {"error": f"rag_search unavailable: {e}"}

    def _emit(**kw):
        kw.pop("out_dir", None)
        kw.pop("as_of", None)
        path = emit_report(out_dir=out_dir, as_of=as_of, **kw)
        return str(path)

    return {
        "get_prices": _prices,
        "get_news": _news,
        "rag_search": _rag,
        "emit_report": _emit,
    }


@app.command()
def healthcheck(
    portfolio: Path = typer.Option(..., "--portfolio", help="YAML portfolio file"),
    as_of: Optional[str] = typer.Option(
        None,
        "--as-of",
        help="ISO date (YYYY-MM-DD). Default: max Date across price fixtures.",
    ),
    replay: Optional[Path] = typer.Option(
        None,
        "--replay",
        help="Replay a committed messages-exchange fixture (skips Anthropic call).",
    ),
    out: Path = typer.Option(Path("reports"), "--out", help="Report output dir"),
    record: Optional[Path] = typer.Option(
        None,
        "--record",
        help="When calling live, dump the exchange here for later replay.",
    ),
) -> None:
    """Run the weekly planned healthcheck and emit a Markdown report."""
    pf_data = yaml.safe_load(portfolio.read_text())
    pf = Portfolio(**pf_data)
    as_of_date = (
        date.fromisoformat(as_of)
        if as_of
        else _fixture_max_date()
    )
    out.mkdir(parents=True, exist_ok=True)

    tools = _build_tools(out_dir=out, as_of=as_of_date)
    user_msg = _summarize_portfolio(pf, as_of_date)
    system_prompt = _planner_system_prompt()

    result: LoopResult = run_agent(
        system_prompt,
        user_msg,
        replay_path=replay,
        tools=tools,
        record_path=record,
    )

    if result.report_path is None:
        typer.echo("ERROR: agent finished without emitting a report", err=True)
        raise typer.Exit(code=2)
    typer.echo(f"report: {result.report_path}")
    typer.echo(f"turns: {result.turns}, tool_calls: {len(result.tool_calls)}")


if __name__ == "__main__":  # pragma: no cover
    app()
