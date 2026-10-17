"""Parallel multi-token market scanner — no Gemini calls, ATK only."""

from __future__ import annotations

import asyncio

from src.data.market_feed import fetch_market_raw

DEFAULT_WATCHLIST = [
    "ETH-USDT", "BTC-USDT", "SOL-USDT",
    "AVAX-USDT", "BNB-USDT", "XRP-USDT",
    "DOGE-USDT", "ADA-USDT", "DOT-USDT", "LINK-USDT",
]


async def scan_market(inst_ids: list[str], demo: bool = True) -> list[dict]:
    """Fetch signals for all tokens in parallel and return ranked by opportunity score."""
    results = await asyncio.gather(*[
        _fetch_safe(inst_id, demo) for inst_id in inst_ids
    ])

    signals = [r for r in results if r is not None]
    if not signals:
        return []

    max_vol = max(s["volume_24h"] for s in signals)

    for s in signals:
        rsi = s["rsi"]
        vol_rank = s["volume_24h"] / max_vol if max_vol > 0 else 0

        # The further RSI is from neutral (50), the stronger the signal
        rsi_score = abs(rsi - 50) / 50

        s["opportunity_score"] = round(rsi_score * 0.7 + vol_rank * 0.3, 3)
        s["suggested_action"] = (
            "BUY"  if rsi <= 45 else
            "SELL" if rsi >= 65 else
            "HOLD"
        )

    return sorted(signals, key=lambda x: x["opportunity_score"], reverse=True)


async def _fetch_safe(inst_id: str, demo: bool) -> dict | None:
    try:
        return await fetch_market_raw(inst_id, demo=demo)
    except Exception as e:
        print(f"[Scanner] {inst_id} failed: {e}")
        return None
