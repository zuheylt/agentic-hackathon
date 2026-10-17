"""Builds a live MarketSignal from OKX ATK data (ticker + candles)."""

from __future__ import annotations

import asyncio

from src.okx_client import get_candles, get_ticker
from src import logger


def _compute_rsi(candles: list, period: int = 14) -> float:
    closes = [float(c[4]) for c in reversed(candles)]
    if len(closes) < period + 1:
        return 50.0

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains  = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


async def fetch_market_raw(inst_id: str, demo: bool = True) -> dict:
    logger.subsection(f"ATK Market Feed — {inst_id}")

    ticker, candles = await asyncio.gather(
        get_ticker(inst_id, demo=demo),
        get_candles(inst_id, bar="1H", limit=20, demo=demo),
    )

    last       = float(ticker["last"])
    open24h    = float(ticker["open24h"])
    high24h    = float(ticker["high24h"])
    low24h     = float(ticker["low24h"])
    vol_usd    = float(ticker["volCcy24h"])
    change_pct = ((last - open24h) / open24h) * 100
    rsi        = _compute_rsi(candles)
    token      = inst_id.split("-")[0]

    summary = (
        f"{token}/USDT trading at ${last:,.2f}. "
        f"24h change: {change_pct:+.2f}% (H: ${high24h:,.2f} / L: ${low24h:,.2f}). "
        f"RSI(14): {rsi}. 24h volume: ${vol_usd:,.0f}."
    )
    logger.log("ATKFeed", f"${last:,.2f} | RSI={rsi} | Vol=${vol_usd/1e6:.1f}M | {change_pct:+.2f}%")

    return {
        "name": f"Live: {inst_id}",
        "inst_id": inst_id,
        "token": token,
        "last_price": last,
        "change_24h_pct": change_pct,
        "rsi": rsi,
        "volume_24h": vol_usd,
        "sentiment_score": 0.0,
        "summary": summary,
    }
