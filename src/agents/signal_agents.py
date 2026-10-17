"""Layer 1 — Sentiment Agent and Technical Agent run concurrently."""

from __future__ import annotations

import asyncio
import json
import os

from google import genai
from google.genai import types

from src.models import MarketSignal
from src import logger


_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
_MODEL = "gemini-3.8-flash"

_SENTIMENT_SYSTEM = """You are a crypto market sentiment analyst.
Given a market signal, assess the social and news sentiment.
Return ONLY valid JSON matching this schema:
{
  "sentiment_score": <float -1.0 to 1.0>,
  "summary": "<one concise sentence>"
}"""

_TECHNICAL_SYSTEM = """You are a crypto technical analyst.
Given RSI and 24h volume data, assess the technical outlook.
Return ONLY valid JSON matching this schema:
{
  "rsi_interpretation": "<oversold|neutral|overbought>",
  "volume_interpretation": "<low|average|high>",
  "technical_summary": "<one concise sentence>"
}"""


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def _call_gemini(system: str, user_prompt: str) -> str:
    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return _strip_fences(response.text.strip())


async def run_sentiment_agent(raw: dict) -> dict:
    logger.subsection("Sentiment Agent")
    prompt = (
        f"Token: {raw['token']}\n"
        f"Sentiment score hint: {raw['sentiment_score']}\n"
        f"Context: {raw['summary']}"
    )
    logger.log("SentimentAgent", f"Analyzing sentiment for {raw['token']}...")
    raw_json = await _call_gemini(_SENTIMENT_SYSTEM, prompt)
    result = json.loads(raw_json)
    logger.result("SentimentAgent", f"score={result['sentiment_score']:.2f} | {result['summary']}")
    return result


async def run_technical_agent(raw: dict) -> dict:
    logger.subsection("Technical Agent")
    prompt = (
        f"Token: {raw['token']}\n"
        f"RSI: {raw['rsi']}\n"
        f"24h Volume (USD): {raw['volume_24h']:,.0f}\n"
        f"Context: {raw['summary']}"
    )
    logger.log("TechnicalAgent", f"Analyzing technicals for {raw['token']}...")
    raw_json = await _call_gemini(_TECHNICAL_SYSTEM, prompt)
    result = json.loads(raw_json)
    logger.result(
        "TechnicalAgent",
        f"RSI={result['rsi_interpretation']} | Volume={result['volume_interpretation']} | {result['technical_summary']}",
    )
    return result


async def gather_signals(raw: dict) -> MarketSignal:
    """Run both signal agents concurrently and merge into a MarketSignal."""
    logger.section("Layer 1 — Signal Gathering")
    sentiment_result, technical_result = await asyncio.gather(
        run_sentiment_agent(raw),
        run_technical_agent(raw),
    )

    combined_summary = (
        f"{sentiment_result['summary']} "
        f"Technically: {technical_result['technical_summary']}"
    )

    return MarketSignal(
        token=raw["token"],
        rsi=raw["rsi"],
        volume_24h=raw["volume_24h"],
        sentiment_score=sentiment_result["sentiment_score"],
        summary=combined_summary,
    )
