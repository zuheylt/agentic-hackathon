"""Orchestrates the full CouncilTrade pipeline for a single market scenario."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.agents._utils import format_volume
from src.agents.signal_agents import gather_signals
from src.agents.strategist import run_strategist
from src.agents.council import run_council_vote
from src.models import FinalDecision, MarketSignal
from src import logger

DECISION_PATH = Path("data/latest_decision.json")
HISTORY_PATH  = Path("data/history.json")


async def run_pipeline(
    raw_scenario: dict,
    demo: bool = True,
    settings: dict | None = None,
    auto_execute: bool = False,
) -> FinalDecision:
    logger.section(f"CouncilTrade — {raw_scenario.get('name', raw_scenario['token'])}")

    signal   = await gather_signals(raw_scenario)
    proposal = await run_strategist(signal, settings=settings)
    votes, consensus = await run_council_vote(signal, proposal, settings=settings)

    status = "PENDING_EXECUTION" if consensus else "REJECTED"

    decision = FinalDecision(
        proposal=proposal,
        votes=votes,
        consensus_reached=consensus,
        timestamp=datetime.now(timezone.utc),
        status=status,
        signal=signal,
    )

    if consensus and auto_execute:
        from src.execution.executor import execute_trade
        decision = await execute_trade(decision, demo=demo)

    _write_decision(decision)
    _append_history(decision)
    logger.decision_banner(decision.status, consensus)

    return decision


async def run_live_pipeline(
    inst_id: str,
    demo: bool = True,
    settings: dict | None = None,
    auto_execute: bool = False,
) -> FinalDecision:
    from src.data.market_feed import fetch_market_raw
    raw = await fetch_market_raw(inst_id, demo=demo)
    return await run_pipeline(raw, demo=demo, settings=settings, auto_execute=auto_execute)


# ── UI bridge ────────────────────────────────────────────────────────────────

def _write_decision(decision: FinalDecision) -> None:
    DECISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_PATH, "w") as f:
        json.dump(_to_ui_dict(decision), f, indent=2, default=str)
    logger.log("UIBridge", f"Decision written to {DECISION_PATH}")


def _append_history(decision: FinalDecision) -> None:
    history: list = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            pass
    history.insert(0, _to_ui_dict(decision))
    HISTORY_PATH.write_text(json.dumps(history[:100], indent=2, default=str))


def _to_ui_dict(decision: FinalDecision) -> dict:
    signal = decision.signal
    risk     = next((v for v in decision.votes if v.agent_name == "RiskOfficer"), None)
    momentum = next((v for v in decision.votes if v.agent_name == "MomentumTrader"), None)

    approval_rate = sum(v.approved for v in decision.votes) / len(decision.votes) if decision.votes else 0.0

    prop  = decision.proposal
    token = prop.to_token if prop.action == "BUY" else prop.from_token

    rsi = signal.rsi if signal else 50.0
    if rsi >= 70:
        verdict = "BEARISH (Overbought)"
    elif rsi <= 30:
        verdict = "BULLISH (Oversold)"
    else:
        verdict = "NEUTRAL"

    vol     = signal.volume_24h if signal else 0.0
    vol_str = format_volume(vol)

    return {
        "timestamp": decision.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": decision.status,
        "technical": {
            "rsi": rsi,
            "volume_24h": vol_str,
            "verdict": verdict,
        },
        "sentiment": {
            "score": signal.sentiment_score if signal else 0.0,
            "summary": signal.summary if signal else "",
        },
        "proposal": {
            "action": prop.action,
            "token": token,
            "amount_usd": prop.amount_usd,
            "rationale": prop.rationale,
        },
        "council": {
            "risk_officer": {
                "status": "APPROVED" if risk and risk.approved else "REJECTED",
                "notes": risk.reason if risk else "",
            },
            "momentum_trader": {
                "status": "APPROVED" if momentum and momentum.approved else "REJECTED",
                "confidence": f"{momentum.confidence:.0%}" if momentum else "0%",
            },
            "votes": [
                {
                    "agent":      v.agent_name,
                    "status":     "APPROVED" if v.approved else "REJECTED",
                    "confidence": f"{v.confidence:.0%}",
                    "reason":     v.reason,
                }
                for v in decision.votes
            ],
            "consensus_passed":  decision.consensus_reached,
            "consensus_score":   f"{approval_rate:.0%}",
            "approved_count":    sum(v.approved for v in decision.votes),
            "total_count":       len(decision.votes),
        },
        "execution": {
            "order_id": decision.order_id or "—",
            "exchange": "OKX",
            "mode":     "Demo Trading",
            "okx_url":  f"https://www.okx.com/trade-spot/{token.lower()}-usdt",
        },
    }
