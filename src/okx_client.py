"""Thin async wrapper around the OKX ATK CLI (--json mode)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

ATK_BIN = str(Path.home() / ".npm-global" / "bin" / "okx")


async def call_atk(*args: str, demo: bool = True) -> list | dict:
    mode_flag = "--demo" if demo else "--live"
    cmd = [ATK_BIN, mode_flag, "--json"] + list(args)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ATK error: {stderr.decode().strip()}")

    return json.loads(stdout.decode())


async def get_ticker(inst_id: str, demo: bool = True) -> dict:
    data = await call_atk("market", "ticker", inst_id, demo=demo)
    return data[0]


async def get_candles(inst_id: str, bar: str = "1H", limit: int = 20, demo: bool = True) -> list:
    return await call_atk("market", "candles", inst_id, "--bar", bar, "--limit", str(limit), demo=demo)


async def get_balance(demo: bool = True) -> list:
    return await call_atk("account", "balance", demo=demo)


async def place_spot_order(
    inst_id: str,
    side: str,
    sz: str,
    tgt_ccy: str | None = None,
    demo: bool = True,
) -> dict:
    args = [
        "spot", "place",
        "--instId", inst_id,
        "--side", side,
        "--ordType", "market",
        "--sz", sz,
    ]
    if tgt_ccy:
        args += ["--tgtCcy", tgt_ccy]
    data = await call_atk(*args, demo=demo)
    return data[0] if isinstance(data, list) else data
