"""Executes approved trade proposals via OKX ATK."""

from __future__ import annotations

from src.models import FinalDecision, TradeProposal
from src.okx_client import get_ticker, get_balance, place_spot_order
from src import logger


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
                inst_id=inst_id,
                side="buy",
                sz=str(round(proposal.amount_usd, 4)),
                tgt_ccy="quote_ccy",
                demo=demo,
            )
        else:  # SELL
            ticker = await get_ticker(inst_id, demo=demo)
            price = float(ticker["last"])
            token_sz = round(proposal.amount_usd / price, 6)
            order = await place_spot_order(
                inst_id=inst_id,
                side="sell",
                sz=str(token_sz),
                demo=demo,
            )

        ord_id = order.get("ordId", "unknown")
        logger.result("Executor", f"Order placed — ID: {ord_id} | {proposal.action} {inst_id} ${proposal.amount_usd:.2f}")
        return decision.model_copy(update={"status": "EXECUTED", "order_id": ord_id})

    except Exception as e:
        logger.log("Executor", f"Order failed: {e}")
        return decision.model_copy(update={"status": "REJECTED"})


async def execute_from_ui(demo: bool = True) -> dict:
    """Called from the UI when user manually approves a PENDING_EXECUTION decision."""
    import json
    from pathlib import Path
    from src.pipeline import DECISION_PATH, HISTORY_PATH, _to_ui_dict
    from src.models import FinalDecision, TradeProposal, CouncilVote, MarketSignal
    from datetime import datetime, timezone

    data = json.loads(DECISION_PATH.read_text())
    if data["status"] != "PENDING_EXECUTION":
        return data

    prop_data = data["proposal"]
    token = prop_data["token"]
    action = prop_data["action"]
    amount_usd = prop_data["amount_usd"]
    inst_id = f"{token}-USDT"

    try:
        if action == "BUY":
            order = await place_spot_order(inst_id, "buy", str(round(amount_usd, 4)), "quote_ccy", demo)
        elif action == "SELL":
            ticker = await get_ticker(inst_id, demo=demo)
            token_sz = round(amount_usd / float(ticker["last"]), 6)
            order = await place_spot_order(inst_id, "sell", str(token_sz), demo=demo)
        else:
            order = {"ordId": "HOLD"}

        ord_id = order.get("ordId", "unknown")
        data["status"] = "EXECUTED"
        data["execution"]["order_id"] = ord_id
    except Exception as e:
        data["status"] = "REJECTED"
        data["execution"]["order_id"] = f"ERROR: {e}"

    DECISION_PATH.write_text(json.dumps(data, indent=2))

    # Update the matching history entry
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text())
        if history:
            history[0]["status"] = data["status"]
            history[0]["execution"]["order_id"] = data["execution"]["order_id"]
            HISTORY_PATH.write_text(json.dumps(history, indent=2))

    return data


async def _log_balance(demo: bool) -> None:
    try:
        rows = await get_balance(demo=demo)
        usdt = next((r for r in rows if r.get("currency") == "USDT"), None)
        if usdt:
            logger.log("Portfolio", f"USDT available: {usdt.get('available', '?')}")
    except Exception:
        pass
