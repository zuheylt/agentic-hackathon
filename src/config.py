"""Settings management — load/save user configuration."""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path("data/settings.json")

DEFAULTS: dict = {
    "budget_usd": 100.0,
    "risk_strategy": "moderate",   # conservative | moderate | aggressive
    "max_tx_usd": 5.0,
    "max_commodity_ratio": 30,     # % of portfolio in one token
    "stop_loss_pct": 5.0,
    "take_profit_pct": 15.0,
    "max_daily_trades": 5,
    "auto_execute": False,
}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            saved = json.loads(SETTINGS_PATH.read_text())
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return DEFAULTS.copy()


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
