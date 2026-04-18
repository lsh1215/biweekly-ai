"""RIA CLI entry points (Sprint 2+).

Commands:
    ria healthcheck     --portfolio <yaml> [--as-of <YYYY-MM-DD>]
                        [--replay <json>] --out <dir>
    ria process-events  --queue <dir> --portfolio <yaml> --out <dir>
                        [--replay-dir <dir>]

Replay mode: when ``ANTHROPIC_API_KEY`` is unset, ``process-events`` falls
back to ``tests/fixtures/replay/events/`` (classify + interrupt fixtures)
so the overnight pipeline keeps running without a live key.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import typer
import yaml

from ria.agent.event_loop import EventLoopReport, process_all
from ria.agent.loop import LoopResult, run_agent
from ria.fixtures import DEFAULT_FIXTURE_ROOT, load_prices
from ria.models import Portfolio
from ria.tools.classify import ClassifierResult, classify_severity

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


_INTERRUPT_PROMPT_PATH = (
    Path(__file__).resolve().parent / "agent" / "prompts" / "interrupt.md"
)
_DEFAULT_EVENTS_REPLAY_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "replay" / "events"
)
INTERRUPT_MAX_ITERATIONS = 10


def _interrupt_system_prompt() -> str:
    return _INTERRUPT_PROMPT_PATH.read_text()


def _summarize_event(event, portfolio: Portfolio, classification: ClassifierResult) -> str:
    holdings = ", ".join(f"{p.ticker}({p.quantity})" for p in portfolio.positions)
    return (
        f"이벤트 ID: {event.event_id}\n"
        f"발생: {event.ts_utc.isoformat()}  source={event.source_type}\n"
        f"영향 ticker(추정): {event.expected_affected_tickers}\n"
        f"보유 포트폴리오: {holdings}, cash=${portfolio.cash_usd:.2f}\n"
        f"Severity: {classification.severity} — {classification.rationale}\n\n"
        f"원문 요약:\n---\n{event.raw_text}\n---\n\n"
        "위 P0 이벤트에 대해 interrupt 리포트를 1개 작성하세요. "
        "title 첫 문장에 action verb, citations ≥ 1 (가능하면 2), "
        "emit_report 1회. 신속하게 결정하세요."
    )


def _interrupt_agent_runner_factory(replay_dir: Path | None):
    """Return a callable suitable for ``process_all(agent_runner=...)``."""
    def runner(event, portfolio: Portfolio, out_dir: Path, classification):
        as_of_date = event.ts_utc.date()
        tools = _build_tools(out_dir=out_dir, as_of=as_of_date)
        # interrupt reports use a different filename convention — wrap emit
        existing_emit = tools["emit_report"]

        def _emit(**kw):
            from ria.tools.emit_report import emit_report
            kw.pop("out_dir", None)
            kw.pop("as_of", None)
            kw.pop("kind", None)
            kw.pop("severity", None)
            kw.pop("ticker", None)
            ticker = (
                event.expected_affected_tickers[0]
                if event.expected_affected_tickers
                else "PORT"
            )
            path = emit_report(
                out_dir=out_dir,
                as_of=as_of_date,
                kind="interrupt",
                severity=classification.severity,
                ticker=ticker,
                **kw,
            )
            return str(path)

        tools["emit_report"] = _emit

        replay_path: Path | None = None
        if replay_dir is not None:
            candidate = replay_dir / "interrupt" / f"{event.event_id}.json"
            if candidate.exists():
                replay_path = candidate

        user_msg = _summarize_event(event, portfolio, classification)
        system_prompt = _interrupt_system_prompt()
        result = run_agent(
            system_prompt,
            user_msg,
            replay_path=replay_path,
            tools=tools,
            max_iterations=INTERRUPT_MAX_ITERATIONS,
        )
        return result.report_path

    return runner


def _classify_fn_factory(replay_dir: Path | None):
    classify_replay = (replay_dir / "classify") if replay_dir is not None else None

    def fn(event, portfolio):
        return classify_severity(event, portfolio, replay_dir=classify_replay)
    return fn


@app.command(name="process-events")
def process_events(
    queue: Path = typer.Option(..., "--queue", help="Directory of synthetic event JSON files"),
    portfolio: Path = typer.Option(..., "--portfolio", help="YAML portfolio file"),
    out: Path = typer.Option(..., "--out", help="Where interrupt reports are written"),
    replay_dir: Optional[Path] = typer.Option(
        None,
        "--replay-dir",
        help="Use replay fixtures (subdirs `classify/` and `interrupt/`). "
             "Auto-defaults to tests/fixtures/replay/events/ when ANTHROPIC_API_KEY is unset.",
    ),
) -> None:
    """Drain an event queue, gating P0 → interrupt; P1/P2 → deferred journal."""
    pf = Portfolio(**yaml.safe_load(portfolio.read_text()))
    out.mkdir(parents=True, exist_ok=True)

    if replay_dir is None and not os.environ.get("ANTHROPIC_API_KEY"):
        if _DEFAULT_EVENTS_REPLAY_DIR.exists():
            replay_dir = _DEFAULT_EVENTS_REPLAY_DIR
            typer.echo(
                f"[process-events] ANTHROPIC_API_KEY unset — falling back to replay_dir={replay_dir}",
                err=True,
            )

    classify_fn = _classify_fn_factory(replay_dir)
    agent_runner = _interrupt_agent_runner_factory(replay_dir)

    from ria.db.conn import connect, ensure_schema
    conn = connect()
    try:
        ensure_schema(conn)
        report: EventLoopReport = process_all(
            queue_dir=queue,
            portfolio=pf,
            out_dir=out,
            db_conn=conn,
            classify_fn=classify_fn,
            agent_runner=agent_runner,
        )
    finally:
        conn.close()

    counts: dict[str, int] = {}
    for d in report.decisions:
        counts[d.cycle_type] = counts.get(d.cycle_type, 0) + 1
    typer.echo(f"events processed: {len(report.decisions)}")
    for k in sorted(counts):
        typer.echo(f"  {k}: {counts[k]}")
    for d in report.decisions:
        if d.report_path:
            typer.echo(f"  report: {d.report_path}")


if __name__ == "__main__":  # pragma: no cover
    app()
