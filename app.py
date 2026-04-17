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
import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from engines.cost_engine import calculate_onprem_tco, calculate_manual_tco, MIGRATION_ECONOMICS
from engines.cloud_cost_engine import run_cloud_analysis
from engines.risk_engine import calculate_risk_adjustment, risk_adjusted_tco
from engines.rule_engine import recommend_strategy, recommend_dr, get_migration_roadmap, check_technical_debt
from engines.decision_engine import recommend_strategy as financial_recommend, calculate_roi_timeline
from ml.zombie_detector import detect_zombie_servers
from ml.risk_nlp import analyze_migration_concerns
from ml.predict_strategy import run_system_audit, generate_friction_report, calculate_failure_probability
from report_generator import generate_html_report, generate_csv_export


# ── Currency: USD → INR ───────────────────────────────────────────────────────
USD_TO_INR = 84.0   # Update this rate as needed

def inr(usd_value: float, decimals: int = 0) -> str:
    val = usd_value * USD_TO_INR
    s = f"{val:,.{decimals}f}"
    parts = s.split(".")
    integer_str = parts[0].replace(",", "")
    neg = integer_str.startswith("-")
    if neg:
        integer_str = integer_str[1:]
    if len(integer_str) > 3:
        last3 = integer_str[-3:]
        rest  = integer_str[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted = ",".join(groups) + "," + last3
    else:
        formatted = integer_str
    if decimals > 0:
        formatted += "." + parts[1]
    sign = "-" if neg else ""
    return f"₹{sign}{formatted}"


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
    [data-testid="stSidebar"] { background-color: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label { color: #94a3b8 !important; }

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

    [data-testid="stMetric"] {
        background: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
    }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }

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

    .badge-blue   { background:#1d4ed8; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-green  { background:#15803d; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-orange { background:#c2410c; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }
    .badge-purple { background:#7e22ce; color:white; padding:4px 14px; border-radius:20px; font-weight:600; font-size:.85rem; }

    .roadmap-step {
        background: #1e293b;
        border-left: 3px solid #2563eb;
        padding: 10px 16px;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
        color: #e2e8f0;
        font-size: .93rem;
    }

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

    .info-box {
        background: #0c2340;
        border: 1px solid #1d4ed8;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #bfdbfe;
        font-size: .9rem;
    }

    .warn-box {
        background: #2d1b00;
        border: 1px solid #d97706;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #fde68a;
        font-size: .9rem;
    }

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
from models import MigrationSessionState

if "state_initialized" not in st.session_state:
    # Initialize with strict typing and defaults via Pydantic
    initial_state = MigrationSessionState().model_dump()
    for key, val in initial_state.items():
        if key not in st.session_state:
            st.session_state[key] = val
    st.session_state["state_initialized"] = True


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☁️ CMDSS")
    st.markdown("**Cloud Migration Decision Support System**")
    st.divider()

    st.markdown("### 🏢 Organisation")
    org_name_input = st.text_input("Organisation Name", value="My Organisation",
                                    placeholder="Enter your org name")
    st.session_state["org_name"] = org_name_input

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
        st.success(f"✅ Cloud analysis done\n\nBest: **{bp}** @ **{inr(cost)}/yr**")

    st.divider()
    st.markdown("### 📥 Export Report")

    def _build_report_data_sidebar():
        return {
            "org_name":      st.session_state.get("org_name", "My Organisation"),
            "pricing_model": st.session_state["pricing_model"] or "on_demand",
            "tco":           st.session_state["tco_result"],
            "cloud":         st.session_state["cloud_analysis"],
            "risk":          st.session_state["report_risk"],
            "strategy":      st.session_state["report_strategy"],
            "ml":            st.session_state["report_ml"],
        }

    rd = _build_report_data_sidebar()
    phases_done = sum([
        rd["tco"] is not None,
        rd["cloud"] is not None,
        rd["risk"] is not None,
        rd["strategy"] is not None,
        rd["ml"] is not None,
    ])
    st.caption(f"{phases_done}/5 phases complete")

    if phases_done > 0:
        html_bytes = generate_html_report(rd).encode("utf-8")
        st.download_button(
            label="📄 Download HTML Report",
            data=html_bytes,
            file_name=f"cmdss_report_{rd['org_name'].replace(' ','_')}.html",
            mime="text/html",
            width="stretch"
        )
        csv_bytes = generate_csv_export(rd).encode("utf-8")
        st.download_button(
            label="📊 Download CSV Data",
            data=csv_bytes,
            file_name=f"cmdss_data_{rd['org_name'].replace(' ','_')}.csv",
            mime="text/csv",
            width="stretch"
        )
    else:
        st.info("Complete at least one phase to enable export.")

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📦 Phase 1 — Infrastructure & TCO",
    "💰 Phase 2 — Cost Analysis",
    "⚠️ Phase 3 — Risk Analysis",
    "🧭 Phase 4 — Strategy & Rules",
    "🤖 Phase 5 — ML Prediction",
    "📥 Export Report"
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

            # ── Format guidance panel ──
            st.markdown("""
            <div style="background:#0c1929;border:1px solid #1d4ed8;border-radius:10px;
                        padding:16px 20px;margin-bottom:14px;">
              <div style="color:#60a5fa;font-weight:700;font-size:.9rem;
                          margin-bottom:10px;letter-spacing:.04em;">
                📋 REQUIRED FILE FORMAT
              </div>
              <div style="color:#cbd5e1;font-size:.85rem;margin-bottom:10px;">
                Your <code style="background:#1e293b;padding:1px 6px;border-radius:3px;">.xlsx</code>
                file must contain these <strong style="color:#f8fafc;">two columns</strong>
                with exact names (case-sensitive):
              </div>
              <table style="width:100%;border-collapse:collapse;font-size:.82rem;">
                <thead>
                  <tr>
                    <th style="background:#1e3a5f;color:#93c5fd;padding:7px 12px;
                               text-align:left;border-radius:4px 0 0 0;">Column Name</th>
                    <th style="background:#1e3a5f;color:#93c5fd;padding:7px 12px;
                               text-align:left;">Type</th>
                    <th style="background:#1e3a5f;color:#93c5fd;padding:7px 12px;
                               text-align:left;border-radius:0 4px 0 0;">Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:8px 12px;">
                      <code style="color:#34d399;background:#052e16;
                                   padding:2px 8px;border-radius:3px;font-size:.8rem;">Quantity</code>
                    </td>
                    <td style="padding:8px 12px;color:#94a3b8;font-size:.82rem;">Integer</td>
                    <td style="padding:8px 12px;color:#cbd5e1;font-size:.82rem;">
                      Number of servers of this type</td>
                  </tr>
                  <tr>
                    <td style="padding:8px 12px;">
                      <code style="color:#34d399;background:#052e16;
                                   padding:2px 8px;border-radius:3px;font-size:.8rem;">Storage (TB) per Server</code>
                    </td>
                    <td style="padding:8px 12px;color:#94a3b8;font-size:.82rem;">Decimal</td>
                    <td style="padding:8px 12px;color:#cbd5e1;font-size:.82rem;">
                      Storage per individual server in TB</td>
                  </tr>
                </tbody>
              </table>
              <div style="margin-top:12px;padding:10px 12px;background:#0f172a;
                          border-radius:6px;font-size:.8rem;line-height:1.8;color:#94a3b8;">
                <div style="margin-bottom:4px;">
                  <span style="color:#e2e8f0;font-weight:600;">How values are used:</span><br>
                  Total Servers &nbsp;= &nbsp;SUM of all Quantity values<br>
                  Total Storage &nbsp;= &nbsp;SUM of (Quantity × Storage per Server)
                </div>
                <div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e293b;">
                  <span style="color:#e2e8f0;font-weight:600;">Example row:</span>
                  &nbsp; Web Servers | <strong style="color:#f8fafc;">10</strong> |
                  <strong style="color:#f8fafc;">2.0</strong>
                  &nbsp;→&nbsp; 10 servers, 2 TB each = 20 TB total<br>
                  <span style="color:#e2e8f0;font-weight:600;">Extra columns</span>
                  &nbsp;(e.g. Server Type, Notes) are <em>allowed and ignored</em>.
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Sample file download ──
            try:
                sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_infrastructure.xlsx")
                with open(sample_path, "rb") as _f:
                    _sample_bytes = _f.read()
                st.download_button(
                    label="⬇️ Download Sample Excel Template",
                    data=_sample_bytes,
                    file_name="sample_infrastructure.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    help="A ready-to-edit sample with the correct column format and example data"
                )
            except FileNotFoundError:
                pass

            # ── File uploader ──
            uploaded_file = st.file_uploader(
                "Upload your Infrastructure Excel file",
                type=["xlsx"],
                help="Must contain 'Quantity' and 'Storage (TB) per Server' columns"
            )
            if uploaded_file:
                try:
                    result = calculate_onprem_tco(file_path=uploaded_file)
                    st.session_state["tco_result"] = result
                    st.session_state["servers"]    = result["servers"]
                    st.session_state["storage_tb"] = result["storage_tb"]
                    st.success(
                        f"✅ Loaded: **{result['servers']} servers** · "
                        f"**{result['storage_tb']} TB** total storage"
                    )
                except ValueError as e:
                    st.error(f"❌ Format error: {e}")
                    st.markdown("""
                    <div class="warn-box">
                      Ensure your file has exactly these column names (case-sensitive):<br><br>
                      <code style="background:#1a1000;padding:2px 7px;border-radius:3px;">Quantity</code>
                      &nbsp; and &nbsp;
                      <code style="background:#1a1000;padding:2px 7px;border-radius:3px;">Storage (TB) per Server</code>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Could not read file: {e}")

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
            if st.button("▶ Load Preset", width="stretch"):
                result = calculate_onprem_tco(preset=preset)
                st.session_state["tco_result"] = result
                st.session_state["servers"]    = result["servers"]
                st.session_state["storage_tb"] = result["storage_tb"]
                st.success(f"✅ Preset loaded: **{result['servers']} servers**, **{result['storage_tb']} TB**")

        elif input_method == "Manual Inputs":
            servers_input = st.number_input("Number of Servers",  min_value=1, value=20)
            storage_input = st.number_input("Storage (TB)",        min_value=1.0, value=10.0, step=1.0)
            if st.button("▶ Calculate TCO", width="stretch"):
                result = calculate_manual_tco(servers=servers_input, storage_tb=storage_input)
                st.session_state["tco_result"] = result
                st.session_state["servers"]    = result["servers"]
                st.session_state["storage_tb"] = result["storage_tb"]
                st.success(f"✅ Calculated: **{result['servers']} servers**, **{result['storage_tb']} TB**")

        # ── Utilisation inputs ──
        st.markdown("---")
        st.markdown("#### Server Utilisation")
        vcpu_input = st.number_input("vCPU per Server",      min_value=1, value=8)
        ram_input  = st.number_input("RAM per Server (GB)",  min_value=1, value=32)
        cpu_util   = st.slider("CPU Utilisation (%)",        10, 100, 60, step=5)
        ram_util   = st.slider("RAM Utilisation (%)",        10, 100, 70, step=5)

        st.session_state["cpu_util"] = cpu_util
        st.session_state["ram_util"] = ram_util

        if st.session_state["servers"] and st.button("☁️ Run Cloud Analysis",
                                                       width="stretch", type="primary"):
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
            except ValueError as ve:
                st.error("⚠️ **Input Validation Error:** The provided input triggered a validation rule.")
                st.info(f"Details: {ve}")
            except Exception as e:
                st.error("⚠️ **Unexpected Error:** We encountered an issue while running the cloud analysis.")
                st.info("Please verify your input values and try again.")

    with col_right:
        result = st.session_state["tco_result"]

        if result:
            st.markdown("#### On-Premise TCO Results")

            m1, m2, m3 = st.columns(3)
            m1.metric("Annual OpEx", inr(result['annual_operational_cost']))
            m2.metric("3-Year TCO",  inr(result['tco_3yr']))
            m3.metric("5-Year TCO",  inr(result['tco_5yr']))

            st.markdown("---")

            cost_items = {
                "Hardware CapEx":  result["hardware_cost"],
                "Storage CapEx":   result["storage_capex"],
                "Maintenance":     result["annual_maintenance"],
                "Power & Cooling": result["annual_power"],
                "IT Staff":        result["annual_staff"],
                "Storage OpEx":    result["annual_storage_opex"],
            }
            df_costs = pd.DataFrame({
                "Category": list(cost_items.keys()),
                "Amount":   list(cost_items.values())
            })

            fig_donut = px.pie(
                df_costs, values="Amount", names="Category",
                title="Cost Breakdown", hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0", title_font_size=14,
                legend=dict(font=dict(size=11)),
                margin=dict(t=50, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_donut, width="stretch")

            years    = [1, 2, 3, 4, 5]
            capex    = result["total_capex"]
            opex     = result["annual_operational_cost"]
            tco_vals = [capex + opex * y for y in years]

            fig_line = px.line(
                x=years, y=tco_vals, title="TCO Projection (5 Years)",
                markers=True, labels={"x": "Year", "y": "Cumulative Cost (₹)"}
            )
            fig_line.update_traces(line_color="#2563eb", line_width=3, marker_size=8)
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0", title_font_size=14,
                margin=dict(t=50, b=30, l=10, r=10),
                xaxis=dict(gridcolor="#334155"), yaxis=dict(gridcolor="#334155")
            )
            st.plotly_chart(fig_line, width="stretch")

            analysis = st.session_state["cloud_analysis"]
            if analysis:
                st.markdown("#### Right-Sizing Result")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("vCPU (Before)", analysis["original_vcpu"])
                r2.metric("vCPU (After)",  analysis["recommended_vcpu"],
                          delta=f"-{analysis['cpu_reduction_pct']}%")
                r3.metric("RAM (Before)",  f"{analysis['original_ram']} GB")
                r4.metric("RAM (After)",   f"{analysis['recommended_ram']} GB",
                          delta=f"-{analysis['ram_reduction_pct']}%")

                st.markdown(f"""
                <div class="info-box">
                  🔬 <b>Workload Type:</b> {analysis['workload_type'].capitalize()} —
                  Right-sized from <b>{analysis['original_vcpu']} vCPU / {analysis['original_ram']} GB</b>
                  to <b>{analysis['recommended_vcpu']} vCPU / {analysis['recommended_ram']} GB</b>
                  using actual utilisation + 30% safety buffer.
                </div>
                """, unsafe_allow_html=True)

                # ── Zombie Server / Inventory Integrity Check ────────────
                st.markdown("---")
                st.markdown("#### 🧟 Inventory Integrity Check")
                st.caption("AI scans your infrastructure for over-provisioned 'zombie' servers before cloud pricing begins.")

                # Build server list from session data
                zombie_server_list = [{
                    "name":         f"server-pool",
                    "ram_gb":       float(st.session_state.get("ram_input", 32)),
                    "vcpu":         int(st.session_state.get("vcpu_input", 8)),
                    "cpu_util_pct": float(cpu_util),
                    "ram_util_pct": float(ram_util),
                }]
                zombie_result = detect_zombie_servers(zombie_server_list)
                integrity = zombie_result["inventory_integrity"]

                if integrity == "CLEAN":
                    st.markdown("""
                    <div style="background:#052e16;border:1px solid #22c55e;
                                border-left:4px solid #22c55e;border-radius:8px;
                                padding:12px 18px;color:#86efac;font-size:.88rem;">
                      ✅ <b>Inventory Integrity: CLEAN</b> — No zombie servers detected.
                      Resource allocation is healthy for cloud migration.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    sev_color = "#ef4444" if integrity == "CRITICAL" else "#f59e0b"
                    sev_icon  = "🚨" if integrity == "CRITICAL" else "⚠️"
                    st.markdown(f"""
                    <div style="background:#1a0a0a;border:1px solid {sev_color};
                                border-left:4px solid {sev_color};border-radius:8px;
                                padding:14px 18px;margin-bottom:12px;">
                      <div style="color:{sev_color};font-weight:700;margin-bottom:6px;">
                        {sev_icon} INVENTORY INTEGRITY: {integrity}
                      </div>
                      <div style="color:#fca5a5;font-size:.9rem;">
                        {zombie_result['waste_summary']}
                      </div>
                      <div style="color:#fde68a;font-size:.82rem;margin-top:8px;">
                        💡 Right-size or decommission flagged servers BEFORE
                        proceeding to cloud pricing — migrating waste locks in
                        inflated cloud bills.
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    for z in zombie_result["zombies"]:
                        sev_c = {"Critical": "#ef4444", "High": "#f59e0b",
                                 "Medium": "#60a5fa", "Low": "#22c55e"}.get(z["severity"], "#60a5fa")
                        st.markdown(f"""
                        <div style="background:#1e293b;border-left:4px solid {sev_c};
                                    border-radius:0 8px 8px 0;padding:10px 14px;margin:4px 0;">
                          <span style="color:#f1f5f9;font-weight:600;">🧟 {z['name']}</span>
                          <span style="color:{sev_c};font-size:.8rem;font-weight:700;float:right;">{z['severity'].upper()}</span>
                          <div style="color:#94a3b8;font-size:.83rem;margin-top:3px;">
                            {z['ram_gb']} GB RAM · {z['vcpu']} vCPU · CPU @ {z['cpu_util_pct']}%
                          </div>
                          <div style="color:#fde68a;font-size:.8rem;margin-top:4px;">
                            💡 {z['recommendation']}
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                st.session_state["report_audit"] = zombie_result

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

        best_provider = analysis["best_provider"]
        cloud_yearly  = analysis["costs"][best_provider]["selected"]
        onprem_annual = result["annual_operational_cost"]
        onprem_5yr    = result["tco_5yr"]
        cloud_5yr     = cloud_yearly * 5
        savings_5yr   = onprem_5yr - cloud_5yr
        savings_pct   = (savings_5yr / onprem_5yr) * 100 if onprem_5yr else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("On-Prem Annual",      inr(onprem_annual))
        c2.metric("Cloud Annual (Best)", inr(cloud_yearly),
                  delta=f"-{inr(onprem_annual - cloud_yearly)}")
        c3.metric("5-Year Savings",      inr(savings_5yr),
                  delta=f"{savings_pct:.1f}%")
        c4.metric("Best Provider",       best_provider)

        st.markdown("---")

        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown("#### 5-Year TCO Comparison")
            fig_bar = go.Figure(data=[
                go.Bar(name="On-Premise", x=["On-Premise"], y=[onprem_5yr],
                       marker_color="#ef4444", text=[inr(onprem_5yr)],
                       textposition="auto"),
                go.Bar(name=f"Cloud ({best_provider})", x=[f"Cloud ({best_provider})"],
                       y=[cloud_5yr], marker_color="#22c55e",
                       text=[inr(cloud_5yr)], textposition="auto")
            ])
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0", showlegend=False,
                margin=dict(t=20, b=20), yaxis=dict(gridcolor="#334155")
            )
            st.plotly_chart(fig_bar, width="stretch")

        with col_b:
            st.markdown("#### Year-by-Year Cost Trajectory")
            years         = list(range(1, 6))
            onprem_cumul  = [result["total_capex"] + onprem_annual * y for y in years]
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
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0", margin=dict(t=20, b=20),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(title="Year", gridcolor="#334155"),
                yaxis=dict(title="Cumulative Cost (₹)", gridcolor="#334155")
            )
            st.plotly_chart(fig_traj, width="stretch")

        st.markdown("#### 🌐 Supported Cloud Providers")
        col_logo1, col_logo2, col_logo3 = st.columns(3)
        col_logo1.markdown("### 🟠 AWS")
        col_logo2.markdown("### 🔵 Azure")
        col_logo3.markdown("### 🟢 GCP")

        st.markdown("#### Multi-Provider Annual Cost Comparison")
        st.markdown(f"*Pricing model: **{pricing_model.replace('_', ' ').title()}***")

        provider_rows = []
        for provider, cost_data in analysis["costs"].items():
            sel_cost = cost_data["selected"]
            saving   = onprem_annual - sel_cost
            saving_p = (saving / onprem_annual) * 100 if onprem_annual else 0
            provider_rows.append({
                "Provider":   provider,
                "Annual Cost": sel_cost,
                "vs On-Prem": saving,
                "Savings %":  saving_p,
                "Instance":   analysis["instances"][provider]["instance"],
                "vCPU":       analysis["instances"][provider]["vcpu"],
                "RAM (GB)":   analysis["instances"][provider]["ram_gb"],
                "Best":       provider == best_provider
            })

        for _, row in pd.DataFrame(provider_rows).iterrows():
            css_class = "provider-row best" if row["Best"] else "provider-row"
            badge     = "⭐ BEST" if row["Best"] else ""
            color     = "#22c55e" if row["vs On-Prem"] > 0 else "#ef4444"
            arrow     = "▼" if row["vs On-Prem"] > 0 else "▲"
            st.markdown(f"""
            <div class="{css_class}">
              <div><b>{row['Provider']}</b> {badge}</div>
              <div style="color:#94a3b8;font-size:.85rem;">{row['Instance']} · {row['vCPU']} vCPU · {row['RAM (GB)']} GB</div>
              <div style="font-size:1.2rem;font-weight:700;">{inr(row['Annual Cost'])}</div>
              <div style="color:{color};font-weight:600;">{arrow} {inr(abs(row['vs On-Prem']))} ({abs(row['Savings %']):.1f}%)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"#### Pricing Model Breakdown — {best_provider}")
        costs_bp = analysis["costs"][best_provider]
        models   = ["on_demand", "reserved_1yr", "reserved_3yr"]
        labels   = ["On-Demand", "Reserved 1-Year", "Reserved 3-Year"]
        vals     = [costs_bp[m] for m in models]

        fig_pm = go.Figure(go.Bar(
            x=labels, y=vals,
            marker_color=["#94a3b8", "#60a5fa", "#2563eb"],
            text=[inr(v) for v in vals], textposition="auto"
        ))
        fig_pm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
            font_color="#e2e8f0", margin=dict(t=10, b=10),
            yaxis=dict(gridcolor="#334155")
        )
        st.plotly_chart(fig_pm, width="stretch")

        st.markdown("#### Financial Migration Decision")
        try:
            financial_decision = financial_recommend(
                onprem_cost=onprem_annual,
                cloud_costs=analysis["costs"],
                pricing_model=pricing_model,
                servers=result.get("servers", 1)
            )
            summary = financial_decision.get("_summary", {})

            if summary.get("overall_recommendation") == "Migrate to Cloud":
                st.success("✅ **Recommendation: Migrate to Cloud**")
                cols = st.columns(3)
                cols[0].metric("Best Provider",  summary.get("best_cloud_option", "N/A"))
                cols[1].metric("Annual Savings", inr(summary.get("best_savings", 0)))
                cols[2].metric("Confidence",     summary.get("confidence", "N/A"))
                st.info(f"💡 {summary.get('reason', '')}")
            else:
                st.warning("⚠️ **Recommendation: Stay On-Prem** — No cloud provider offers sufficient savings.")

            with st.expander("📊 Full Per-Provider Decision Breakdown"):
                for prov, data in financial_decision.items():
                    if prov.startswith("_"):
                        continue
                    st.markdown(
                        f"**{prov}** — {data['recommendation']} | "
                        f"Savings: {inr(data['savings'])} ({data['savings_pct']:.1f}%) | "
                        f"Confidence: {data['confidence']}"
                    )
        except Exception as e:
            st.warning(f"⚠️ **Decision Engine Error:** {e}")


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
            downtime_risk  = st.slider("Downtime Probability", 0.0, 1.0, 0.10, 0.01,
                                       help="Probability that significant downtime occurs during migration")
            downtime_cost  = st.number_input("Downtime Cost (₹)", value=50000, step=5000)

            st.markdown("**🟡 Compliance Risk**")
            compliance_risk    = st.slider("Compliance Probability", 0.0, 1.0, 0.05, 0.01)
            compliance_penalty = st.number_input("Compliance Penalty (₹)", value=100000, step=10000)

            st.markdown("**🟢 Skill Gap Risk**")
            skill_risk    = st.slider("Skill Gap Probability", 0.0, 1.0, 0.20, 0.01)
            training_cost = st.number_input("Training Cost (₹)", value=20000, step=2000)

            # ── NLP Fear Classifier ──────────────────────────────────
            st.markdown("---")
            st.markdown("#### 📝 Describe Your Migration Concerns")
            st.caption(
                "Type your biggest fears about this migration. "
                "The AI will classify them into risk categories and adjust "
                "your probability sliders automatically."
            )
            fear_text = st.text_area(
                "Migration Concerns (free text)",
                placeholder=(
                    "e.g. I'm worried about data breaches and our team has no "
                    "Kubernetes experience. The budget is tight and we can't "
                    "afford delays..."
                ),
                height=120,
                key="nlp_fear_text",
                label_visibility="collapsed",
            )

            # Analyze NLP concerns
            nlp_result = None
            nlp_penalty = 0.0
            if fear_text and fear_text.strip():
                best_provider_t3 = analysis["best_provider"]
                cloud_yearly_t3  = analysis["costs"][best_provider_t3]["selected"]
                nlp_result = analyze_migration_concerns(fear_text, cloud_annual=cloud_yearly_t3)

                if nlp_result["detected_categories"]:
                    nlp_penalty = nlp_result["total_penalty"]
                    adj = nlp_result["probability_adjustments"]

                    # Show detected categories
                    for cat in nlp_result["detected_categories"]:
                        sev_colors = {"Low": "#22c55e", "Medium": "#f59e0b",
                                      "High": "#ef4444", "Critical": "#991b1b"}
                        sc = sev_colors.get(cat["severity"], "#60a5fa")
                        st.markdown(f"""
                        <div style="background:#1e293b;border-left:4px solid {sc};
                                    border-radius:0 8px 8px 0;padding:10px 14px;margin:4px 0;">
                          <span style="color:#f1f5f9;font-weight:600;">{cat['icon']} {cat['label']}</span>
                          <span style="color:{sc};font-size:.8rem;font-weight:700;float:right;">
                            {cat['severity']} · +{cat['prob_adjustment']:.0%}
                          </span>
                          <div style="color:#94a3b8;font-size:.82rem;margin-top:4px;">
                            Matched: {', '.join(cat['matched_keywords'])}
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Apply NLP adjustments to sliders
                    downtime_risk    = min(1.0, downtime_risk    + adj.get("downtime_risk", 0.0))
                    compliance_risk  = min(1.0, compliance_risk  + adj.get("compliance_risk", 0.0))
                    skill_risk       = min(1.0, skill_risk       + adj.get("skill_risk", 0.0))

                    st.markdown(f"""
                    <div class="info-box">
                      📊 <b>NLP Adjustments Applied:</b><br>
                      Downtime → {downtime_risk:.0%} ·
                      Compliance → {compliance_risk:.0%} ·
                      Skill Gap → {skill_risk:.0%}<br>
                      Financial Penalty: <b>{inr(nlp_penalty)}/yr</b> added to risk-adjusted cost.
                    </div>
                    """, unsafe_allow_html=True)

                    st.session_state["nlp_risk_result"] = nlp_result
                else:
                    st.info("✅ No specific risk categories detected in your description.")

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

                adj_cloud_cost = risk_adjusted_tco(cloud_yearly, risk) + nlp_penalty
                adj_savings    = onprem_annual - adj_cloud_cost
                adj_savings_p  = (adj_savings / onprem_annual * 100) if onprem_annual else 0

                st.session_state["report_risk"] = {
                    "risk":           risk,
                    "adj_cloud_cost": adj_cloud_cost,
                    "inputs": {
                        "downtime_risk":       downtime_risk,
                        "downtime_cost":       downtime_cost,
                        "compliance_risk":     compliance_risk,
                        "compliance_penalty":  compliance_penalty,
                        "skill_risk":          skill_risk,
                        "training_cost":       training_cost,
                    }
                }

                st.markdown("#### Risk-Adjusted Results")

                m1, m2 = st.columns(2)
                m1.metric("Total Risk Cost",          inr(risk['total_risk_cost']))
                m2.metric("Risk-Adjusted Cloud Cost", inr(adj_cloud_cost),
                          delta=f"+{inr(risk['total_risk_cost'])} risk")

                m3, m4 = st.columns(2)
                m3.metric("Base Cloud Cost",  inr(cloud_yearly))
                m4.metric("Adjusted Savings", inr(adj_savings),
                          delta=f"{adj_savings_p:.1f}% vs on-prem")

                fig_risk = go.Figure(go.Bar(
                    x=["Downtime Risk", "Compliance Risk", "Skill Gap Risk"],
                    y=[risk["downtime_cost"], risk["compliance_cost"], risk["skill_cost"]],
                    marker_color=["#ef4444", "#f59e0b", "#22c55e"],
                    text=[inr(v) for v in [
                        risk["downtime_cost"], risk["compliance_cost"], risk["skill_cost"]
                    ]],
                    textposition="auto"
                ))
                fig_risk.update_layout(
                    title="Expected Risk Cost Breakdown",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                    font_color="#e2e8f0", margin=dict(t=40, b=20),
                    yaxis=dict(gridcolor="#334155", title="Expected Cost (₹)")
                )
                st.plotly_chart(fig_risk, width="stretch")

                onprem_5yr    = result["tco_5yr"]
                cloud_5yr     = cloud_yearly * 5
                adj_cloud_5yr = adj_cloud_cost * 5

                fig_comp = go.Figure(data=[
                    go.Bar(name="On-Premise 5yr",       y=[onprem_5yr],    marker_color="#ef4444",
                           text=[inr(onprem_5yr)],    textposition="auto"),
                    go.Bar(name="Cloud 5yr (base)",      y=[cloud_5yr],     marker_color="#22c55e",
                           text=[inr(cloud_5yr)],     textposition="auto"),
                    go.Bar(name="Cloud 5yr (risk-adj.)", y=[adj_cloud_5yr], marker_color="#f59e0b",
                           text=[inr(adj_cloud_5yr)], textposition="auto"),
                ])
                fig_comp.update_layout(
                    title="5-Year: On-Prem vs Cloud vs Risk-Adjusted Cloud",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                    font_color="#e2e8f0", margin=dict(t=40, b=20),
                    barmode="group", yaxis=dict(gridcolor="#334155"),
                    legend=dict(bgcolor="rgba(0,0,0,0)")
                )
                st.plotly_chart(fig_comp, width="stretch")

                st.markdown("#### 🚀 Migration Readiness Score")
                risk_factor = risk["total_risk_cost"] / max(cloud_yearly, 1)
                score = int(max(0, min(100, 60 + adj_savings_p - (risk_factor * 20))))
                st.metric("Readiness Score", f"{score}/100")
                if score > 75:
                    st.success("Highly Ready for Cloud Migration")
                elif score > 50:
                    st.info("Moderately Ready — Some Risks Present")
                else:
                    st.warning("Low Readiness — Address Risks First")

                if adj_savings > 0:
                    st.markdown(f"""
                    <div class="info-box">
                      ✅ Even after accounting for all migration risks,
                      <b>{best_provider}</b> saves <b>{inr(adj_savings)}/year</b>
                      ({adj_savings_p:.1f}% cheaper than on-premise).
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="warn-box">
                      ⚠️ After risk adjustment, on-premise is more cost-effective by
                      <b>{inr(abs(adj_savings))}/year</b>.
                      Consider reducing migration risks or renegotiating cloud pricing.
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error("⚠️ **Risk Calculation Failed:** Could not compute the risk-adjusted costs. Please verify that all parameters are valid.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — Strategy & Rules (with Technical Debt Check + Migration Economics)
# ══════════════════════════════════════════════════════════════════════════════
with tab4:

    st.markdown('<div class="section-header">🧭 Rule-Based Strategy Recommendation — The Honest Advisor</div>',
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
        st.markdown("#### 🔍 Technical Debt Check")
        st.caption("Optional — fill in to detect migration blockers.")

        os_input  = st.text_input("Operating System (e.g. Windows 2008 R2, Ubuntu 22)",
                                   placeholder="e.g. Windows Server 2019",
                                   help="Legacy OS patterns trigger a force-override to Retain / Rehost")
        app_input = st.text_area("Application Pattern Notes",
                                  placeholder="e.g. stateful, shared filesystem, sticky session…",
                                  height=80,
                                  help="Stateful or shared-disk apps may block Cloud-Native migration")
        net_input = st.text_input("Network / IP Config Notes",
                                   placeholder="e.g. hardcoded IP, ip whitelist…",
                                   help="Hardcoded IP dependencies are a hard migration blocker")

        st.markdown("---")
        st.markdown("#### 👥 Team Capability")
        has_skilled_team = st.checkbox(
            "Highly Skilled Cloud Team",
            help="Reduces labour multiplier by 30%. Applies to migration cost calculation."
        )
        has_cicd = st.checkbox(
            "Automated CI/CD Pipelines",
            help="Reduces labour multiplier by 20%. Applies to migration cost calculation."
        )

        st.markdown("---")
        budget_level_sel = st.selectbox(
            "Budget Sensitivity",
            ["low", "medium", "high"],
            format_func=lambda x: {"low": "Low / Cost-Sensitive",
                                   "medium": "Moderate",
                                   "high": "Flexible / High Budget"}[x],
            index=1
        )

        st.markdown("""
        <div class="info-box">
          <b>Rule Logic:</b><br>
          • High compliance + Low downtime → <b>Hybrid</b><br>
          • High growth → <b>Cloud-Native</b><br>
          • Default → <b>Lift-and-Shift</b><br>
          • Legacy OS / Hardcoded IPs → <b>Force Retain</b><br>
          • Stateful apps → <b>Force Rehost</b>
        </div>
        """, unsafe_allow_html=True)

    with col_out:
        try:
            _compliance = str(compliance_sel).strip().lower()
            _downtime   = str(downtime_sel).strip().lower()
            _growth     = str(growth_sel).strip().lower()

            # Build server_info only if any field was filled
            server_info = None
            if os_input.strip() or app_input.strip() or net_input.strip():
                server_info = {
                    "os":             os_input,
                    "app_pattern":    app_input,
                    "network_config": net_input,
                }

            strategy_result = recommend_strategy(_compliance, _downtime, _growth,
                                                  server_info=server_info)
            strategy  = strategy_result["strategy"]
            overridden = strategy_result["overridden"]
            debt_check = strategy_result["debt_check"]

            dr_plan = recommend_dr(_downtime)
            roadmap = get_migration_roadmap(strategy)

            # ── Technical Debt Banner ──────────────────────────────────
            if debt_check and debt_check["has_debt"]:
                severity_color = "#ef4444" if debt_check["severity"] == "hard" else "#f59e0b"
                severity_icon  = "⛔" if debt_check["severity"] == "hard" else "⚠️"
                st.markdown(f"""
                <div style="background:#1a0a0a;border:1px solid {severity_color};
                            border-left:4px solid {severity_color};border-radius:8px;
                            padding:14px 18px;margin-bottom:16px;">
                  <div style="color:{severity_color};font-weight:700;margin-bottom:6px;">
                    {severity_icon} TECHNICAL DEBT OVERRIDE
                  </div>
                  <div style="color:#fca5a5;font-size:.9rem;">
                    Business rules suggested: <b>{strategy_result['original_strategy']}</b><br>
                    Overridden to: <b style="color:#f9fafb;">{strategy}</b>
                  </div>
                  <div style="color:#fde68a;font-size:.82rem;margin-top:8px;">
                    {debt_check['friction_report']}
                  </div>
                </div>
                """, unsafe_allow_html=True)
            elif debt_check:
                st.markdown("""
                <div style="background:#052e16;border:1px solid #22c55e;
                            border-left:4px solid #22c55e;border-radius:8px;
                            padding:12px 18px;margin-bottom:16px;color:#86efac;font-size:.88rem;">
                  ✅ No technical debt blockers detected.
                </div>
                """, unsafe_allow_html=True)

            badge_color = {
                "Lift-and-Shift":         "badge-blue",
                "Hybrid Migration":       "badge-orange",
                "Cloud-Native Migration": "badge-green",
                "Retain On-Premise":      "badge-purple",
            }.get(strategy, "badge-blue")

            st.markdown(f"""
            <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:16px;">
              <div style="color:#94a3b8;font-size:.85rem;margin-bottom:8px;">
                RECOMMENDED STRATEGY {'(OVERRIDDEN)' if overridden else ''}
              </div>
              <span class="{badge_color}" style="font-size:1rem;padding:8px 24px;">{strategy}</span>
            </div>
            """, unsafe_allow_html=True)

            dr_color = {"Hot DR": "#ef4444", "Warm DR": "#f59e0b", "Cold DR": "#22c55e"}.get(dr_plan, "#60a5fa")
            st.markdown(f"""
            <div style="background:#1e293b;border-radius:12px;padding:20px;margin-bottom:16px;">
              <div style="color:#94a3b8;font-size:.85rem;margin-bottom:8px;">DISASTER RECOVERY PLAN</div>
              <span style="color:{dr_color};font-size:1.2rem;font-weight:700;">🛡️ {dr_plan}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### Migration Roadmap")
            for step in roadmap:
                st.markdown(f'<div class="roadmap-step">🔷 {step}</div>', unsafe_allow_html=True)

            # ── Migration Economics Section ────────────────────────────
            if st.session_state.get("tco_result") and st.session_state.get("cloud_analysis"):
                st.markdown("---")
                st.markdown("#### 💸 Migration Economics — Year 1 Reality Check")

                result   = st.session_state["tco_result"]
                analysis = st.session_state["cloud_analysis"]
                bp       = analysis["best_provider"]
                onprem_annual = result["annual_operational_cost"]
                cloud_annual  = analysis["costs"][bp]["selected"]

                # Call financial decision engine with strategy + team info
                fin_dec = financial_recommend(
                    onprem_cost      = onprem_annual,
                    cloud_costs      = analysis["costs"],
                    pricing_model    = pricing_model,
                    strategy_name    = strategy,
                    servers          = result["servers"],
                    has_skilled_team = has_skilled_team,
                    has_cicd         = has_cicd,
                )
                econ = fin_dec.get("_migration_economics")

                if econ:
                    e1, e2, e3 = st.columns(3)
                    e1.metric("Labour Multiplier",  f"{econ['labor_multiplier']}×")
                    e2.metric("Double-Run Period",   f"{econ['double_run_months']} months")
                    e3.metric("Year 1 Total Cost",   inr(econ['year1_total']))

                    e4, e5, e6 = st.columns(3)
                    e4.metric("Labour Cost",         inr(econ['labor_cost']))
                    e5.metric("Double-Run Penalty",  inr(econ['double_run_cost']))

                    if econ["break_even_month"]:
                        e6.metric("Break-Even Month", f"Month {econ['break_even_month']}")
                    else:
                        e6.metric("Break-Even", "Never — review strategy")

                    # Fragility warnings
                    st.markdown("##### 📊 Fragility Analysis")
                    frag_price = econ.get("fragility_10pct_price", "")
                    frag_delay = econ.get("fragility_2mo_delay", "")
                    is_fragile_price = "HIGH FRAGILITY" in frag_price or "CRITICAL" in frag_price
                    is_fragile_delay = "HIGH FRAGILITY" in frag_delay or "CRITICAL" in frag_delay

                    box_class = "warn-box" if (is_fragile_price or is_fragile_delay) else "info-box"
                    st.markdown(f"""
                    <div class="{box_class}">
                      <b>📈 10% Cloud Price Increase:</b> {frag_price}<br><br>
                      <b>⏱️ 2-Month Migration Delay:</b> {frag_delay}
                    </div>
                    """, unsafe_allow_html=True)

                    if has_skilled_team or has_cicd:
                        discounts = []
                        if has_skilled_team: discounts.append("Skilled Team (−30%)")
                        if has_cicd:         discounts.append("CI/CD Automation (−20%)")
                        st.success(f"✅ Team discounts applied: {', '.join(discounts)}")

                    st.session_state["report_migration_econ"] = econ
                else:
                    st.info("Migration economics unavailable — run cloud analysis in Tab 1 first.")

            # Save strategy to report state
            st.session_state["report_strategy"] = {
                "strategy":   strategy,
                "overridden": overridden,
                "debt_check": debt_check,
                "dr_plan":    dr_plan,
                "roadmap":    roadmap,
                "inputs": {
                    "compliance": _compliance,
                    "downtime":   _downtime,
                    "growth":     _growth,
                }
            }

        except Exception as e:
            st.error("⚠️ **Strategy Engine Error:** The rule-based engine failed to process the inputs.")
            st.info(f"Details: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — AI System Auditor (Friction & Failure Predictor)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:

    st.markdown('<div class="section-header">🤖 AI System Auditor — Friction & Failure Predictor</div>',
                unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
      The AI evaluates the <b>risk of your chosen strategy</b> — not what strategy to pick
      (the Rule Engine already does that). It identifies <i>friction points</i>, <i>deadlocks</i>,
      and estimates the <b>probability of project failure</b>, giving you an honest executive
      verdict before you commit.
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("tco_result") and st.session_state.get("cloud_analysis"):
        result_fr    = st.session_state["tco_result"]
        analysis_fr  = st.session_state["cloud_analysis"]
        strategy_fr  = (st.session_state.get("report_strategy") or {}).get("strategy", "Lift-and-Shift")
        bp_fr        = analysis_fr["best_provider"]
        onprem_fr    = result_fr["annual_operational_cost"]
        cloud_fr     = analysis_fr["costs"][bp_fr]["selected"]
        econ_fr      = st.session_state.get("report_migration_econ")
        mig_premium  = econ_fr["migration_premium"] if econ_fr else None
        zombie_data  = st.session_state.get("report_audit")
        zombie_count = zombie_data.get("zombie_count", 0) if zombie_data else 0
        nlp_data     = st.session_state.get("nlp_risk_result")
        nlp_score    = nlp_data.get("risk_score", 0) if nlp_data else 0

        # Strategy context banner
        st.markdown(f"""
        <div style="background:#1e293b;border-radius:10px;padding:16px 20px;margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="color:#94a3b8;font-size:.8rem;">Evaluating Strategy</span><br>
              <span style="color:#e2e8f0;font-size:1.1rem;font-weight:700;">{strategy_fr}</span>
            </div>
            <div style="text-align:right;">
              <span style="color:#94a3b8;font-size:.8rem;">Best Provider</span><br>
              <span style="color:#60a5fa;font-size:1.1rem;font-weight:700;">{bp_fr}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        budget_fr_sel = st.selectbox(
            "Budget Level for Analysis",
            ["low", "medium", "high"],
            format_func=lambda x: {"low": "Low / Cost-Sensitive",
                                   "medium": "Moderate",
                                   "high": "Flexible / High Budget"}[x],
            index=1,
            key="audit_budget"
        )

        # ── Failure Probability ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🎯 Failure Probability Assessment")

        annual_saving = onprem_fr - cloud_fr

        failure = calculate_failure_probability(
            strategy          = strategy_fr,
            budget_level      = budget_fr_sel,
            servers           = result_fr["servers"],
            migration_premium = mig_premium,
            annual_saving     = annual_saving,
            has_skilled_team  = False,
            has_cicd          = False,
            zombie_count      = zombie_count,
            nlp_risk_score    = nlp_score,
        )

        prob_pct = failure["final_probability"] * 100
        tier     = failure["risk_tier"]
        tier_colors = {"Low": "#22c55e", "Medium": "#f59e0b",
                       "High": "#ef4444", "Critical": "#991b1b"}
        tc = tier_colors.get(tier, "#60a5fa")

        m1, m2, m3 = st.columns(3)
        m1.metric("Failure Probability", f"{prob_pct:.0f}%")
        m2.metric("Risk Tier", tier)
        m3.metric("Risk Factors", f"{len(failure['adjustments'])}")

        # Executive verdict
        st.markdown(f"""
        <div style="background:#0f172a;border:2px solid {tc};
                    border-radius:12px;padding:20px 24px;margin:12px 0;">
          <div style="color:{tc};font-size:.9rem;font-weight:700;margin-bottom:8px;">
            EXECUTIVE VERDICT
          </div>
          <div style="color:#e2e8f0;font-size:.92rem;line-height:1.6;">
            {failure['verdict']}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Risk factor decomposition
        if failure["adjustments"]:
            st.markdown("##### 📊 Risk Factor Decomposition")
            for adj in failure["adjustments"]:
                is_positive = adj["adjustment"].startswith("-")
                adj_color = "#22c55e" if is_positive else "#ef4444"
                adj_icon  = "↘" if is_positive else "↗"
                st.markdown(f"""
                <div style="background:#1e293b;border-left:4px solid {adj_color};
                            border-radius:0 8px 8px 0;padding:12px 16px;margin:6px 0;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#f1f5f9;font-weight:600;">{adj['factor']}</span>
                    <span style="color:{adj_color};font-size:.9rem;font-weight:700;">
                      {adj_icon} {adj['adjustment']}
                    </span>
                  </div>
                  <div style="color:#94a3b8;font-size:.83rem;margin-top:4px;">
                    {adj['reason']}
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ── Interactive Plotly Gauge ──────────────────────────────────────
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = prob_pct,
            title = {'text': "Failure Probability (%)", 'font': {'size': 18}},
            number = {'suffix': "%", 'font': {'size': 36}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                'bar': {'color': tc},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 0,
                'steps': [
                    {'range': [0, 15],  'color': "rgba(34, 197, 94, 0.15)"},
                    {'range': [15, 35], 'color': "rgba(245, 158, 11, 0.15)"},
                    {'range': [35, 60], 'color': "rgba(239, 68, 68, 0.15)"},
                    {'range': [60, 100],'color': "rgba(153, 27, 27, 0.25)"}],
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
            font_color="#e2e8f0", height=280, margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        if failure["adjustments"]:
            factors = []
            vals = []
            measure = []
            texts = []
            current_prob = failure["base_rate"] * 100
            
            factors.append("Base Rate")
            vals.append(current_prob)
            measure.append("absolute")
            texts.append(f"{current_prob:.0f}%")
            
            for adj in failure["adjustments"]:
                val_pct = float(adj['adjustment'].strip('%').replace('+',''))
                factors.append(adj['factor'])
                vals.append(val_pct)
                measure.append("relative")
                texts.append(f"{'+' if val_pct > 0 else ''}{val_pct:.0f}%")
                
            factors.append("Final Prob")
            vals.append(prob_pct)
            measure.append("total")
            texts.append(f"{prob_pct:.0f}%")

            fig_wf = go.Figure(go.Waterfall(
                orientation = "v",
                measure = measure,
                x = factors,
                textposition = "outside",
                text = texts,
                y = vals,
                connector = {"line":{"color":"#334155"}},
                decreasing = {"marker":{"color":"#22c55e"}},
                increasing = {"marker":{"color":"#ef4444"}},
                totals = {"marker":{"color":"#3b82f6"}}
            ))
            fig_wf.update_layout(
                title = "Volatility Breakdown (Failure Probability Factors)",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)",
                font_color="#e2e8f0", height=350, margin=dict(t=40, b=20),
                yaxis=dict(gridcolor="#334155")
            )
            st.plotly_chart(fig_wf, use_container_width=True)

        # ── Friction Report ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### ⚡ Friction Report — Strategy × Budget Reality Check")

        zombie_for_friction = st.session_state.get("report_audit")

        friction = generate_friction_report(
            strategy          = strategy_fr,
            budget_level      = budget_fr_sel,
            cloud_annual      = cloud_fr,
            onprem_annual     = onprem_fr,
            servers           = result_fr["servers"],
            migration_premium = mig_premium,
            zombie_report     = zombie_for_friction,
        )

        risk_colors_fr = {"Low": "#22c55e", "Medium": "#f59e0b",
                          "High": "#ef4444", "Critical": "#991b1b"}
        risk_color_fr = risk_colors_fr.get(friction["risk_level"], "#60a5fa")

        st.markdown(f"""
        <div style="background:#1e293b;border-left:4px solid {risk_color_fr};
                    border-radius:0 12px 12px 0;padding:20px 24px;margin-bottom:16px;">
          <div style="color:{risk_color_fr};font-size:1rem;font-weight:700;margin-bottom:8px;">
            Friction Level: {friction['risk_level']}
          </div>
          <div style="color:#e2e8f0;font-size:.9rem;white-space:pre-line;">{friction['narrative']}</div>
        </div>
        """, unsafe_allow_html=True)

        if friction["recommendations"]:
            st.markdown("**Mitigations:**")
            for rec in friction["recommendations"]:
                st.markdown(f"→ {rec}")

        # Save for report
        st.session_state["report_ml"] = {
            "friction_risk":       friction["risk_level"],
            "friction_narrative":  friction["narrative"],
            "warnings":            friction["warnings"],
            "failure_probability": failure["final_probability"],
            "failure_tier":        failure["risk_tier"],
            "failure_verdict":     failure["verdict"],
            "zombie_count":        zombie_count,
            "waste_pct":           (zombie_for_friction or {}).get("potential_savings_pct", 0),
        }
    else:
        st.info("Complete Phase 1 (Tab 1) and run Cloud Analysis first to enable the AI System Auditor.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 6 — Export Report
# ══════════════════════════════════════════════════════════════════════════════
with tab6:

    st.markdown('<div class="section-header">📥 Export Full Analysis Report</div>',
                unsafe_allow_html=True)

    org_name = st.session_state.get("org_name", "My Organisation")

    report_data = {
        "org_name":          org_name,
        "pricing_model":     st.session_state["pricing_model"] or "on_demand",
        "tco":               st.session_state["tco_result"],
        "cloud":             st.session_state["cloud_analysis"],
        "risk":              st.session_state["report_risk"],
        "strategy":          st.session_state["report_strategy"],
        "ml":                st.session_state["report_ml"],
        "migration_econ":    st.session_state["report_migration_econ"],
        "audit":             st.session_state["report_audit"],
    }

    phases_done = sum(
        1 for k, v in report_data.items()
        if k not in ("org_name", "pricing_model") and v is not None
    )

    st.markdown(f"**{phases_done}/5 phases complete** — fill in the remaining tabs to enrich the report.")

    col_status, col_dl = st.columns([1, 1.2], gap="large")

    with col_status:
        st.markdown("#### 📋 Report Contents")
        phase_checks = [
            ("📦 Phase 1 — On-Premise TCO",       report_data["tco"]),
            ("💰 Phase 2 — Cost Analysis",         report_data["cloud"]),
            ("⚠️  Phase 3 — Risk Analysis",        report_data["risk"]),
            ("🧭 Phase 4 — Strategy + Economics",  report_data["strategy"]),
            ("🤖 Phase 5 — AI System Audit",       report_data["ml"]),
        ]
        for label, data in phase_checks:
            tick  = "✅" if data else "⬜"
            color = "#22c55e" if data else "#475569"
            st.markdown(
                f'<div style="padding:8px 12px;background:#1e293b;border-radius:6px;'
                f'margin:4px 0;border-left:3px solid {color};">'
                f'{tick} {label}</div>',
                unsafe_allow_html=True
            )

        if phases_done < 5:
            st.markdown("""
            <div class="warn-box" style="margin-top:14px;">
              ⚠️ Some phases are incomplete. You can still export —
              incomplete sections will show "Not available" in the report.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-box" style="margin-top:14px;">
              ✅ All phases complete. Your report covers the full analysis.
            </div>
            """, unsafe_allow_html=True)

    with col_dl:
        st.markdown("#### 📥 Download Options")

        if phases_done > 0:
            html_report = generate_html_report(report_data)
            st.download_button(
                label="📄 Download HTML Report",
                data=html_report.encode("utf-8"),
                file_name=f"cmdss_report_{org_name.replace(' ', '_')}.html",
                mime="text/html",
                width="stretch",
                type="primary"
            )
            st.markdown("""
            <div style="color:#64748b;font-size:.8rem;margin:-8px 0 16px 4px;">
              Self-contained · Opens in any browser · Print to PDF via Ctrl+P
            </div>
            """, unsafe_allow_html=True)

            csv_data = generate_csv_export(report_data)
            st.download_button(
                label="📊 Download CSV Data Export",
                data=csv_data.encode("utf-8"),
                file_name=f"cmdss_data_{org_name.replace(' ', '_')}.csv",
                mime="text/csv",
                width="stretch"
            )
            st.markdown("""
            <div style="color:#64748b;font-size:.8rem;margin:-8px 0 16px 4px;">
              All metrics from all phases · Flat CSV format · Excel compatible
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 🔍 Report Preview")
            st.caption("Sections included in the HTML report:")
            for title, desc in [
                ("Cover page",         "Organisation name, date, pricing model, phase index"),
                ("Executive Summary",  "Key metrics table across all phases at a glance"),
                ("Phase 1 — TCO",      "Cost breakdown table + CapEx/OpEx + 5yr projection"),
                ("Phase 2 — Cost",     "Right-sizing table + provider comparison + savings"),
                ("Phase 3 — Risk",     "Risk factor table + adjusted costs + verdict banner"),
                ("Phase 4 — Strategy", "Migration strategy + DR plan + phased roadmap"),
                ("Phase 5 — ML",       "Prediction + confidence + XAI factors + decision path"),
            ]:
                st.markdown(
                    f'<div style="display:flex;gap:10px;padding:7px 12px;'
                    f'background:#1e293b;border-radius:6px;margin:3px 0;">'
                    f'<span style="color:#60a5fa;font-weight:600;min-width:160px;">{title}</span>'
                    f'<span style="color:#94a3b8;font-size:.85rem;">{desc}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown("""
            <div class="info-box" style="text-align:center;padding:32px;">
              <h3 style="color:#60a5fa;margin-bottom:8px;">No data yet</h3>
              <p>Complete at least <b>Phase 1</b> in the first tab to enable exports.</p>
            </div>
            """, unsafe_allow_html=True)


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
