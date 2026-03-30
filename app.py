"""
Cloud Migration Decision Support System (CMDSS)
Integrated Streamlit Application — All Phases
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import sys
import os

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from engines.cost_engine import calculate_onprem_tco, calculate_manual_tco
from engines.cloud_cost_engine import run_cloud_analysis
from engines.risk_engine import calculate_risk_adjustment, risk_adjusted_tco
from engines.rule_engine import recommend_strategy, recommend_dr, get_migration_roadmap
from engines.decision_engine import recommend_strategy as financial_recommend
from ml.predict_strategy import predict_strategy


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CMDSS — Cloud Migration Decision Support System",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label { color: #94a3b8 !important; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
    }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }

    /* Section headers */
    .section-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
        border-left: 4px solid #2563eb;
        border-radius: 0 8px 8px 0;
        padding: 12px 20px;
        margin: 20px 0 16px 0;
        font-size: 1.1rem;
        font-weight: 600;
        color: #e2e8f0;
    }

    /* Strategy badges */
    .badge-blue   { background:#1d4ed8; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-green  { background:#15803d; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-orange { background:#c2410c; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-purple { background:#7e22ce; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }

    /* Roadmap steps */
    .roadmap-step {
        background: #1e293b;
        border-left: 3px solid #2563eb;
        padding: 10px 16px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        color: #e2e8f0;
        font-size: .93rem;
    }

    /* Decision path rules */
    .rule-step {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 14px;
        margin: 4px 0;
        font-family: monospace;
        font-size: .85rem;
        color: #7dd3fc;
    }

    /* Info box */
    .info-box {
        background: #0c2340;
        border: 1px solid #1d4ed8;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #bfdbfe;
        font-size: .9rem;
    }

    /* Warning box */
    .warn-box {
        background: #2d1b00;
        border: 1px solid #d97706;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #fde68a;
        font-size: .9rem;
    }

    /* Provider comparison table */
    .provider-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #1e293b;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 6px 0;
        border: 1px solid #334155;
    }
    .provider-row.best { border-color: #22c55e; background: #052e16; }

    div[data-testid="stForm"] { border: none; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
for key in ["tco_result", "cloud_analysis", "servers", "storage_tb",
            "cpu_util", "ram_util", "pricing_model"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☁️ CMDSS")
    st.markdown("**Cloud Migration Decision Support System**")
    st.divider()

    st.markdown("### ⚙️ Global Settings")

    pricing_model = st.selectbox(
        "Pricing Model",
        ["on_demand", "reserved_1yr", "reserved_3yr"],
        format_func=lambda x: {
            "on_demand":    "On-Demand (no commitment)",
            "reserved_1yr": "Reserved 1-Year (~35% off)",
            "reserved_3yr": "Reserved 3-Year (~55% off)"
        }[x],
        help="Applies to cloud cost calculations across all tabs"
    )
    st.session_state["pricing_model"] = pricing_model

    st.divider()
    st.markdown("### 📊 System Status")

    if st.session_state["tco_result"]:
        st.success(f"✅ On-Prem TCO loaded\n\n**{st.session_state['servers']} servers** · **{st.session_state['storage_tb']} TB**")
    else:
        st.info("⏳ No infrastructure loaded yet.\nComplete Tab 1 first.")

    if st.session_state["cloud_analysis"]:
        bp = st.session_state["cloud_analysis"]["best_provider"]
        cost = st.session_state["cloud_analysis"]["costs"][bp]["selected"]
        st.success(f"✅ Cloud analysis done\n\nBest: **{bp}** @ **${cost:,.0f}/yr**")

    st.divider()
    st.caption("Phases: Cost · Risk · Rules · ML · Multi-Cloud")


# ── Title bar ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
            border-radius:12px;padding:24px 32px;margin-bottom:24px;
            border:1px solid #1d4ed8;">
  <h1 style="color:white;margin:0;font-size:1.8rem;">
    ☁️ Cloud Migration Decision Support System
  </h1>
  <p style="color:#94a3b8;margin:6px 0 0 0;font-size:.95rem;">
    End-to-end infrastructure analysis · TCO modelling · Risk assessment · AI strategy recommendation
  </p>
</div>
""", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Phase 1 — Infrastructure & TCO",
    "💰 Phase 2 — Cost Analysis",
    "⚠️ Phase 3 — Risk Analysis",
    "🧭 Phase 4 — Strategy & Rules",
    "🤖 Phase 5 — ML Prediction"
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — Infrastructure & TCO
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    st.markdown('<div class="section-header">📦 Infrastructure Input & On-Premise TCO</div>',
                unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1.6], gap="large")

    with col_left:
        st.markdown("#### Select Input Method")
        input_method = st.radio(
            "Input Method",
            ["Upload Infrastructure Dataset", "Enterprise Preset", "Manual Inputs"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # ── Input mode ──
        if input_method == "Upload Infrastructure Dataset":
            uploaded_file = st.file_uploader(
                "Upload Infrastructure Excel (.xlsx)",
                type=["xlsx"],
                help="Requires columns: 'Quantity' and 'Storage (TB) per Server'"
            )
            if uploaded_file:
                try:
                    result = calculate_onprem_tco(file_path=uploaded_file)
                    st.session_state["tco_result"] = result
                    st.session_state["servers"]    = result["servers"]
                    st.session_state["storage_tb"] = result["storage_tb"]
                    st.success(f"✅ Loaded: **{result['servers']} servers**, **{result['storage_tb']} TB**")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        elif input_method == "Enterprise Preset":
            preset = st.selectbox(
                "Enterprise Size",
                ["small", "medium", "large"],
                format_func=lambda x: {
                    "small":  "Small  (8 servers · 5 TB)",
                    "medium": "Medium (21 servers · 18 TB)",
                    "large":  "Large  (120 servers · 120 TB)"
                }[x]
            )
            if st.button("▶ Load Preset", use_container_width=True):
                result = calculate_onprem_tco(preset=preset)
                st.session_state["tco_result"] = result
                st.session_state["servers"]    = result["servers"]
                st.session_state["storage_tb"] = result["storage_tb"]
                st.success(f"✅ Preset loaded: **{result['servers']} servers**, **{result['storage_tb']} TB**")

        elif input_method == "Manual Inputs":
            servers_input    = st.number_input("Number of Servers",  min_value=1, value=20)
            storage_input    = st.number_input("Storage (TB)",        min_value=1.0, value=10.0, step=1.0)
            if st.button("▶ Calculate TCO", use_container_width=True):
                result = calculate_manual_tco(servers=servers_input, storage_tb=storage_input)
                st.session_state["tco_result"] = result
                st.session_state["servers"]    = result["servers"]
                st.session_state["storage_tb"] = result["storage_tb"]
                st.success(f"✅ Calculated: **{result['servers']} servers**, **{result['storage_tb']} TB**")

        # ── Utilisation inputs (always visible) ──
        st.markdown("---")
        st.markdown("#### Server Utilisation")
        vcpu_input    = st.number_input("vCPU per Server",       min_value=1,   value=8)
        ram_input     = st.number_input("RAM per Server (GB)",   min_value=1,   value=32)
        cpu_util      = st.slider("CPU Utilisation (%)",         10, 100, 60,   step=5)
        ram_util      = st.slider("RAM Utilisation (%)",         10, 100, 70,   step=5)

        st.session_state["cpu_util"] = cpu_util
        st.session_state["ram_util"] = ram_util

        if st.session_state["servers"] and st.button("☁️ Run Cloud Analysis", use_container_width=True, type="primary"):
            try:
                analysis = run_cloud_analysis(
                    current_vcpu=vcpu_input,
                    current_ram=ram_input,
                    cpu_utilization=cpu_util,
                    ram_utilization=ram_util,
                    servers=st.session_state["servers"],
                    pricing_model=pricing_model
                )
                st.session_state["cloud_analysis"] = analysis
                st.session_state["vcpu_input"] = vcpu_input
                st.session_state["ram_input"]  = ram_input
                st.success("✅ Cloud analysis complete — see other tabs!")
            except Exception as e:
                st.error(f"Cloud analysis error: {e}")

    with col_right:
        result = st.session_state["tco_result"]

        if result:
            st.markdown("#### On-Premise TCO Results")

            # ── TCO headline metrics ──
            m1, m2, m3 = st.columns(3)
            m1.metric("Annual OpEx",  f"${result['annual_operational_cost']:,.0f}")
            m2.metric("3-Year TCO",   f"${result['tco_3yr']:,.0f}")
            m3.metric("5-Year TCO",   f"${result['tco_5yr']:,.0f}")

            st.markdown("---")

            # ── Cost breakdown chart ──
            cost_items = {
                "Hardware CapEx":    result["hardware_cost"],
                "Storage CapEx":     result["storage_capex"],
                "Maintenance":       result["annual_maintenance"],
                "Power & Cooling":   result["annual_power"],
                "IT Staff":          result["annual_staff"],
                "Storage OpEx":      result["annual_storage_opex"],
            }
            df_costs = pd.DataFrame({
                "Category": list(cost_items.keys()),
                "Amount":   list(cost_items.values())
            })

            fig_donut = px.pie(
                df_costs, values="Amount", names="Category",
                title="Cost Breakdown",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                title_font_size=14,
                legend=dict(font=dict(size=11)),
                margin=dict(t=50, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

            # ── TCO projection line chart ──
            years = [1, 2, 3, 4, 5]
            capex = result["total_capex"]
            opex  = result["annual_operational_cost"]
            tco_vals = [capex + opex * y for y in years]

            fig_line = px.line(
                x=years, y=tco_vals,
                title="TCO Projection (5 Years)",
                markers=True,
                labels={"x": "Year", "y": "Cumulative Cost ($)"}
            )
            fig_line.update_traces(line_color="#2563eb", line_width=3, marker_size=8)
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0",
                title_font_size=14,
                margin=dict(t=50, b=30, l=10, r=10),
                xaxis=dict(gridcolor="#334155"),
                yaxis=dict(gridcolor="#334155")
            )
            st.plotly_chart(fig_line, use_container_width=True)

            # ── Right-sizing preview if cloud analysis done ──
            analysis = st.session_state["cloud_analysis"]
            if analysis:
                st.markdown("#### Right-Sizing Result")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("vCPU (Before)",  analysis["original_vcpu"])
                r2.metric("vCPU (After)",   analysis["recommended_vcpu"],
                          delta=f"-{analysis['cpu_reduction_pct']}%")
                r3.metric("RAM (Before)",   f"{analysis['original_ram']} GB")
                r4.metric("RAM (After)",    f"{analysis['recommended_ram']} GB",
                          delta=f"-{analysis['ram_reduction_pct']}%")

                st.markdown(f"""
                <div class="info-box">
                  🔬 <b>Workload Type:</b> {analysis['workload_type'].capitalize()} —
                  Right-sized from <b>{analysis['original_vcpu']} vCPU / {analysis['original_ram']} GB</b>
                  to <b>{analysis['recommended_vcpu']} vCPU / {analysis['recommended_ram']} GB</b>
                  using actual utilisation + 30% safety buffer.
                </div>
                """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="info-box" style="margin-top:40px;text-align:center;">
              <h3 style="color:#60a5fa;">👈 Select an input method</h3>
              <p>Choose Upload, Preset, or Manual on the left to calculate your on-premise TCO.</p>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — Cost Analysis
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    result   = st.session_state["tco_result"]
    analysis = st.session_state["cloud_analysis"]

    if not result:
        st.markdown('<div class="warn-box">⚠️ Complete <b>Phase 1 (Tab 1)</b> first to load infrastructure data.</div>',
                    unsafe_allow_html=True)
    elif not analysis:
        st.markdown('<div class="warn-box">⚠️ Run <b>Cloud Analysis</b> in Tab 1 to enable cost comparison.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-header">💰 On-Premise vs Cloud Cost Analysis</div>',
                    unsafe_allow_html=True)

        best_provider   = analysis["best_provider"]
        cloud_yearly    = analysis["costs"][best_provider]["selected"]
        onprem_annual   = result["annual_operational_cost"]
        onprem_5yr      = result["tco_5yr"]
        cloud_5yr       = cloud_yearly * 5
        savings_5yr     = onprem_5yr - cloud_5yr
        savings_pct     = (savings_5yr / onprem_5yr) * 100 if onprem_5yr else 0

        # ── Headline metrics ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("On-Prem Annual",   f"${onprem_annual:,.0f}")
        c2.metric("Cloud Annual (Best)", f"${cloud_yearly:,.0f}",
                  delta=f"-${onprem_annual - cloud_yearly:,.0f}")
        c3.metric("5-Year Savings",   f"${savings_5yr:,.0f}",
                  delta=f"{savings_pct:.1f}%")
        c4.metric("Best Provider",    best_provider)

        st.markdown("---")

        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("#### 5-Year TCO Comparison")

            fig_bar = go.Figure(data=[
                go.Bar(name="On-Premise", x=["On-Premise"], y=[onprem_5yr],
                       marker_color="#ef4444", text=[f"${onprem_5yr:,.0f}"],
                       textposition="auto"),
                go.Bar(name=f"Cloud ({best_provider})", x=[f"Cloud ({best_provider})"],
                       y=[cloud_5yr], marker_color="#22c55e",
                       text=[f"${cloud_5yr:,.0f}"], textposition="auto")
            ])
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0",
                showlegend=False,
                margin=dict(t=20, b=20),
                yaxis=dict(gridcolor="#334155")
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            st.markdown("#### Year-by-Year Cost Trajectory")

            years = list(range(1, 6))
            onprem_capex  = result["total_capex"]
            onprem_opex   = result["annual_operational_cost"]
            onprem_cumul  = [onprem_capex + onprem_opex * y for y in years]
            cloud_cumul   = [cloud_yearly * y for y in years]

            fig_traj = go.Figure()
            fig_traj.add_trace(go.Scatter(
                x=years, y=onprem_cumul, name="On-Premise",
                line=dict(color="#ef4444", width=3), mode="lines+markers"
            ))
            fig_traj.add_trace(go.Scatter(
                x=years, y=cloud_cumul, name=f"Cloud ({best_provider})",
                line=dict(color="#22c55e", width=3), mode="lines+markers"
            ))
            fig_traj.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0",
                margin=dict(t=20, b=20),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(title="Year", gridcolor="#334155"),
                yaxis=dict(title="Cumulative Cost ($)", gridcolor="#334155")
            )
            st.plotly_chart(fig_traj, use_container_width=True)

        # ── All providers comparison ──
        st.markdown("#### Multi-Provider Annual Cost Comparison")
        st.markdown(f"*Pricing model: **{pricing_model.replace('_', ' ').title()}***")

        provider_rows = []
        for provider, cost_data in analysis["costs"].items():
            sel_cost = cost_data["selected"]
            saving   = onprem_annual - sel_cost
            saving_p = (saving / onprem_annual) * 100 if onprem_annual else 0
            provider_rows.append({
                "Provider":      provider,
                "Annual Cost":   sel_cost,
                "vs On-Prem":    saving,
                "Savings %":     saving_p,
                "Instance":      analysis["instances"][provider]["instance"],
                "vCPU":          analysis["instances"][provider]["vcpu"],
                "RAM (GB)":      analysis["instances"][provider]["ram_gb"],
                "Best":          provider == best_provider
            })

        prov_df = pd.DataFrame(provider_rows)

        # Visual provider cards
        for _, row in prov_df.iterrows():
            css_class = "provider-row best" if row["Best"] else "provider-row"
            badge     = "⭐ BEST" if row["Best"] else ""
            color     = "#22c55e" if row["vs On-Prem"] > 0 else "#ef4444"
            arrow     = "▼" if row["vs On-Prem"] > 0 else "▲"
            st.markdown(f"""
            <div class="{css_class}">
              <div><b>{row['Provider']}</b> {badge}</div>
              <div style="color:#94a3b8;font-size:.85rem;">{row['Instance']} · {row['vCPU']} vCPU · {row['RAM (GB)']} GB</div>
              <div style="font-size:1.2rem;font-weight:700;">${row['Annual Cost']:,.0f}</div>
              <div style="color:{color};font-weight:600;">{arrow} ${abs(row['vs On-Prem']):,.0f} ({abs(row['Savings %']):.1f}%)</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Pricing model comparison for best provider ──
        st.markdown(f"#### Pricing Model Breakdown — {best_provider}")
        costs_bp = analysis["costs"][best_provider]
        models   = ["on_demand", "reserved_1yr", "reserved_3yr"]
        labels   = ["On-Demand", "Reserved 1-Year", "Reserved 3-Year"]
        vals     = [costs_bp[m] for m in models]
        colors   = ["#94a3b8", "#60a5fa", "#2563eb"]

        fig_pm = go.Figure(go.Bar(
            x=labels, y=vals,
            marker_color=colors,
            text=[f"${v:,.0f}" for v in vals],
            textposition="auto"
        ))
        fig_pm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.8)",
            font_color="#e2e8f0",
            margin=dict(t=10, b=10),
            yaxis=dict(gridcolor="#334155")
        )
        st.plotly_chart(fig_pm, use_container_width=True)

        # ── Financial decision from decision_engine ──
        st.markdown("#### Financial Migration Decision")
        try:
            financial_decision = financial_recommend(
                onprem_cost=onprem_annual,
                cloud_costs=analysis["costs"],
                pricing_model=pricing_model
            )
            summary = financial_decision.get("_summary", {})

            if summary.get("overall_recommendation") == "Migrate to Cloud":
                st.success(f"✅ **Recommendation: Migrate to Cloud**")
                cols = st.columns(3)
                cols[0].metric("Best Provider",  summary.get("best_cloud_option", "N/A"))
                cols[1].metric("Annual Savings", f"${summary.get('best_savings', 0):,.0f}")
                cols[2].metric("Confidence",     summary.get("confidence", "N/A"))
                st.info(f"💡 **Strategy:** {summary.get('strategy', 'N/A')} — {summary.get('reason', '')}")
            else:
                st.warning("⚠️ **Recommendation: Stay On-Prem** — No cloud provider offers sufficient savings.")

            with st.expander("📊 Full Per-Provider Decision Breakdown"):
                for prov, data in financial_decision.items():
                    if prov == "_summary":
                        continue
                    st.markdown(f"**{prov}** — {data['recommendation']} | "
                                f"Savings: ${data['savings']:,.0f} ({data['savings_pct']:.1f}%) | "
                                f"Confidence: {data['confidence']} | Strategy: {data['strategy']}")
        except Exception as e:
            st.warning(f"Decision engine error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — Risk Analysis
# ══════════════════════════════════════════════════════════════════════════════
with tab3:

    result   = st.session_state["tco_result"]
    analysis = st.session_state["cloud_analysis"]

    if not result or not analysis:
        st.markdown('<div class="warn-box">⚠️ Complete <b>Phase 1 (Tab 1)</b> and run Cloud Analysis first.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-header">⚠️ Migration Risk Analysis</div>',
                    unsafe_allow_html=True)

        col_inputs, col_results = st.columns([1, 1.4], gap="large")

        with col_inputs:
            st.markdown("#### Risk Parameters")

            st.markdown("**🔴 Downtime Risk**")
            downtime_risk  = st.slider("Downtime Probability",  0.0, 1.0, 0.10, 0.01,
                                       help="Probability that significant downtime occurs during migration")
            downtime_cost  = st.number_input("Downtime Cost ($)", value=50000, step=5000)

            st.markdown("**🟡 Compliance Risk**")
            compliance_risk    = st.slider("Compliance Probability",   0.0, 1.0, 0.05, 0.01)
            compliance_penalty = st.number_input("Compliance Penalty ($)", value=100000, step=10000)

            st.markdown("**🟢 Skill Gap Risk**")
            skill_risk     = st.slider("Skill Gap Probability",  0.0, 1.0, 0.20, 0.01)
            training_cost  = st.number_input("Training Cost ($)", value=20000, step=2000)

        with col_results:
            try:
                risk = calculate_risk_adjustment(
                    downtime_risk, downtime_cost,
                    compliance_risk, compliance_penalty,
                    skill_risk, training_cost
                )

                best_provider  = analysis["best_provider"]
                cloud_yearly   = analysis["costs"][best_provider]["selected"]
                onprem_annual  = result["annual_operational_cost"]

                adj_cloud_cost = risk_adjusted_tco(cloud_yearly, risk)
                adj_savings    = onprem_annual - adj_cloud_cost
                adj_savings_p  = (adj_savings / onprem_annual * 100) if onprem_annual else 0

                st.markdown("#### Risk-Adjusted Results")

                m1, m2 = st.columns(2)
                m1.metric("Total Risk Cost",          f"${risk['total_risk_cost']:,.0f}")
                m2.metric("Risk-Adjusted Cloud Cost", f"${adj_cloud_cost:,.0f}",
                          delta=f"+${risk['total_risk_cost']:,.0f} risk")

                m3, m4 = st.columns(2)
                m3.metric("Base Cloud Cost",   f"${cloud_yearly:,.0f}")
                m4.metric("Adjusted Savings",  f"${adj_savings:,.0f}",
                          delta=f"{adj_savings_p:.1f}% vs on-prem")

                # ── Risk breakdown chart ──
                fig_risk = go.Figure(go.Bar(
                    x=["Downtime Risk", "Compliance Risk", "Skill Gap Risk"],
                    y=[risk["downtime_cost"], risk["compliance_cost"], risk["skill_cost"]],
                    marker_color=["#ef4444", "#f59e0b", "#22c55e"],
                    text=[f"${v:,.0f}" for v in [
                        risk["downtime_cost"], risk["compliance_cost"], risk["skill_cost"]
                    ]],
                    textposition="auto"
                ))
                fig_risk.update_layout(
                    title="Expected Risk Cost Breakdown",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.8)",
                    font_color="#e2e8f0",
                    margin=dict(t=40, b=20),
                    yaxis=dict(gridcolor="#334155", title="Expected Cost ($)")
                )
                st.plotly_chart(fig_risk, use_container_width=True)

                # ── 5-year risk-adjusted comparison ──
                onprem_5yr   = result["tco_5yr"]
                cloud_5yr    = cloud_yearly * 5
                adj_cloud_5yr = adj_cloud_cost * 5

                fig_comp = go.Figure(data=[
                    go.Bar(name="On-Premise 5yr",        y=[onprem_5yr],    marker_color="#ef4444",
                           text=[f"${onprem_5yr:,.0f}"],    textposition="auto"),
                    go.Bar(name="Cloud 5yr (base)",       y=[cloud_5yr],     marker_color="#22c55e",
                           text=[f"${cloud_5yr:,.0f}"],     textposition="auto"),
                    go.Bar(name="Cloud 5yr (risk-adj.)",  y=[adj_cloud_5yr], marker_color="#f59e0b",
                           text=[f"${adj_cloud_5yr:,.0f}"], textposition="auto"),
                ])
                fig_comp.update_layout(
                    title="5-Year: On-Prem vs Cloud vs Risk-Adjusted Cloud",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.8)",
                    font_color="#e2e8f0",
                    margin=dict(t=40, b=20),
                    barmode="group",
                    yaxis=dict(gridcolor="#334155"),
                    legend=dict(bgcolor="rgba(0,0,0,0)")
                )
                st.plotly_chart(fig_comp, use_container_width=True)

                # ── Risk summary box ──
                if adj_savings > 0:
                    st.markdown(f"""
                    <div class="info-box">
                      ✅ Even after accounting for all migration risks,
                      <b>{best_provider}</b> saves <b>${adj_savings:,.0f}/year</b>
                      ({adj_savings_p:.1f}% cheaper than on-premise).
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="warn-box">
                      ⚠️ After risk adjustment, on-premise is more cost-effective by
                      <b>${abs(adj_savings):,.0f}/year</b>.
                      Consider reducing migration risks or renegotiating cloud pricing.
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Risk calculation error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — Strategy & Rules (Phase 3)
# ══════════════════════════════════════════════════════════════════════════════
with tab4:

    st.markdown('<div class="section-header">🧭 Rule-Based Strategy Recommendation</div>',
                unsafe_allow_html=True)

    col_in, col_out = st.columns([1, 1.5], gap="large")

    with col_in:
        st.markdown("#### Business Factors")

        compliance_sel = st.selectbox(
            "Compliance Level",
            ["low", "medium", "high"],
            format_func=lambda x: x.capitalize(),
            index=1,
            help="Regulatory and compliance requirements of your organisation"
        )
        downtime_sel = st.selectbox(
            "Downtime Tolerance",
            ["low", "medium", "high"],
            format_func=lambda x: x.capitalize(),
            index=1,
            help="How much downtime is acceptable during migration"
        )
        growth_sel = st.selectbox(
            "Expected Growth Rate",
            ["low", "medium", "high"],
            format_func=lambda x: x.capitalize(),
            index=1,
            help="Anticipated business / infrastructure growth"
        )

        st.markdown("---")
        st.markdown("""
        <div class="info-box">
          <b>Rule Logic:</b><br>
          • High compliance + Low downtime → <b>Hybrid</b><br>
          • High growth → <b>Cloud-Native</b><br>
          • Default → <b>Lift-and-Shift</b>
        </div>
        """, unsafe_allow_html=True)

    with col_out:
        try:
            # Explicitly cast to str and lowercase — guards against any type coercion
            _compliance = str(compliance_sel).strip().lower()
            _downtime   = str(downtime_sel).strip().lower()
            _growth     = str(growth_sel).strip().lower()

            strategy = recommend_strategy(_compliance, _downtime, _growth)
            dr_plan  = recommend_dr(_downtime)
            roadmap  = get_migration_roadmap(strategy)

            # Strategy badge
            badge_color = {
                "Lift-and-Shift":       "badge-blue",
                "Hybrid Migration":     "badge-orange",
                "Cloud-Native Migration": "badge-green"
            }.get(strategy, "badge-blue")

            st.markdown(f"""
            <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:16px;">
              <div style="color:#94a3b8;font-size:.85rem;margin-bottom:8px;">RECOMMENDED STRATEGY</div>
              <span class="{badge_color}" style="font-size:1rem;padding:8px 24px;">{strategy}</span>
            </div>
            """, unsafe_allow_html=True)

            # DR Plan
            dr_color = {"Hot DR": "#ef4444", "Warm DR": "#f59e0b", "Cold DR": "#22c55e"}.get(dr_plan, "#60a5fa")
            st.markdown(f"""
            <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:16px;">
              <div style="color:#94a3b8;font-size:.85rem;margin-bottom:8px;">DISASTER RECOVERY PLAN</div>
              <span style="color:{dr_color};font-size:1.2rem;font-weight:700;">🛡️ {dr_plan}</span>
            </div>
            """, unsafe_allow_html=True)

            # Roadmap
            st.markdown("#### Migration Roadmap")
            for step in roadmap:
                st.markdown(f'<div class="roadmap-step">🔷 {step}</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Strategy engine error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — ML Prediction (Phase 4 + 5)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:

    st.markdown('<div class="section-header">🤖 Machine Learning Strategy Prediction</div>',
                unsafe_allow_html=True)

    col_feat, col_pred = st.columns([1, 1.5], gap="large")

    with col_feat:
        st.markdown("#### Enterprise Feature Inputs")
        st.caption("These feed directly into the trained Decision Tree model.")

        # Auto-fill from Tab 1 if available
        default_servers  = st.session_state["servers"]  or 50
        default_storage  = st.session_state["storage_tb"] or 20.0
        default_cpu_util = st.session_state["cpu_util"]   or 60

        ml_servers   = st.number_input("Number of Servers",       min_value=5,   max_value=500, value=int(default_servers))
        ml_cpu       = st.number_input("Average CPU Utilisation (%)", min_value=10,  max_value=90,  value=min(int(default_cpu_util), 90))
        ml_storage   = st.number_input("Storage Size (TB)",       min_value=1.0, max_value=100.0, value=min(float(default_storage), 100.0), step=1.0)
        ml_downtime  = st.slider("Downtime Tolerance (hrs)",      0.5, 24.0, 4.0, 0.5)
        ml_compliance= st.select_slider("Compliance Level",       options=[1, 2, 3],
                                         format_func=lambda x: {1:"Low",2:"Medium",3:"High"}[x], value=2)
        ml_growth    = st.slider("Growth Rate (%)",               0, 40, 15)
        ml_budget    = st.select_slider("Budget Flexibility",     options=[1, 2, 3],
                                         format_func=lambda x: {1:"Tight",2:"Medium",3:"Flexible"}[x], value=2)

        if st.session_state["servers"]:
            st.markdown("""
            <div class="info-box" style="font-size:.8rem;">
              ℹ️ Server count and storage auto-filled from Phase 1.
            </div>
            """, unsafe_allow_html=True)

    with col_pred:
        features = {
            "server_count":       ml_servers,
            "avg_cpu_util":       ml_cpu,
            "storage_tb":         ml_storage,
            "downtime_tolerance": ml_downtime,
            "compliance_level":   ml_compliance,
            "growth_rate":        ml_growth,
            "budget_sensitivity": ml_budget
        }

        try:
            ml_result = predict_strategy(features)
            strategy_ml = ml_result["strategy"]

            # ── Prediction badge ──
            badge_map = {
                "Hybrid":          ("badge-orange", "🔀"),
                "Cloud-Native":    ("badge-green",  "☁️"),
                "Lift-and-Shift":  ("badge-blue",   "🚀")
            }
            badge_cls, icon = badge_map.get(strategy_ml, ("badge-purple", "🤖"))

            st.markdown(f"""
            <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:16px;text-align:center;">
              <div style="color:#94a3b8;font-size:.85rem;margin-bottom:12px;">ML PREDICTED STRATEGY</div>
              <span class="{badge_cls}" style="font-size:1.2rem;padding:10px 28px;">{icon} {strategy_ml}</span>
              <div style="color:#60a5fa;font-size:.95rem;margin-top:12px;">
                Confidence: <b>{ml_result['confidence']}</b>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_xai1, col_xai2 = st.columns(2)

            with col_xai1:
                st.markdown("#### 🔍 Top Influencing Factors")
                st.caption("Global XAI — feature importance across all predictions")
                for i, factor in enumerate(ml_result["top_factors"], 1):
                    importance_pct = [0.40, 0.30, 0.20][i - 1] if i <= 3 else 0.10  # approximate visual
                    st.markdown(f"""
                    <div style="background:#1e293b;border-radius:6px;padding:10px 14px;margin:5px 0;">
                      <div style="display:flex;justify-content:space-between;">
                        <span style="color:#e2e8f0;">#{i} {factor}</span>
                      </div>
                      <div style="background:#334155;border-radius:4px;height:6px;margin-top:6px;">
                        <div style="background:#2563eb;height:6px;border-radius:4px;width:{int(importance_pct*100)}%;"></div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_xai2:
                st.markdown("#### 🛣️ Decision Path")
                st.caption("Local XAI — exact rules used for this prediction")
                for rule in ml_result["decision_path"]:
                    st.markdown(f'<div class="rule-step">→ {rule}</div>', unsafe_allow_html=True)

            st.markdown("---")

            # ── Model performance section ──
            st.markdown("#### 📈 Model Performance")

            perf_col1, perf_col2 = st.columns(2)

            with perf_col1:
                st.markdown("**Confusion Matrix**")
                try:
                    cm_img = Image.open("models/confusion_matrix.png")
                    st.image(cm_img, use_container_width=True)
                except:
                    st.info("confusion_matrix.png not found in models/")

            with perf_col2:
                st.markdown("**Decision Tree Visualisation**")
                try:
                    dt_img = Image.open("models/decision_tree_visual.png")
                    st.image(dt_img, use_container_width=True,
                             caption="Trained Decision Tree (max_depth=5)")
                except:
                    st.info("decision_tree_visual.png not found in models/")

            # ── Feature importance bar chart ──
            st.markdown("#### Feature Importance (Global)")
            try:
                import joblib as jl
                model_loaded   = jl.load("models/decision_tree.pkl")
                feat_names     = ["server_count","avg_cpu_util","storage_tb",
                                  "downtime_tolerance","compliance_level",
                                  "growth_rate","budget_sensitivity"]
                feat_labels    = ["Servers","CPU Util","Storage","Downtime Tol.",
                                  "Compliance","Growth Rate","Budget Flex."]
                importances    = model_loaded.feature_importances_

                fi_df = pd.DataFrame({
                    "Feature":    feat_labels,
                    "Importance": importances
                }).sort_values("Importance", ascending=True)

                fig_fi = px.bar(
                    fi_df, x="Importance", y="Feature", orientation="h",
                    color="Importance",
                    color_continuous_scale=["#1e293b", "#2563eb", "#60a5fa"],
                    title="Decision Tree Feature Importances"
                )
                fig_fi.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.8)",
                    font_color="#e2e8f0",
                    margin=dict(t=40, b=10, l=10, r=10),
                    coloraxis_showscale=False,
                    yaxis=dict(gridcolor="#334155"),
                    xaxis=dict(gridcolor="#334155")
                )
                st.plotly_chart(fig_fi, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not load feature importances: {e}")

        except Exception as e:
            st.error(f"ML Prediction error: {e}")
            st.caption("Ensure models/decision_tree.pkl and models/label_encoder.pkl exist.")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#475569;font-size:.8rem;padding:10px 0;">
  Cloud Migration Decision Support System &nbsp;·&nbsp;
  Phase 1: TCO Engine &nbsp;·&nbsp; Phase 2: Cost Analysis &nbsp;·&nbsp;
  Phase 3: Risk Engine &nbsp;·&nbsp; Phase 4: Rule Engine &nbsp;·&nbsp;
  Phase 5: ML Prediction
</div>
""", unsafe_allow_html=True)
