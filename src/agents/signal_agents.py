"""Layer 1 — Build MarketSignal directly from raw data (ATK or mock)."""

from __future__ import annotations

from src.models import MarketSignal
from src import logger


async def gather_signals(raw: dict) -> MarketSignal:
    logger.section("Layer 1 — Market Signal")

    signal = MarketSignal(
        token=raw["token"],
        rsi=raw["rsi"],
        volume_24h=raw["volume_24h"],
        sentiment_score=raw["sentiment_score"],
        summary=raw["summary"],
    )

    logger.log("Signal", f"Token={signal.token} | RSI={signal.rsi} | Vol=${signal.volume_24h/1e6:.1f}M | Sentiment={signal.sentiment_score:+.2f}")
    logger.log("Signal", signal.summary)

    return signal
