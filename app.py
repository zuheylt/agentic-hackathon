import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai as _genai
from google.genai import types as _types
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CouncilTrade",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.stApp { background-color:#0d1117; color:#c9d1d9; font-family:'Courier New',monospace; }
.net-card { background:#161b22; border:1px solid #30363d; border-radius:8px;
            padding:16px; margin-bottom:12px; box-shadow:0 4px 6px rgba(0,0,0,.3); }
.okx-badge  { background:#1a6cff; color:#fff; padding:4px 12px; border-radius:12px;
              font-weight:bold; font-size:13px; display:inline-block; }
.ok-badge   { background:#238636; color:#fff; padding:4px 12px; border-radius:12px;
              font-weight:bold; font-size:13px; display:inline-block; }
.warn-badge { background:#bb8009; color:#fff; padding:4px 12px; border-radius:12px;
              font-weight:bold; font-size:13px; display:inline-block; }
.buy-banner  { background:rgba(46,160,67,.15); border:1px solid #2ea043;
               border-radius:8px; padding:15px; color:#3fb950; }
.sell-banner { background:rgba(218,54,51,.15); border:1px solid #da3633;
               border-radius:8px; padding:15px; color:#f85149; }
.hold-banner { background:rgba(187,128,9,.15); border:1px solid #bb8009;
               border-radius:8px; padding:15px; color:#d29922; }
h1,h2,h3,h4 { color:#58a6ff !important; font-family:'Courier New',monospace; }
a { color:#58a6ff !important; text-decoration:none; font-weight:bold; }
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DECISION_PATH = Path("data/latest_decision.json")
HISTORY_PATH  = Path("data/history.json")
SETTINGS_PATH = Path("data/settings.json")

AGENT_ICONS = {
    "RiskOfficer": "🛡️", "MomentumTrader": "📈", "MacroAnalyst": "🌍",
    "ContrarianTrader": "🔄", "FundamentalsAnalyst": "🔬", "QuantAnalyst": "📐",
    "GrowthInvestor": "🌱", "SentimentAnalyst": "💬",
    "LiquidityAnalyst": "💧", "WhaleWatcher": "🐋",
}

from src.agents._utils import format_volume
from src.config import DEFAULTS as SETTINGS_DEFAULTS, load_settings, save_settings

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_decision() -> dict | None:
    if DECISION_PATH.exists():
        try:
            return json.loads(DECISION_PATH.read_text())
        except Exception:
            pass
    return None


def load_history() -> list:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text())
        except Exception:
            pass
    return []


_thread_pool = ThreadPoolExecutor(max_workers=2)
_assistant_client = _genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def run_async(coro):
    """Run an async coroutine safely from Streamlit's sync context."""
    future = _thread_pool.submit(asyncio.run, coro)
    return future.result()


# ── Sidebar nav ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ CouncilTrade")
    st.markdown('<span class="okx-badge">🔵 OKX Demo</span> '
                '<span class="ok-badge">🤖 10 Agents</span>', unsafe_allow_html=True)
    st.divider()
    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "⚙️ Setup", "💼 Portfolio", "📜 History", "🤖 Assistant"],
        label_visibility="collapsed",
    )
    st.divider()
    settings = load_settings()
    st.caption(f"Budget: ${settings['budget_usd']:.0f} · Risk: {settings['risk_strategy'].title()}")
    st.caption(f"Max/tx: ${settings['max_tx_usd']:.2f} · Auto-exec: {'ON' if settings['auto_execute'] else 'OFF'}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title("⚡ CouncilTrade Dashboard")
    st.caption("Run the AI council on any OKX token and see a full decision breakdown.")

    # ── Market Scanner ────────────────────────────────────────────────────────
    with st.expander("🔍 Scan Multiple Tokens — find the best opportunity", expanded=False):
        from src.data.scanner import DEFAULT_WATCHLIST

        selected_tokens = st.multiselect(
            "Tokens to scan",
            options=DEFAULT_WATCHLIST,
            default=DEFAULT_WATCHLIST[:6],
            help="Select which tokens to scan. The scanner fetches live data for all of them at once.",
        )
        scan_clicked = st.button("🔍 Scan Now", use_container_width=True)

        if scan_clicked and selected_tokens:
            with st.spinner(f"Scanning {len(selected_tokens)} tokens…"):
                try:
                    from src.data.scanner import scan_market
                    scan_results = run_async(scan_market(selected_tokens, demo=True))
                    st.session_state["scan_results"] = scan_results
                except Exception as e:
                    st.error(f"Scan error: {e}")

        if "scan_results" in st.session_state and st.session_state["scan_results"]:
            results = st.session_state["scan_results"]
            st.markdown("#### Results — ranked by opportunity score")

            header = st.columns([1.2, 1.2, 1, 1, 1, 1, 1.2])
            for col, label in zip(header, ["Token", "Price", "24h %", "RSI", "Volume", "Signal", "Action"]):
                col.markdown(f"**{label}**")

            for i, r in enumerate(results):
                action = r["suggested_action"]
                action_color = "#3fb950" if action == "BUY" else ("#f85149" if action == "SELL" else "#d29922")
                rsi = r["rsi"]
                rsi_color = "#f85149" if rsi >= 65 else ("#3fb950" if rsi <= 35 else "#c9d1d9")
                change = r["change_24h_pct"]
                change_color = "#3fb950" if change >= 0 else "#f85149"
                vol = r["volume_24h"]
                vol_str = format_volume(vol)
                score_bar = "█" * int(r["opportunity_score"] * 10) + "░" * (10 - int(r["opportunity_score"] * 10))

                row = st.columns([1.2, 1.2, 1, 1, 1, 1, 1.2])
                crown = "👑 " if i == 0 else ""
                row[0].markdown(f"**{crown}{r['token']}**")
                row[1].markdown(f"${r['last_price']:,.2f}")
                row[2].markdown(f"<span style='color:{change_color};'>{change:+.2f}%</span>", unsafe_allow_html=True)
                row[3].markdown(f"<span style='color:{rsi_color};'>{rsi}</span>", unsafe_allow_html=True)
                row[4].markdown(vol_str)
                row[5].markdown(f"<span style='color:{action_color};'>{score_bar}</span>", unsafe_allow_html=True)
                if row[6].button(f"Run on {r['token']}", key=f"scan_run_{i}"):
                    st.session_state["inst_id_input"] = r["inst_id"]
                    st.rerun()

            st.caption("Score = RSI deviation from neutral (70%) + volume rank (30%). Higher = stronger signal.")

    st.divider()

    # ── Run controls ──────────────────────────────────────────────────────────
    if "inst_id_input" not in st.session_state:
        st.session_state["inst_id_input"] = "ETH-USDT"

    col_inst, col_mode, col_btn = st.columns([2, 1, 1])
    with col_inst:
        inst_id = st.text_input("Token pair", key="inst_id_input",
                                help="Any OKX spot pair, e.g. BTC-USDT, SOL-USDT").upper().strip()
    with col_mode:
        use_mock = st.checkbox("Use mock data", value=False,
                               help="Tick this if you have no OKX API key — uses offline demo scenarios")
        mock_idx = 0
        if use_mock:
            mock_idx = st.number_input("Scenario #", min_value=0, max_value=3, value=0, step=1)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_clicked = st.button("▶ Run Council", use_container_width=True, type="primary")

    if run_clicked:
        with st.spinner("Council is deliberating…"):
            try:
                from src.pipeline import run_live_pipeline, run_pipeline
                if use_mock:
                    scenarios = json.loads(Path("data/mock_scenarios.json").read_text())
                    scenario = scenarios[mock_idx % len(scenarios)]
                    run_async(run_pipeline(scenario, settings=settings,
                                          auto_execute=settings["auto_execute"]))
                else:
                    run_async(run_live_pipeline(inst_id, demo=True, settings=settings,
                                               auto_execute=settings["auto_execute"]))
                st.success("Done! Decision written.")
                st.session_state["_just_ran"] = True
            except Exception as e:
                st.error(f"Pipeline error: {e}")
        st.rerun()

    # ── Decision display ──────────────────────────────────────────────────────
    data = load_decision()
    if not data:
        st.info("No decision yet. Hit **▶ Run Council** above to start.")
        st.stop()

    st.divider()

    # Status bar
    status = data.get("status", "—")
    status_color = {"EXECUTED": "#3fb950", "FORCE_EXECUTED": "#e06c00",
                    "REJECTED": "#f85149", "PENDING_EXECUTION": "#d29922"}.get(status, "#c9d1d9")
    st.markdown(
        f'<span style="color:{status_color}; font-size:18px; font-weight:bold;">● {status}</span>'
        f' &nbsp;·&nbsp; <span style="color:#8b949e;">{data.get("timestamp", "—")}</span>',
        unsafe_allow_html=True,
    )

    # Approve button (manual execution gate)
    if status == "PENDING_EXECUTION" and not settings["auto_execute"]:
        st.warning("⚠️ Council approved this trade — waiting for your go-ahead.")
        if st.button("✅ Approve & Execute Trade", type="primary"):
            with st.spinner("Sending order to OKX…"):
                try:
                    from src.execution.executor import execute_from_ui
                    data = run_async(execute_from_ui(demo=True))
                    st.success(f"Order placed! ID: {data['execution']['order_id']}")
                except Exception as e:
                    st.error(f"Execution error: {e}")
            st.rerun()

    # Force override (council rejected but user wants to execute anyway)
    if status == "REJECTED":
        prop = data.get("proposal", {})
        with st.expander("⚡ Override Council Decision"):
            st.error(
                f"The council rejected this trade ({data['council'].get('approved_count', '?')}/{data['council'].get('total_count', 10)} votes). "
                "Forcing it will execute regardless of the AI's recommendation."
            )
            st.markdown(
                f"**Proposal:** {prop.get('action')} {prop.get('token')} · "
                f"${prop.get('amount_usd')} · *{prop.get('rationale')}*"
            )
            col_warn, col_btn = st.columns([3, 1])
            col_warn.warning("You are overriding 10 AI agents. This action is logged.")
            if col_btn.button("🔴 Force Execute", type="primary"):
                with st.spinner("Forcing order to OKX…"):
                    try:
                        from src.execution.executor import force_execute_from_ui
                        data = run_async(force_execute_from_ui(demo=True))
                        st.success(f"Force executed! Order ID: {data['execution']['order_id']}")
                    except Exception as e:
                        st.error(f"Execution error: {e}")
                st.rerun()

    st.divider()
    st.subheader("🌐 Market Signal")

    col_tech, col_sent = st.columns(2)
    with col_tech:
        rsi = data["technical"]["rsi"]
        rsi_color = "#f85149" if rsi >= 70 else ("#3fb950" if rsi <= 30 else "#c9d1d9")
        st.markdown(f"""<div class="net-card">
            <h4>📊 Technical</h4>
            <p><strong>RSI(14):</strong> <span style="color:{rsi_color};">{rsi}</span>
               &nbsp;·&nbsp; <strong>Vol:</strong> {data['technical']['volume_24h']}</p>
            <p><strong>Verdict:</strong> <span style="color:{rsi_color};">{data['technical']['verdict']}</span></p>
        </div>""", unsafe_allow_html=True)

    with col_sent:
        score = data["sentiment"]["score"]
        sc = "#3fb950" if score > 0.1 else ("#f85149" if score < -0.1 else "#d29922")
        st.markdown(f"""<div class="net-card">
            <h4>📰 Sentiment</h4>
            <p><strong>Score:</strong> <span style="color:{sc};">{score:+.2f}</span></p>
            <p><small><em>{data['sentiment']['summary']}</em></small></p>
        </div>""", unsafe_allow_html=True)

    st.subheader("🧠 Proposal")
    prop = data["proposal"]
    action = prop["action"]
    cls = {"BUY": "buy-banner", "SELL": "sell-banner"}.get(action, "hold-banner")
    st.markdown(f"""<div class="{cls}">
        <h3>{action} {prop['token']} · ${prop['amount_usd']}</h3>
        <p>{prop['rationale']}</p>
    </div><br>""", unsafe_allow_html=True)

    st.subheader("🗳️ Council Votes")
    votes = data["council"].get("votes", [])
    cols = st.columns(5)
    for i, vote in enumerate(votes):
        with cols[i % 5]:
            color = "#2ea043" if vote["status"] == "APPROVED" else "#da3633"
            icon = AGENT_ICONS.get(vote["agent"], "🤖")
            st.markdown(f"""<div class="net-card">
                <h4>{icon} {vote['agent']}</h4>
                <p><span style="color:{color}; font-weight:bold;">{vote['status']}</span>
                   <span style="color:#8b949e;"> {vote['confidence']}</span></p>
                <p><small>{vote['reason']}</small></p>
            </div>""", unsafe_allow_html=True)

    approved = data["council"].get("approved_count", "—")
    total    = data["council"].get("total_count", 10)
    passed   = data["council"]["consensus_passed"]
    c_color  = "#2ea043" if passed else "#da3633"
    c_text   = f"{'PASSED' if passed else 'REJECTED'} — {approved}/{total} ({data['council']['consensus_score']})"
    st.markdown(f"""<div class="net-card" style="text-align:center;">
        <h4>🗳️ Consensus</h4>
        <h3 style="color:{c_color} !important;">{c_text}</h3>
        <p><small>Threshold: RiskOfficer ✓ + ≥70% approval</small></p>
    </div>""", unsafe_allow_html=True)

    st.subheader("🔵 Execution")
    ex = data["execution"]
    col_ex, col_link = st.columns([3, 1])
    with col_ex:
        st.markdown(f"**Order ID:** `{ex['order_id']}` &nbsp;·&nbsp; "
                    f"**Exchange:** `{ex['exchange']}` &nbsp;·&nbsp; "
                    f"**Mode:** `{ex['mode']}`", unsafe_allow_html=True)
    with col_link:
        st.markdown(f'<a href="{ex["okx_url"]}" target="_blank" style="background:#1a6cff;'
                    f'color:#fff !important;padding:8px 16px;border-radius:6px;'
                    f'font-weight:bold;display:inline-block;">View on OKX ↗</a>',
                    unsafe_allow_html=True)

    st.caption(f"Auto-refreshing · Last updated: {data['timestamp']}")
    if st.session_state.get("_just_ran"):
        st.session_state["_just_ran"] = False
        time.sleep(2)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — SETUP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Setup":
    st.title("⚙️ Agent Setup")
    st.caption("Configure how the council behaves. Changes take effect on the next run.")

    s = settings  # already loaded in sidebar

    st.subheader("💰 Capital & Position Sizing")
    col1, col2 = st.columns(2)
    with col1:
        budget = st.number_input(
            "Total budget (USD)",
            min_value=10.0, max_value=100000.0, value=float(s["budget_usd"]), step=10.0,
            help="How much money you want the system to manage in total.",
        )
    with col2:
        max_tx = st.number_input(
            "Max amount per trade (USD)",
            min_value=1.0, max_value=budget, value=float(s["max_tx_usd"]), step=0.5,
            help="The maximum the council is allowed to spend on a single trade. "
                 "Keeping this small limits your downside on any one decision.",
        )

    st.subheader("⚖️ Risk Strategy")
    risk = st.select_slider(
        "Risk level",
        options=["conservative", "moderate", "aggressive"],
        value=s["risk_strategy"],
        help="Conservative: tighter RSI limits, smaller positions. "
             "Aggressive: wider thresholds, full position sizing.",
    )
    risk_explain = {
        "conservative": "🔵 Safe mode — the RiskOfficer will veto anything with RSI above 60 on a BUY. "
                        "Prioritises not losing money over making it.",
        "moderate":     "🟡 Balanced — standard thresholds (RSI < 70 for BUY). "
                        "Good mix of opportunity and caution.",
        "aggressive":   "🔴 High risk / high reward — RSI up to 78 allowed on a BUY. "
                        "More trades will get through, but more can also go wrong.",
    }[risk]
    st.info(risk_explain)

    st.subheader("🛡️ Portfolio Protection")
    col3, col4 = st.columns(2)
    with col3:
        max_ratio = st.slider(
            "Max single-token allocation (%)",
            min_value=5, max_value=100, value=int(s["max_commodity_ratio"]), step=5,
            help="If one token already makes up this % of your portfolio, "
                 "the RiskOfficer will veto buying more of it. "
                 "Prevents over-concentration in one asset.",
        )
    with col4:
        max_daily = st.number_input(
            "Max trades per day",
            min_value=1, max_value=50, value=int(s["max_daily_trades"]), step=1,
            help="Hard limit on how many trades the council can execute in 24 hours.",
        )

    col5, col6 = st.columns(2)
    with col5:
        stop_loss = st.number_input(
            "Stop-loss (%)",
            min_value=1.0, max_value=50.0, value=float(s["stop_loss_pct"]), step=0.5,
            help="If a position drops by this percentage, sell automatically. "
                 "For example, 5% means sell if price falls 5% from your entry.",
        )
    with col6:
        take_profit = st.number_input(
            "Take-profit (%)",
            min_value=1.0, max_value=200.0, value=float(s["take_profit_pct"]), step=1.0,
            help="If a position rises by this percentage, sell to lock in gains.",
        )

    st.subheader("🤖 Execution")
    auto_exec = st.toggle(
        "Allow automatic execution (no human approval)",
        value=bool(s["auto_execute"]),
        help="When OFF (default), the council will propose a trade and wait for you to approve it. "
             "When ON, approved trades execute immediately without asking you first. "
             "Only turn this ON if you trust the system completely.",
    )
    if auto_exec:
        st.warning("⚠️ Auto-execution is ON. Approved trades will be placed immediately without your review.")

    st.divider()
    if st.button("💾 Save Settings", type="primary"):
        new_settings = {
            "budget_usd": budget,
            "risk_strategy": risk,
            "max_tx_usd": max_tx,
            "max_commodity_ratio": max_ratio,
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
            "max_daily_trades": max_daily,
            "auto_execute": auto_exec,
        }
        save_settings(new_settings)
        st.success("Settings saved! They'll apply on the next council run.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 Portfolio":
    st.title("💼 Portfolio")
    st.caption("Your OKX demo account holdings, pulled live via ATK.")

    if st.button("🔄 Refresh"):
        st.rerun()

    with st.spinner("Fetching balance from OKX…"):
        try:
            from src.okx_client import get_balance
            raw = run_async(get_balance(demo=True))
        except Exception as e:
            st.error(f"Could not fetch balance: {e}")
            raw = []

    # ATK returns [{..., "totalEq": "...", "details": [...]}]
    account   = raw[0] if raw else {}
    holdings  = account.get("details", [])
    total_usd = float(account.get("totalEq") or 0)

    if holdings:
        st.metric("Total Account Value", f"${total_usd:,.2f}")
        st.divider()
        st.subheader("Holdings")

        cols = st.columns(3)
        for i, h in enumerate(holdings):
            ccy       = h.get("ccy", "?")
            eq        = float(h.get("eq") or 0)
            avail     = float(h.get("availBal") or 0)
            eq_usd    = float(h.get("eqUsd") or 0)
            upl       = float(h.get("spotUpl") or 0)
            upl_pct   = float(h.get("spotUplRatio") or 0) * 100
            avg_px    = float(h.get("openAvgPx") or 0)
            pct_port  = (eq_usd / total_usd * 100) if total_usd > 0 else 0
            bar       = "█" * int(pct_port / 5) + "░" * (20 - int(pct_port / 5))
            upl_color = "#3fb950" if upl >= 0 else "#f85149"

            with cols[i % 3]:
                st.markdown(f"""<div class="net-card">
                    <h4>{ccy}</h4>
                    <p><strong>Balance:</strong> {eq:,.6g}
                       &nbsp;·&nbsp; <strong>≈ ${eq_usd:,.2f}</strong></p>
                    <p><strong>Available:</strong> {avail:,.6g}</p>
                    {f'<p><strong>Avg buy:</strong> ${avg_px:,.4f}</p>' if avg_px > 0 else ''}
                    {f'<p><strong>P&amp;L:</strong> <span style="color:{upl_color};">{upl:+.4f} ({upl_pct:+.2f}%)</span></p>' if upl != 0 else ''}
                    <p style="color:#8b949e;font-size:11px;">{bar} {pct_port:.1f}% of portfolio</p>
                </div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("💡 What does this mean?")
        s = settings
        st.info(
            f"**Your setup:** Budget ${s['budget_usd']:.0f} · "
            f"Max {s['max_commodity_ratio']}% in one token · "
            f"Max ${s['max_tx_usd']:.2f} per trade\n\n"
            "**Diversification tip:** Spreading your holdings across multiple tokens reduces risk. "
            "If one token crashes, the others cushion the blow. "
            f"The council will not buy more of any token that already exceeds "
            f"{s['max_commodity_ratio']}% of your portfolio."
        )
    else:
        st.info("No holdings data available. Make sure your OKX API key is configured.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜 History":
    st.title("📜 Transaction History")
    st.caption("Every council run is logged here — approved or rejected.")

    history = load_history()

    if not history:
        st.info("No history yet. Run the council from the Dashboard to see results here.")
        st.stop()

    for i, entry in enumerate(history):
        prop   = entry.get("proposal", {})
        action = prop.get("action", "?")
        token  = prop.get("token", "?")
        amount = prop.get("amount_usd", 0)
        status = entry.get("status", "?")
        ts     = entry.get("timestamp", "")
        votes  = entry.get("council", {})
        approved = votes.get("approved_count", "?")
        total    = votes.get("total_count", 10)
        score    = votes.get("consensus_score", "?")

        action_color = {"BUY": "#3fb950", "SELL": "#f85149", "HOLD": "#d29922"}.get(action, "#c9d1d9")
        status_color = {"EXECUTED": "#3fb950", "REJECTED": "#f85149", "PENDING_EXECUTION": "#d29922"}.get(status, "#c9d1d9")

        with st.expander(f"{'✅' if status == 'EXECUTED' else '❌' if status == 'REJECTED' else '⏳'} "
                         f"[{ts[:16]}]  {action} {token}  ·  ${amount}  ·  {status}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Action:** <span style='color:{action_color};'>{action} {token}</span>",
                            unsafe_allow_html=True)
                st.markdown(f"**Amount:** ${amount}")
                st.markdown(f"**Status:** <span style='color:{status_color};'>{status}</span>",
                            unsafe_allow_html=True)
                st.markdown(f"**Order ID:** `{entry.get('execution', {}).get('order_id', '—')}`")
            with col_b:
                st.markdown(f"**Vote:** {approved}/{total} approved ({score})")
                st.markdown(f"**RSI:** {entry.get('technical', {}).get('rsi', '—')}")
                st.markdown(f"**Sentiment:** {entry.get('sentiment', {}).get('score', '—')}")
            st.markdown(f"*{prop.get('rationale', '')}*")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Assistant":
    st.title("🤖 CouncilBot — Your Crypto Guide")
    st.caption("Ask anything about what the council did, why, or what crypto terms mean. "
               "This is an educational tool — not financial advice.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    data    = load_decision()
    history = load_history()
    # settings already loaded in sidebar

    def _build_system() -> str:
        if data:
            decision_summary = (
                f"Latest decision: {data['proposal']['action']} {data['proposal']['token']} "
                f"${data['proposal']['amount_usd']} — Status: {data['status']} — "
                f"Votes: {data['council'].get('approved_count','?')}/{data['council'].get('total_count',10)} approved. "
                f"Rationale: {data['proposal']['rationale']}. "
                f"RSI: {data['technical']['rsi']} ({data['technical']['verdict']}). "
                f"Sentiment: {data['sentiment']['score']:+.2f}. "
                "Individual votes: " + "; ".join(
                    f"{v['agent']}: {v['status']} ({v['confidence']}) — {v['reason']}"
                    for v in data['council'].get('votes', [])
                )
            )
        else:
            decision_summary = "No decision has been run yet."

        recent = ""
        if history:
            recent = "Recent history: " + " | ".join(
                f"{h['proposal']['action']} {h['proposal']['token']} → {h['status']}"
                for h in history[:5]
            )

        return f"""You are CouncilBot, a friendly and patient crypto education assistant inside CouncilTrade.
Your job is to help people who are NEW to crypto understand what the AI trading council is doing and why.

Current council configuration:
- Budget: ${settings['budget_usd']:.0f}
- Risk strategy: {settings['risk_strategy']}
- Max per trade: ${settings['max_tx_usd']:.2f}
- Max single-token allocation: {settings['max_commodity_ratio']}%
- Auto-execution: {'enabled' if settings['auto_execute'] else 'disabled (user approves each trade)'}

{decision_summary}
{recent}

Your communication rules:
- Use very simple, plain English. Avoid jargon — if you must use a term, explain it immediately.
- RSI = Relative Strength Index, a number 0-100 that shows if an asset is overbought (>70) or oversold (<30).
- Sentiment score = a number from -1.0 (very negative mood) to +1.0 (very positive mood) about the asset.
- BUY = using USD to purchase the token. SELL = converting the token back to USD. HOLD = do nothing.
- Always remind users this is a DEMO — no real money is at risk.
- Be warm, encouraging and educational. Never make users feel stupid for not knowing something.
- When explaining why a vote happened, reference the actual reason from the vote data above.
- If asked about the council members, explain their role in plain terms.
- Never give real financial advice. Always note that crypto is risky and this is for learning only.
"""

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"] if msg["role"] != "model" else "assistant"):
            st.markdown(msg["content"])

    # Suggested questions for new users
    if not st.session_state.chat_history:
        st.markdown("**Not sure what to ask? Try one of these:**")
        suggestions = [
            "Why did the council make that decision?",
            "What is RSI and why does it matter?",
            "Which agent vetoed the trade and why?",
            "What does the Risk Officer actually do?",
            "Is this safe? Could I lose real money?",
        ]
        cols = st.columns(len(suggestions))
        for i, q in enumerate(suggestions):
            if cols[i].button(q, key=f"sug_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": q})
                st.rerun()

    if prompt := st.chat_input("Ask CouncilBot anything…"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.rerun()

    # Generate response for the last unanswered user message
    if (st.session_state.chat_history
            and st.session_state.chat_history[-1]["role"] == "user"):
        with st.chat_message("assistant"):
            with st.spinner("CouncilBot is thinking…"):
                try:
                    contents = [
                        _types.Content(
                            role="user" if msg["role"] == "user" else "model",
                            parts=[_types.Part(text=msg["content"])]
                        )
                        for msg in st.session_state.chat_history
                    ]
                    response = _assistant_client.models.generate_content(
                        model="gemini-flash-lite-latest",
                        contents=contents,
                        config=_types.GenerateContentConfig(
                            system_instruction=_build_system(),
                            max_output_tokens=1024,
                        ),
                    )
                    answer = response.text
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "model", "content": answer})
                except Exception as e:
                    err = f"CouncilBot error: {e}"
                    st.error(err)
                    st.session_state.chat_history.append({"role": "model", "content": err})
