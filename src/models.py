from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class MarketSignal(BaseModel):
    token: str
    rsi: float = Field(ge=0.0, le=100.0)
    volume_24h: float = Field(ge=0.0)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    summary: str


class TradeProposal(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    from_token: str
    to_token: str
    amount_usd: float = Field(ge=0.0)
    rationale: str


AgentName = Literal[
    "RiskOfficer",
    "MomentumTrader",
    "MacroAnalyst",
    "ContrarianTrader",
    "FundamentalsAnalyst",
    "QuantAnalyst",
    "GrowthInvestor",
    "SentimentAnalyst",
    "LiquidityAnalyst",
    "WhaleWatcher",
]


class CouncilVote(BaseModel):
    agent_name: AgentName
    approved: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class FinalDecision(BaseModel):
    proposal: TradeProposal
    votes: List[CouncilVote]
    consensus_reached: bool
    timestamp: datetime
    status: Literal["PENDING_EXECUTION", "REJECTED", "EXECUTED"]
    signal: MarketSignal | None = None
    order_id: str | None = None
