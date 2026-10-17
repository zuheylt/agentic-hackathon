"""Executes approved trade proposals via OKX ATK."""

from __future__ import annotations

import json
from pathlib import Path

from src.models import FinalDecision
from src.okx_client import get_balance, get_ticker, place_spot_order
from src import logger

_DECISION_PATH = Path("data/latest_decision.json")
_HISTORY_PATH  = Path("data/history.json")


async def execute_trade(decision: FinalDecision, demo: bool = True) -> FinalDecision:
    proposal = decision.proposal

    if proposal.action == "HOLD":
        logger.log("Executor", "Action is HOLD — no order placed.")
        return decision.model_copy(update={"status": "EXECUTED"})

    inst_id = f"{proposal.to_token if proposal.action == 'BUY' else proposal.from_token}-USDT"

    logger.subsection("ATK Execution")
    await _log_balance(demo)

    try:
        if proposal.action == "BUY":
            order = await place_spot_order(
                inst_id=inst_id, side="buy",
                sz=str(round(proposal.amount_usd, 4)), tgt_ccy="quote_ccy", demo=demo,
            )
        else:
            ticker   = await get_ticker(inst_id, demo=demo)
            token_sz = round(proposal.amount_usd / float(ticker["last"]), 6)
            order    = await place_spot_order(inst_id=inst_id, side="sell", sz=str(token_sz), demo=demo)

        ord_id = order.get("ordId", "unknown")
        logger.result("Executor", f"Order placed — ID: {ord_id} | {proposal.action} {inst_id} ${proposal.amount_usd:.2f}")

        # Record the approved decision on Avalanche C-Chain (fire-and-forget)
        try:
            from avalanche_executor import record_decision
            await record_decision(proposal.action, proposal.to_token if proposal.action == "BUY" else proposal.from_token, proposal.amount_usd, proposal.rationale)
        except Exception as avax_err:
            logger.log("Avalanche", f"On-chain record skipped: {avax_err}")

        return decision.model_copy(update={"status": "EXECUTED", "order_id": ord_id})

    except Exception as e:
        logger.log("Executor", f"Order failed: {e}")
        return decision.model_copy(update={"status": "REJECTED"})


async def execute_from_ui(demo: bool = True) -> dict:
    """Called from the UI when the user manually approves a PENDING_EXECUTION decision."""
    data = json.loads(_DECISION_PATH.read_text())
    if data["status"] != "PENDING_EXECUTION":
        return data

    prop       = data["proposal"]
    inst_id    = f"{prop['token']}-USDT"
    action     = prop["action"]
    amount_usd = prop["amount_usd"]

    try:
        if action == "BUY":
            order = await place_spot_order(inst_id, "buy", str(round(amount_usd, 4)), "quote_ccy", demo)
        elif action == "SELL":
            ticker   = await get_ticker(inst_id, demo=demo)
            token_sz = round(amount_usd / float(ticker["last"]), 6)
            order    = await place_spot_order(inst_id, "sell", str(token_sz), demo=demo)
        else:
            order = {"ordId": "HOLD"}

        data["status"]                = "EXECUTED"
        data["execution"]["order_id"] = order.get("ordId", "unknown")
    except Exception as e:
        data["status"]                = "REJECTED"
        data["execution"]["order_id"] = f"ERROR: {e}"

    _DECISION_PATH.write_text(json.dumps(data, indent=2))

    if _HISTORY_PATH.exists():
        history = json.loads(_HISTORY_PATH.read_text())
        if history:
            history[0]["status"]                = data["status"]
            history[0]["execution"]["order_id"] = data["execution"]["order_id"]
            _HISTORY_PATH.write_text(json.dumps(history, indent=2))

    return data


async def _log_balance(demo: bool) -> None:
    try:
        rows = await get_balance(demo=demo)
        usdt = next((r for r in rows if r.get("currency") == "USDT"), None)
        if usdt:
            logger.log("Portfolio", f"USDT available: {usdt.get('available', '?')}")
    except Exception:
        pass
