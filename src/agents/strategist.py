"""Layer 2 — Strategist Agent synthesizes signals into a TradeProposal."""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types

from src.models import MarketSignal, TradeProposal
from src import logger


_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-3.8-flash"

_STRATEGIST_SYSTEM = """You are a crypto trading strategist.
Given a market signal, produce a concrete trade proposal.
The amount_usd must be between $1 and $5 (small position for risk control).
Return ONLY valid JSON matching this schema:
{
  "action": "<BUY|SELL|HOLD>",
  "from_token": "<token or USD>",
  "to_token": "<token or USD>",
  "amount_usd": <float 1.0 to 5.0>,
  "rationale": "<one clear sentence explaining the trade>"
}
Rules:
- BUY: from_token = "USD", to_token = signal token
- SELL: from_token = signal token, to_token = "USD"
- HOLD: from_token and to_token both equal signal token, amount_usd = 0"""


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def run_strategist(signal: MarketSignal) -> TradeProposal:
    logger.section("Layer 2 — Strategist")
    logger.log("Strategist", f"Synthesizing proposal for {signal.token}...")

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
        config=types.GenerateContentConfig(system_instruction=_STRATEGIST_SYSTEM),
    )

    data = json.loads(_strip_fences(response.text.strip()))
    proposal = TradeProposal(**data)
    logger.result(
        "Strategist",
        f"{proposal.action} {proposal.from_token} -> {proposal.to_token} @ ${proposal.amount_usd:.2f}",
    )
    logger.log("Strategist", f"Rationale: {proposal.rationale}")
    return proposal
