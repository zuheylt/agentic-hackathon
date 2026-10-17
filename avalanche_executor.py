"""
Records approved CouncilTrade decisions on Avalanche C-Chain via ERC-8004.
Called after every successful trade execution — creates an immutable audit trail.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("contracts/.env")

_RPC_URL          = os.getenv("AVALANCHE_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc")
_CONTRACT_ADDRESS = os.getenv("REGISTRY_CONTRACT_ADDRESS", "")
_PRIVATE_KEY      = os.getenv("PRIVATE_KEY", "")
_AGENT_ID         = int(os.getenv("AGENT_ID", "1"))
_DRY_RUN          = os.getenv("DRY_RUN", "true").lower() == "true"
_CHAIN_ID         = int(os.getenv("CHAIN_ID", "43113"))
_EXPLORER         = "https://testnet.snowtrace.io" if "test" in _RPC_URL else "https://snowtrace.io"

_ABI_PATH = Path("contracts/ERC8004Registry_abi.json")

# Fallback minimal ABI if the compiled ABI file isn't present yet
_FALLBACK_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId",   "type": "uint256"},
            {"internalType": "string",  "name": "action",    "type": "string"},
            {"internalType": "string",  "name": "tokenPair", "type": "string"},
            {"internalType": "uint256", "name": "amountUsd", "type": "uint256"},
            {"internalType": "string",  "name": "rationale", "type": "string"},
        ],
        "name": "recordValidation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def _load_abi() -> list:
    if _ABI_PATH.exists():
        return json.loads(_ABI_PATH.read_text())
    return _FALLBACK_ABI


def _record_sync(action: str, token: str, amount_usd: float, rationale: str) -> dict:
    """Synchronous blockchain call — run in a thread from async code."""
    from web3 import Web3

    abi = _load_abi()

    if _DRY_RUN or not _PRIVATE_KEY or not _CONTRACT_ADDRESS:
        import secrets
        fake_hash = "0x" + secrets.token_hex(32)
        print(f"  [Avalanche] DRY_RUN — simulated tx: {fake_hash[:20]}...")
        return {"tx_hash": fake_hash, "dry_run": True}

    w3       = Web3(Web3.HTTPProvider(_RPC_URL))
    account  = w3.eth.account.from_key(_PRIVATE_KEY)
    contract = w3.eth.contract(address=Web3.to_checksum_address(_CONTRACT_ADDRESS), abi=abi)

    tx = contract.functions.recordValidation(
        _AGENT_ID,
        action,
        f"{token}/USDT",
        int(amount_usd),
        rationale,
    ).build_transaction({
        "from":     account.address,
        "nonce":    w3.eth.get_transaction_count(account.address),
        "gas":      200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  _CHAIN_ID,
    })

    signed  = w3.eth.account.sign_transaction(tx, _PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    tx_hex = tx_hash.hex()
    print(f"  [Avalanche] Recorded on-chain: {_EXPLORER}/tx/{tx_hex}")
    return {"tx_hash": tx_hex, "explorer_url": f"{_EXPLORER}/tx/{tx_hex}"}


async def record_decision(action: str, token: str, amount_usd: float, rationale: str) -> dict:
    """Async wrapper — runs the blocking web3 call in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _record_sync, action, token, amount_usd, rationale
    )


# ── Legacy CLI entry point (kept for standalone use) ─────────────────────────
def execute_proposal():
    """Read latest_decision.json and record on-chain. Called from CLI."""
    import time
    data_path = Path("data/latest_decision.json")
    if not data_path.exists():
        print("❌ data/latest_decision.json not found.")
        return

    data     = json.loads(data_path.read_text())
    proposal = data.get("proposal", {})
    amount   = proposal.get("amount_usd", 0.0)

    if amount > 5.0:
        print(f"⚠️  Amount ${amount} exceeds $5 limit. Aborted.")
        return

    result = asyncio.run(record_decision(
        action     = proposal.get("action", "BUY"),
        token      = proposal.get("token", "?"),
        amount_usd = amount,
        rationale  = proposal.get("rationale", "Council consensus"),
    ))

    data.setdefault("execution", {})["avalanche_tx"] = result.get("tx_hash", "—")
    data["execution"]["avalanche_url"]               = result.get("explorer_url", "")
    data_path.write_text(json.dumps(data, indent=2))
    print("✅ Decision recorded on Avalanche.")


if __name__ == "__main__":
    execute_proposal()
