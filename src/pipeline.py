"""Orchestrates the full CouncilTrade pipeline for a single market scenario."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from src.agents.signal_agents import gather_signals
from src.agents.strategist import run_strategist
from src.agents.council import run_council_vote
from src.models import FinalDecision
from src import logger

DECISION_PATH = Path("data/latest_decision.json")


async def run_pipeline(raw_scenario: dict) -> FinalDecision:
    logger.section(f"CouncilTrade — {raw_scenario.get('name', raw_scenario['token'])}")

    # Layer 1: gather signals concurrently
    signal = await gather_signals(raw_scenario)

    # Layer 2: strategist produces a proposal
    proposal = await run_strategist(signal)

    # Layer 3: council votes
    votes, consensus = await run_council_vote(signal, proposal)

    status = "PENDING_EXECUTION" if consensus else "REJECTED"

    decision = FinalDecision(
        proposal=proposal,
        votes=votes,
        consensus_reached=consensus,
        timestamp=datetime.now(timezone.utc),
        status=status,
    )

    _write_decision(decision)
    logger.decision_banner(status, consensus)

    return decision


def _write_decision(decision: FinalDecision) -> None:
    DECISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_PATH, "w") as f:
        json.dump(decision.model_dump(mode="json"), f, indent=2, default=str)
    logger.log("UIBridge", f"Decision written to {DECISION_PATH}")
