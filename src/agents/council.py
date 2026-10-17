"""Layer 3 — 10-member Council Vote (2 parallel batches of 5)."""

from __future__ import annotations

import asyncio
import json
import os
from typing import List

from google import genai
from google.genai import types

from src.agents._utils import strip_fences
from src.models import CouncilVote, MarketSignal, TradeProposal
from src import logger


_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-flash-lite-latest"

_BATCH_A = [
    ("RiskOfficer",
     "Auto-reject if: amount exceeds max, RSI too high on BUY, sentiment < -0.5 on BUY, RSI too low on SELL. Capital preservation first."),
    ("MomentumTrader",
     "Approve when RSI trend and volume confirm the move. High RSI + high volume = strong BUY signal."),
    ("MacroAnalyst",
     "Cautious in overheated markets. Bearish when signals look extended, bullish in oversold macro contexts."),
    ("ContrarianTrader",
     "Fades euphoria (high sentiment + high RSI = suspicious). Approves when the crowd seems wrong."),
    ("FundamentalsAnalyst",
     "Needs a reason beyond momentum. Skeptical of trades driven purely by sentiment."),
]

_BATCH_B = [
    ("QuantAnalyst",
     "RSI 40-60 = no statistical edge (lean reject). RSI < 35 = oversold BUY edge. RSI > 65 = overbought SELL edge. Volume must confirm."),
    ("GrowthInvestor",
     "Bullish on dips in strong tokens. Ignores short-term noise, focuses on long-term utility."),
    ("SentimentAnalyst",
     "Sentiment > 0.5 supports BUY. Sentiment < -0.3 supports caution. Near 0 = reduce confidence."),
    ("LiquidityAnalyst",
     "High 24h volume = clean execution, approve confidently. Low volume = slippage risk, be skeptical."),
    ("WhaleWatcher",
     "High vol + positive sentiment = institutional accumulation (bullish). High vol + negative = distribution (bearish)."),
]


def _build_batch_prompt(members: list, signal: MarketSignal, proposal: TradeProposal,
                        settings: dict | None = None) -> tuple[str, str]:
    s = settings or {}
    max_usd  = s.get("max_tx_usd", 5.0)
    risk     = s.get("risk_strategy", "moderate")
    budget   = s.get("budget_usd", 100.0)
    rsi_buy  = {"conservative": 60, "moderate": 70, "aggressive": 78}[risk]
    rsi_sell = {"conservative": 40, "moderate": 30, "aggressive": 22}[risk]

    names_list = "\n".join(f"{i+1}. {name}: {desc}" for i, (name, desc) in enumerate(members))
    names_json = "\n".join(
        f'  {{"agent_name": "{name}", "approved": true|false, "confidence": 0.0-1.0, "reason": "<one sentence>"}}'
        for name, _ in members
    )

    system = (
        f"You are simulating {len(members)} crypto trading council members.\n"
        f"Council config: Budget ${budget:.0f} | Risk: {risk} | Max/trade: ${max_usd:.2f} | "
        f"RSI BUY limit: {rsi_buy} | RSI SELL floor: {rsi_sell}\n\n"
        f"Members and their rules:\n{names_list}\n\n"
        f"Return ONLY a JSON array with exactly {len(members)} objects in the same order:\n"
        f"[\n{names_json}\n]\nReturn ONLY the JSON array. No markdown fences."
    )
    user = (
        f"Proposal: {proposal.action} {proposal.from_token}->{proposal.to_token} ${proposal.amount_usd:.2f}\n"
        f"Rationale: {proposal.rationale}\n"
        f"RSI: {signal.rsi} | Volume: ${signal.volume_24h:,.0f} | Sentiment: {signal.sentiment_score:.2f}\n"
        f"Analysis: {signal.summary}"
    )
    return system, user


async def _run_batch(members: list, signal: MarketSignal, proposal: TradeProposal,
                     settings: dict | None = None) -> List[CouncilVote]:
    system, user = _build_batch_prompt(members, signal, proposal, settings)
    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=user,
        config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=600),
    )
    return [CouncilVote(**v) for v in json.loads(strip_fences(response.text))]


async def run_council_vote(
    signal: MarketSignal,
    proposal: TradeProposal,
    settings: dict | None = None,
) -> tuple[List[CouncilVote], bool]:
    logger.section("Layer 3 — Council Vote (2 parallel batches)")

    batch_a, batch_b = await asyncio.gather(
        _run_batch(_BATCH_A, signal, proposal, settings),
        _run_batch(_BATCH_B, signal, proposal, settings),
    )
    votes: List[CouncilVote] = batch_a + batch_b

    logger.subsection("Voting Results")
    for v in votes:
        logger.vote_line(v.agent_name, v.approved, v.confidence, v.reason)

    risk_vote      = next(v for v in votes if v.agent_name == "RiskOfficer")
    risk_approved  = risk_vote.approved
    approved_count = sum(v.approved for v in votes)
    approval_rate  = approved_count / len(votes)
    consensus      = risk_approved and approval_rate >= 0.70

    logger.log(
        "Council",
        f"Result: {approved_count}/{len(votes)} approved | "
        f"RiskOfficer={'✓' if risk_approved else 'VETOED'} | "
        f"Rate={approval_rate:.0%} | Consensus={'YES' if consensus else 'NO'}",
    )
    return votes, consensus
