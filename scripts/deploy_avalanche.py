"""
Deploy ERC8004Registry to Avalanche Fuji testnet and register PocketTrader as an on-chain AI agent.

Usage:
    python scripts/deploy_avalanche.py

Prerequisites:
    1. Get free test AVAX: https://faucet.avax.network/
    2. Export your MetaMask private key and add it to contracts/.env:
       PRIVATE_KEY=0x<your_key>
    3. pip install -r requirements.txt
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("contracts/.env")

FUJI_RPC   = "https://api.avax-test.network/ext/bc/C/rpc"
FUJI_CHAIN = 43113
EXPLORER   = "https://testnet.snowtrace.io"

CONTRACT_SOURCE = Path("contracts/contracts/ERC8004Registry.sol").read_text()
AGENT_CARD      = json.loads(Path("data/data/agent_card.json").read_text())
ENV_PATH        = Path("contracts/.env")


def _check_prereqs() -> str:
    key = os.environ.get("PRIVATE_KEY", "")
    if not key or key == "0x<your_key>":
        print("\n[ERROR] PRIVATE_KEY not set in contracts/.env")
        print("  1. Open MetaMask → Account → ··· → Account Details → Export Private Key")
        print("  2. Add to contracts/.env:  PRIVATE_KEY=0x<your_key>")
        sys.exit(1)
    return key


def _install_solc():
    from solcx import install_solc, get_installed_solc_versions
    version = "0.8.20"
    if version not in [str(v) for v in get_installed_solc_versions()]:
        print(f"  Installing Solidity {version}...")
        install_solc(version)
    return version


def _compile(solc_version: str) -> tuple[list, str]:
    from solcx import compile_source
    compiled = compile_source(
        CONTRACT_SOURCE,
        output_values=["abi", "bin"],
        solc_version=solc_version,
    )
    key = next(k for k in compiled if "ERC8004Registry" in k)
    return compiled[key]["abi"], compiled[key]["bin"]


def deploy():
    from web3 import Web3

    private_key = _check_prereqs()

    print("\n── Connecting to Avalanche Fuji testnet...")
    w3 = Web3(Web3.HTTPProvider(FUJI_RPC))
    if not w3.is_connected():
        print("[ERROR] Could not connect to Fuji RPC. Check your internet connection.")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    balance = w3.from_wei(w3.eth.get_balance(account.address), "ether")
    print(f"  Wallet:  {account.address}")
    print(f"  Balance: {balance:.4f} AVAX")

    if balance < 0.01:
        print("\n[ERROR] Insufficient balance. Get free test AVAX:")
        print("  https://faucet.avax.network/")
        sys.exit(1)

    print("\n── Compiling ERC8004Registry.sol...")
    solc_version = _install_solc()
    abi, bytecode = _compile(solc_version)
    print("  Compiled OK")

    print("\n── Deploying contract...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor().build_transaction({
        "from":     account.address,
        "nonce":    w3.eth.get_transaction_count(account.address),
        "gas":      1_500_000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  FUJI_CHAIN,
    })
    signed  = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    print(f"  Tx sent: {EXPLORER}/tx/{tx_hash.hex()}")
    print("  Waiting for confirmation (~2s)...")
    receipt          = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    contract_address = receipt["contractAddress"]
    print(f"  Contract deployed: {contract_address}")
    print(f"  Snowtrace: {EXPLORER}/address/{contract_address}")

    print("\n── Registering PocketTrader as ERC-8004 AI agent...")
    contract  = w3.eth.contract(address=contract_address, abi=abi)
    agent_uri = json.dumps(AGENT_CARD)

    gas_est = contract.functions.registerAgent(
        "PocketTrader AI Agent", agent_uri
    ).estimate_gas({"from": account.address})

    reg_tx = contract.functions.registerAgent(
        "PocketTrader AI Agent", agent_uri
    ).build_transaction({
        "from":     account.address,
        "nonce":    w3.eth.get_transaction_count(account.address),
        "gas":      gas_est + 50_000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  FUJI_CHAIN,
    })
    signed_reg   = w3.eth.account.sign_transaction(reg_tx, private_key)
    reg_tx_hash  = w3.eth.send_raw_transaction(signed_reg.raw_transaction)
    reg_receipt  = w3.eth.wait_for_transaction_receipt(reg_tx_hash, timeout=60)

    # Parse agent ID from AgentRegistered event
    logs     = contract.events.AgentRegistered().process_receipt(reg_receipt)
    agent_id = logs[0]["args"]["agentId"] if logs else 1
    print(f"  Agent registered — ID: {agent_id}")
    print(f"  Tx: {EXPLORER}/tx/{reg_tx_hash.hex()}")

    print("\n── Saving config to contracts/.env...")
    ENV_PATH.write_text(
        f"REGISTRY_CONTRACT_ADDRESS={contract_address}\n"
        f"AVALANCHE_RPC_URL={FUJI_RPC}\n"
        f"DRY_RUN=false\n"
        f"PRIVATE_KEY={private_key}\n"
        f"AGENT_ID={agent_id}\n"
        f"CHAIN_ID={FUJI_CHAIN}\n"
    )

    # Save ABI for use by executor
    Path("contracts/ERC8004Registry_abi.json").write_text(json.dumps(abi, indent=2))

    print("\n✅  Deployment complete!")
    print(f"   Contract:  {contract_address}")
    print(f"   Agent ID:  {agent_id}")
    print(f"   Explorer:  {EXPLORER}/address/{contract_address}")
    print("\n  Next: run 'python main.py --live AVAX-USDT'")
    print("  Every approved trade will now be recorded on Avalanche.")


if __name__ == "__main__":
    deploy()
