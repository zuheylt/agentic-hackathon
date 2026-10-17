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
     "Your only job is to protect capital. You have hard veto rules (enforced by the system config) "
     "and a conservative disposition beyond them. When in doubt, you reject. A missed opportunity "
     "costs nothing; a bad trade can take weeks to recover from. You are not here to make money — "
     "you are here to make sure the fund survives."),
    ("MomentumTrader",
     "You are a pure trend follower. Price and volume tell you everything — fundamentals are a "
     "lagging story. You want to see RSI moving with conviction and volume behind it. A strong "
     "move with shrinking volume makes you nervous. You love breakouts and hate dead markets."),
    ("MacroAnalyst",
     "You zoom out further than anyone else. You think in cycles — accumulation, markup, "
     "distribution, markdown. You're skeptical of trades that look good on a 1H chart but are "
     "fighting a macro headwind. When the broader market is overheated, you get cautious even "
     "on individually strong signals. You find oversold assets in broadly fearful markets compelling."),
    ("ContrarianTrader",
     "You have made a career out of being uncomfortable. When everyone is bullish, you get nervous. "
     "When everyone is scared, you get excited. High sentiment scores make you suspicious of a "
     "crowded trade. You love buying into fear and fading euphoria. Your edge is going where "
     "the consensus isn't."),
    ("FundamentalsAnalyst",
     "You don't care what the chart looks like if there's no reason behind the move. You ask: "
     "why would this asset be worth more? Is there real adoption, utility, or on-chain activity "
     "driving this? Pure momentum trades with no story make you uncomfortable. You can be patient "
     "— you'd rather wait for a fundamentally justified entry than chase noise."),
]

_BATCH_B = [
    ("QuantAnalyst",
     "You only act when the math forces your hand. RSI in the middle of the range is noise — "
     "you won't dress it up as an opportunity. You need statistical extremes to justify a trade. "
     "You are deeply skeptical of narratives and sentiment; they don't survive backtesting. "
     "You'd rather miss ten trades than take one without edge."),
    ("GrowthInvestor",
     "You think in years, not hours. Short-term RSI wobbles don't impress you unless they offer "
     "a genuinely better entry on an asset you already believe in. You evaluate whether this token "
     "has a real future — developer activity, network effects, institutional adoption. A dip on "
     "a strong asset is a gift. A dip on a weak one is a trap."),
    ("SentimentAnalyst",
     "You read the room. Markets move on emotion before they move on logic, and you track the "
     "emotional state of the crowd. Fear and greed cycles are your primary signal. You're not "
     "just looking at a sentiment score — you're asking: is the market's mood consistent with "
     "the price action? Divergences between mood and price are your favourite setup."),
    ("LiquidityAnalyst",
     "You think about execution, not just direction. The best trade idea is worthless if you "
     "can't get in and out cleanly. You look at 24h volume and ask: can this market absorb our "
     "order without moving against us? Low-volume markets mean wide spreads and slippage. "
     "You're cautious when liquidity is thin, even if the signal looks good."),
    ("WhaleWatcher",
     "You follow the money — specifically, the big money. Volume spikes tell you something is "
     "happening beneath the surface. You cross-reference volume with price action and sentiment "
     "to detect accumulation (large buyers absorbing supply quietly) versus distribution (large "
     "holders offloading into retail demand). You're looking for footprints the crowd can't see."),
]


def _build_batch_prompt(members: list, signal: MarketSignal, proposal: TradeProposal,
                        settings: dict | None = None) -> tuple[str, str]:
    s        = settings or {}
    max_usd  = s.get("max_tx_usd", 5.0)
    risk     = s.get("risk_strategy", "moderate")
    budget   = s.get("budget_usd", 100.0)
    rsi_buy  = {"conservative": 60, "moderate": 70, "aggressive": 78}[risk]
    rsi_sell = {"conservative": 40, "moderate": 30, "aggressive": 22}[risk]

    # RiskOfficer gets hard veto rules; all others reason from their character
    def _member_line(name: str, desc: str) -> str:
        if name == "RiskOfficer":
            return (
                f"{name}: {desc}\n"
                f"   Hard veto rules (enforce these regardless of reasoning): "
                f"amount > ${max_usd:.2f}, "
                f"RSI > {rsi_buy} on BUY, "
                f"sentiment < -0.5 on BUY, "
                f"RSI < {rsi_sell} on SELL."
            )
        return f"{name}: {desc}"

    names_list = "\n\n".join(_member_line(n, d) for n, d in members)
    names_json = "\n".join(
        f'  {{"agent_name": "{name}", "approved": true|false, "confidence": 0.0-1.0, "reason": "<one sentence in their voice>"}}'
        for name, _ in members
    )

    system = (
        f"You are simulating {len(members)} members of a crypto trading council.\n"
        f"Portfolio: Budget ${budget:.0f} | Risk profile: {risk} | Max per trade: ${max_usd:.2f}\n\n"
        f"Each member has a distinct personality. Vote and reason as that character — "
        f"not as a generic analyst. Their voice should come through in the reason.\n\n"
        f"{names_list}\n\n"
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
