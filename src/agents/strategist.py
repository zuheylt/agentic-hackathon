"""Layer 2 — Strategist Agent synthesizes signals into a TradeProposal."""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types

from src.agents._utils import strip_fences
from src.models import MarketSignal, TradeProposal
from src import logger


_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-flash-lite-latest"


def _build_system(settings: dict) -> str:
    max_usd = settings.get("max_tx_usd", 5.0)
    risk = settings.get("risk_strategy", "moderate")
    budget = settings.get("budget_usd", 100.0)

    size_guidance = {
        "conservative": f"Use 50-70% of max (${max_usd * 0.6:.2f}) unless the signal is very strong.",
        "moderate":     f"Use 70-90% of max (${max_usd * 0.8:.2f}) when signal is clear.",
        "aggressive":   f"Use the full max (${max_usd:.2f}) when signal is strong.",
    }[risk]

    return f"""You are a crypto trading strategist.
Given a market signal, produce a concrete trade proposal.
amount_usd must be between $1.00 and ${max_usd:.2f}.
Total portfolio budget: ${budget:.2f}. Risk strategy: {risk}.
Position sizing guidance: {size_guidance}
Return ONLY valid JSON:
{{
  "action": "<BUY|SELL|HOLD>",
  "from_token": "<token or USD>",
  "to_token": "<token or USD>",
  "amount_usd": <float 1.0 to {max_usd:.2f}>,
  "rationale": "<one clear sentence explaining the trade>"
}}
Rules:
- BUY: from_token = "USD", to_token = signal token
- SELL: from_token = signal token, to_token = "USD"
- HOLD: from_token and to_token both equal signal token, amount_usd = 0"""


async def run_strategist(signal: MarketSignal, settings: dict | None = None) -> TradeProposal:
    logger.section("Layer 2 — Strategist")
    logger.log("Strategist", f"Synthesizing proposal for {signal.token}...")

    system = _build_system(settings or {})
    prompt = (
        f"Token: {signal.token}\n"
        f"RSI: {signal.rsi}\n"
        f"24h Volume: {signal.volume_24h:,.0f} USD\n"
        f"Sentiment Score: {signal.sentiment_score:.2f}\n"
        f"Analysis: {signal.summary}"
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=300,
        ),
    )

    data = json.loads(strip_fences(response.text))
    proposal = TradeProposal(**data)
    logger.result(
        "Strategist",
        f"{proposal.action} {proposal.from_token} -> {proposal.to_token} @ ${proposal.amount_usd:.2f}",
    )
    logger.log("Strategist", f"Rationale: {proposal.rationale}")
    return proposal
