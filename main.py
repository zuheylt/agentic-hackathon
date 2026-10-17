#!/usr/bin/env python3
"""CouncilTrade CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src import logger
from src.pipeline import run_pipeline


MOCK_PATH = Path("data/mock_scenarios.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CouncilTrade — autonomous multi-agent trading council"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use pre-configured mock scenarios from data/mock_scenarios.json",
    )
    parser.add_argument(
        "--scenario",
        type=int,
        default=0,
        help="Index of the mock scenario to run (default: 0)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all mock scenarios sequentially",
    )
    return parser.parse_args()


def load_mock_scenario(index: int) -> dict:
    if not MOCK_PATH.exists():
        print(f"[ERROR] Mock file not found: {MOCK_PATH}", file=sys.stderr)
        sys.exit(1)
    scenarios = json.loads(MOCK_PATH.read_text())
    if index >= len(scenarios):
        print(
            f"[ERROR] Scenario index {index} out of range (0-{len(scenarios)-1})",
            file=sys.stderr,
        )
        sys.exit(1)
    return scenarios[index]


async def main() -> None:
    args = parse_args()

    if not args.mock:
        logger.section("CouncilTrade")
        print("  No live data source configured.")
        print("  Run with --mock to use demo scenarios:")
        print("    python main.py --mock              # scenario 0 (default)")
        print("    python main.py --mock --scenario 2 # pick scenario index")
        print("    python main.py --mock --all        # run all scenarios")
        return

    if args.all:
        scenarios = json.loads(MOCK_PATH.read_text())
        for i, scenario in enumerate(scenarios):
            print(f"\n{'#' * 60}")
            print(f"# SCENARIO {i+1}/{len(scenarios)}: {scenario['name']}")
            print(f"{'#' * 60}")
            await run_pipeline(scenario)
    else:
        scenario = load_mock_scenario(args.scenario)
        await run_pipeline(scenario)


if __name__ == "__main__":
    asyncio.run(main())
