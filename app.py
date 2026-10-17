import streamlit as st
import json
import os
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="CouncilTrade // AI Investment Council",
    page_icon="🔺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom Cyberpunk / Dark Mode Styling ---
st.markdown("""
    <style>
    /* Main Dark Theme */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Custom Card Style */
    .net-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Cyber Badges */
    .status-badge {
        background-color: #238636;
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 14px;
        display: inline-block;
    }
    
    .avax-badge {
        background-color: #e84142;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 14px;
        display: inline-block;
    }

    /* Decision Banner Colors */
    .buy-banner {
        background-color: rgba(46, 160, 67, 0.15);
        border: 1px solid #2ea043;
        border-radius: 8px;
        padding: 15px;
        color: #3fb950;
    }
    
    /* Headers */
    h1, h2, h3, h4 {
        color: #58a6ff !important;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Links */
    a {
        color: #58a6ff !important;
        text-decoration: none;
        font-weight: bold;
    }
    a:hover {
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

# --- Data Loader Function (With Fallback Dummy Data) ---
def load_data():
    json_path = os.path.join("data", "latest_decision.json")
    
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Dummy Data if JSON is not ready/found
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "technical": {
            "rsi": 28.4,
            "volume_24h": "$142.8M",
            "verdict": "BULLISH (Oversold)"
        },
        "sentiment": {
            "score": 0.78,
            "summary": "Avalanche Subnet adoption surging + OKX integration news trending positively."
        },
        "proposal": {
            "action": "BUY",
            "token": "AVAX",
            "amount_usd": 50.0,
            "rationale": "RSI shows severe oversold bounce zone paired with strong positive Twitter/News sentiment."
        },
        "council": {
            "risk_officer": {
                "status": "APPROVED",
                "notes": "Portfolio risk ratio within limits (<2%). Stop loss set at -3%."
            },
            "momentum_trader": {
                "status": "APPROVED",
                "confidence": "92%"
            },
            "consensus_passed": True,
            "consensus_score": "85%"
        },
        "execution": {
            "tx_hash": "0x8f3c4a2b1e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b",
            "block_finality": "1.18s",
            "gas_fee": "0.0012 AVAX",
            "snowtrace_url": "https://snowtrace.io/"
        }
    }

data = load_data()

# --- 1. HEADER SECTION ---
col_title, col_status = st.columns([3, 1])

with col_title:
    st.title("⚡ CouncilTrade")
    st.caption("Autonomous AI Investment Council // Multi-Agent Pipeline")

with col_status:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="avax-badge">🔺 Avalanche C-Chain [LIVE]</span>', unsafe_allow_html=True)
    st.markdown(' <span class="status-badge">🤖 4 Agents Online</span>', unsafe_allow_html=True)

st.divider()

# --- 2. LAYER 1: MARKET INTELLIGENCE ---
st.subheader("🌐 Layer 1: Market Intelligence")

col_tech, col_sent = st.columns(2)

with col_tech:
    st.markdown("""
        <div class="net-card">
            <h4>📊 Technical Analyst Agent</h4>
            <p><strong>RSI Gauge:</strong> {rsi} (Oversold Zone)</p>
            <p><strong>24h Volume:</strong> {vol}</p>
            <p><strong>Verdict:</strong> <span style="color:#3fb950;">{verdict}</span></p>
        </div>
    """.format(
        rsi=data["technical"]["rsi"],
        vol=data["technical"]["volume_24h"],
        verdict=data["technical"]["verdict"]
    ), unsafe_allow_html=True)

with col_sent:
    score = data["sentiment"]["score"]
    score_color = "#3fb950" if score > 0 else "#f85149"
    st.markdown("""
        <div class="net-card">
            <h4>📰 Sentiment Analyst Agent</h4>
            <p><strong>Sentiment Score:</strong> <span style="color:{color};">{score} / +1.0</span></p>
            <p><strong>Latest Summary:</strong> <em>"{summary}"</em></p>
        </div>
    """.format(
        color=score_color,
        score=score,
        summary=data["sentiment"]["summary"]
    ), unsafe_allow_html=True)

# --- 3. LAYER 2 & 3: STRATEGIST PROPOSAL & COUNCIL VOTING ---
st.subheader("🧠 Layer 2 & 3: Strategist Proposal & Council Consensus")

# Proposal Banner
prop = data["proposal"]
st.markdown("""
    <div class="buy-banner">
        <h3>Proposed Trade: {action} {token} (${amount})</h3>
        <p><strong>Rationale:</strong> {rationale}</p>
    </div>
    <br>
""".format(
    action=prop["action"],
    token=prop["token"],
    amount=prop["amount_usd"],
    rationale=prop["rationale"]
), unsafe_allow_html=True)

# Voting Grid
col_risk, col_trend, col_consensus = st.columns(3)

with col_risk:
    risk_status = data["council"]["risk_officer"]["status"]
    badge_color = "#2ea043" if risk_status == "APPROVED" else "#da3633"
    st.markdown("""
        <div class="net-card">
            <h4>🛡️ Risk Officer</h4>
            <p><strong>Decision:</strong> <span style="color:{color}; font-weight:bold;">{status}</span></p>
            <p><small>{notes}</small></p>
        </div>
    """.format(
        color=badge_color,
        status=risk_status,
        notes=data["council"]["risk_officer"]["notes"]
    ), unsafe_allow_html=True)

with col_trend:
    trend_status = data["council"]["momentum_trader"]["status"]
    badge_color = "#2ea043" if trend_status == "APPROVED" else "#da3633"
    st.markdown("""
        <div class="net-card">
            <h4>📈 Momentum Trader</h4>
            <p><strong>Decision:</strong> <span style="color:{color}; font-weight:bold;">{status}</span></p>
            <p><strong>Confidence:</strong> {conf}</p>
        </div>
    """.format(
        color=badge_color,
        status=trend_status,
        conf=data["council"]["momentum_trader"]["confidence"]
    ), unsafe_allow_html=True)

with col_consensus:
    passed = data["council"]["consensus_passed"]
    status_text = f"PASSED ({data['council']['consensus_score']})" if passed else "REJECTED"
    color = "#2ea043" if passed else "#da3633"
    st.markdown("""
        <div class="net-card" style="text-align: center;">
            <h4>🗳️ Final Consensus</h4>
            <h2 style="color:{color} !important;">{status}</h2>
            <p><small>Threshold Required: >70%</small></p>
        </div>
    """.format(
        color=color,
        status=status_text
    ), unsafe_allow_html=True)

# --- 4. LAYER 4: AVALANCHE ON-CHAIN EXECUTION ---
st.subheader("🔺 Layer 4: On-Chain Execution (Avalanche C-Chain)")

exec_data = data["execution"]
col_exec_info, col_link = st.columns([3, 1])

with col_exec_info:
    st.markdown(f"""
        **Tx Hash:** `{exec_data['tx_hash']}`  
        **Block Finality:** `{exec_data['block_finality']}` | **Gas Fee:** `{exec_data['gas_fee']}`
    """)

with col_link:
    st.markdown(f"""
        <br>
        <a href="{exec_data['snowtrace_url']}" target="_blank" style="
            background-color: #e84142;
            color: white !important;
            padding: 10px 18px;
            border-radius: 6px;
            font-weight: bold;
            display: inline-block;
        ">View on Snowtrace ↗</a>
    """, unsafe_allow_html=True)

st.caption(f"Last updated: {data['timestamp']} — (Auto-refreshing state...)")
time.sleep(2)
st.rerun()
