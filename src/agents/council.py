"""Layer 3 — Council Voting: RiskOfficer (veto) + MomentumTrader."""

from __future__ import annotations

import asyncio
import json
import os
from typing import List

from google import genai
from google.genai import types

from src.models import CouncilVote, MarketSignal, TradeProposal
from src import logger


_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-3.8-flash"

_RISK_OFFICER_SYSTEM = """You are a Risk Officer on a crypto trading council.
Your role is to veto trades that are too risky.
AUTO-VETO rules (return approved=false):
  - amount_usd > 5.0
  - RSI > 75 for a BUY
  - sentiment_score < -0.5 for a BUY
  - RSI < 25 for a SELL
Return ONLY valid JSON:
{
  "approved": <true|false>,
  "confidence": <float 0.0 to 1.0>,
  "reason": "<one sentence>"
}"""

_MOMENTUM_TRADER_SYSTEM = """You are a Momentum Trader on a crypto trading council.
You approve trades that align with current momentum signals.
Consider: RSI trend, volume strength, sentiment direction.
Return ONLY valid JSON:
{
  "approved": <true|false>,
  "confidence": <float 0.0 to 1.0>,
  "reason": "<one sentence>"
}"""


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _build_vote_prompt(signal: MarketSignal, proposal: TradeProposal) -> str:
    return (
        f"Trade Proposal:\n"
        f"  Action: {proposal.action}\n"
        f"  Pair: {proposal.from_token} -> {proposal.to_token}\n"
        f"  Amount: ${proposal.amount_usd:.2f}\n"
        f"  Rationale: {proposal.rationale}\n\n"
        f"Market Signal:\n"
        f"  Token: {signal.token}\n"
        f"  RSI: {signal.rsi}\n"
        f"  24h Volume: {signal.volume_24h:,.0f} USD\n"
        f"  Sentiment Score: {signal.sentiment_score:.2f}\n"
        f"  Analysis: {signal.summary}"
    )


async def _ask_gemini(system: str, prompt: str) -> dict:
    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return json.loads(_strip_fences(response.text.strip()))


async def _risk_officer_vote(signal: MarketSignal, proposal: TradeProposal) -> CouncilVote:
    data = await _ask_gemini(_RISK_OFFICER_SYSTEM, _build_vote_prompt(signal, proposal))
    return CouncilVote(agent_name="RiskOfficer", **data)


async def _momentum_trader_vote(signal: MarketSignal, proposal: TradeProposal) -> CouncilVote:
    data = await _ask_gemini(_MOMENTUM_TRADER_SYSTEM, _build_vote_prompt(signal, proposal))
    return CouncilVote(agent_name="MomentumTrader", **data)


async def run_council_vote(
    signal: MarketSignal, proposal: TradeProposal
) -> tuple[List[CouncilVote], bool]:
    """Run both council votes concurrently and evaluate consensus."""
    logger.section("Layer 3 — Council Vote")

    risk_vote, momentum_vote = await asyncio.gather(
        _risk_officer_vote(signal, proposal),
        _momentum_trader_vote(signal, proposal),
    )

    votes = [risk_vote, momentum_vote]

    logger.subsection("Voting Results")
    for v in votes:
        logger.vote_line(v.agent_name, v.approved, v.confidence, v.reason)

    risk_approved = risk_vote.approved
    approval_rate = sum(v.approved for v in votes) / len(votes)
    consensus = risk_approved and approval_rate >= 0.70

    logger.log(
        "Council",
        f"RiskOfficer={'APPROVED' if risk_approved else 'VETOED'} | "
        f"Approval rate={approval_rate:.0%} | "
        f"Consensus={'YES' if consensus else 'NO'}",
    )

    return votes, consensus
