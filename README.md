# PocketTrader

Autonomous multi-agent trading council — signals, strategy, and consensus voting powered by Claude.

## Architecture

```
Layer 1 — Signal Gathering  (concurrent)
  ├── SentimentAgent   → reads narrative + sentiment score
  └── TechnicalAgent   → reads RSI + volume
           ↓
Layer 2 — Strategist         (serial)
  └── Synthesizes a TradeProposal (BUY / SELL / HOLD, $1–$5)
           ↓
Layer 3 — Council Vote       (concurrent)
  ├── RiskOfficer     → veto power; blocks if amount > $5 or RSI overbought
  └── MomentumTrader  → checks momentum alignment
           ↓
FinalDecision → data/latest_decision.json  (UI bridge)
```

Consensus rule: **RiskOfficer must approve AND approval rate ≥ 70%.**

## Setup

```bash
# 1. Clone and enter the repo
cd agentic-hackathon

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Anthropic API key
cp .env.example .env
# edit .env and paste your key
```

## Usage

```bash
# Run scenario 0 (Bullish ETH Breakout)
python main.py --mock

# Pick a specific scenario (0–3)
python main.py --mock --scenario 2

# Run all four mock scenarios back-to-back
python main.py --mock --all
```

## Mock Scenarios

| # | Name                         | Token | Bias      |
|---|------------------------------|-------|-----------|
| 0 | Bullish ETH Breakout         | ETH   | BUY       |
| 1 | BTC Overbought Warning       | BTC   | SELL/HOLD |
| 2 | SOL High-Risk Momentum       | SOL   | HOLD      |
| 3 | AVAX Undervalued Opportunity | AVAX  | BUY       |

## Output

Every run writes `data/latest_decision.json`:

```json
{
  "proposal": { "action": "BUY", "from_token": "USD", "to_token": "ETH", "amount_usd": 3.5, "rationale": "..." },
  "votes": [
    { "agent_name": "RiskOfficer", "approved": true, "confidence": 0.85, "reason": "..." },
    { "agent_name": "MomentumTrader", "approved": true, "confidence": 0.78, "reason": "..." }
  ],
  "consensus_reached": true,
  "timestamp": "2026-10-17T12:00:00+00:00",
  "status": "PENDING_EXECUTION"
}
```

## File Structure

```
main.py                   # CLI entrypoint
src/
  models.py               # Pydantic data models
  logger.py               # Formatted terminal output
  pipeline.py             # Full pipeline orchestrator
  agents/
    signal_agents.py      # Layer 1: SentimentAgent + TechnicalAgent
    strategist.py         # Layer 2: TradeProposal synthesis
    council.py            # Layer 3: RiskOfficer + MomentumTrader
data/
  mock_scenarios.json     # Pre-configured demo scenarios
  latest_decision.json    # Written after each run (UI bridge)
```
