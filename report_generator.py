"""
report_generator.py
Export Report Engine for CMDSS

Generates a self-contained, print-ready HTML report from session data.
Covers all 5 phases: TCO, Cost Analysis, Risk, Strategy, ML Prediction.
Also produces a CSV data export.
"""

from datetime import datetime
import io
import csv


# ── HTML Report ───────────────────────────────────────────────────────────────

def generate_html_report(report_data: dict) -> str:
    """
    Build a complete, self-contained HTML report string.

    Args:
        report_data: dict assembled by build_report_data() in app.py

    Returns:
        Full HTML string — ready to download as .html
    """
    generated_at = datetime.now().strftime("%d %B %Y, %H:%M")
    org_name     = report_data.get("org_name", "Organisation")
    pricing_label = {
        "on_demand":    "On-Demand",
        "reserved_1yr": "Reserved 1-Year",
        "reserved_3yr": "Reserved 3-Year"
    }.get(report_data.get("pricing_model", "on_demand"), "On-Demand")

    tco      = report_data.get("tco")
    cloud    = report_data.get("cloud")
    risk     = report_data.get("risk")
    strategy = report_data.get("strategy")
    ml       = report_data.get("ml")

    USD_TO_INR = 84.0

    # ── helpers ──
    def fmt(val, prefix="₹"):
        """Format a USD value as INR with Indian number grouping."""
        try:
            inr_val = float(val) * USD_TO_INR
            # Indian grouping: last 3 digits, then groups of 2
            s = f"{inr_val:,.0f}".replace(",", "")
            neg = s.startswith("-")
            if neg:
                s = s[1:]
            if len(s) > 3:
                last3 = s[-3:]
                rest = s[:-3]
                groups = []
                while len(rest) > 2:
                    groups.append(rest[-2:])
                    rest = rest[:-2]
                if rest:
                    groups.append(rest)
                groups.reverse()
                formatted = ",".join(groups) + "," + last3
            else:
                formatted = s
            sign = "-" if neg else ""
            return f"{prefix}{sign}{formatted}"
        except Exception:
            return str(val)

    def section(title, icon, content_html):
        return f"""
        <div class="section">
          <div class="section-header">
            <span class="section-icon">{icon}</span>
            {title}
          </div>
          <div class="section-body">
            {content_html}
          </div>
        </div>
        """

    def metric_grid(metrics: list[tuple]) -> str:
        """metrics = list of (label, value, sub) tuples"""
        cards = ""
        for label, value, sub in metrics:
            cards += f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
              {"<div class='metric-sub'>" + sub + "</div>" if sub else ""}
            </div>"""
        return f'<div class="metric-grid">{cards}</div>'

    def table(headers, rows):
        ths = "".join(f"<th>{h}</th>" for h in headers)
        trs = ""
        for row in rows:
            tds = "".join(f"<td>{cell}</td>" for cell in row)
            trs += f"<tr>{tds}</tr>"
        return f"""
        <table>
          <thead><tr>{ths}</tr></thead>
          <tbody>{trs}</tbody>
        </table>"""

    def badge(text, color="#1d4ed8"):
        return f'<span class="badge" style="background:{color};">{text}</span>'

    def roadmap_steps(steps):
        html = ""
        for i, step in enumerate(steps, 1):
            html += f"""
            <div class="roadmap-step">
              <div class="step-num">{i}</div>
              <div class="step-text">{step}</div>
            </div>"""
        return html

    # ── Phase 1 — TCO ────────────────────────────────────────────────────────
    if tco:
        tco_metrics = metric_grid([
            ("Servers",       tco["servers"],                     None),
            ("Storage",       f"{tco['storage_tb']} TB",          None),
            ("Annual OpEx",   fmt(tco["annual_operational_cost"]), None),
            ("3-Year TCO",    fmt(tco["tco_3yr"]),                 None),
            ("5-Year TCO",    fmt(tco["tco_5yr"]),                 None),
            ("Total CapEx",   fmt(tco["total_capex"]),             None),
        ])
        tco_table = table(
            ["Cost Component", "Annual Amount"],
            [
                ("Server Hardware CapEx",  fmt(tco["hardware_cost"])),
                ("Storage CapEx",          fmt(tco["storage_capex"])),
                ("Maintenance",            fmt(tco["annual_maintenance"])),
                ("Power & Cooling",        fmt(tco["annual_power"])),
                ("IT Staff",               fmt(tco["annual_staff"])),
                ("Storage OpEx",           fmt(tco["annual_storage_opex"])),
            ]
        )
        phase1_html = tco_metrics + "<h4>Cost Breakdown</h4>" + tco_table
    else:
        phase1_html = '<p class="na">Infrastructure data not available.</p>'

    # ── Phase 2 — Cost Analysis ───────────────────────────────────────────────
    if tco and cloud:
        bp           = cloud["best_provider"]
        cloud_yr     = cloud["costs"][bp]["selected"]
        onprem_yr    = tco["annual_operational_cost"]
        onprem_5yr   = tco["tco_5yr"]
        cloud_5yr    = cloud_yr * 5
        savings_5yr  = onprem_5yr - cloud_5yr
        savings_pct  = (savings_5yr / onprem_5yr * 100) if onprem_5yr else 0

        cost_metrics = metric_grid([
            ("Best Provider",        bp,                     None),
            ("On-Prem Annual",       fmt(onprem_yr),          None),
            ("Cloud Annual (Best)",  fmt(cloud_yr),           f"via {bp}"),
            ("Annual Saving",        fmt(onprem_yr - cloud_yr), f"{savings_pct:.1f}%"),
            ("On-Prem 5-Year TCO",   fmt(onprem_5yr),         None),
            ("Cloud 5-Year Cost",    fmt(cloud_5yr),          None),
            ("5-Year Saving",        fmt(savings_5yr),        f"{savings_pct:.1f}%"),
        ])

        # Right-sizing
        rs_html = f"""
        <h4>Right-Sizing Analysis</h4>
        <p>Workload type: <strong>{cloud.get('workload_type','').capitalize()}</strong>
        &nbsp;|&nbsp; Pricing model: <strong>{pricing_label}</strong></p>"""
        rs_html += table(
            ["Metric", "Before", "After", "Reduction"],
            [
                ("vCPU",  cloud["original_vcpu"],        cloud["recommended_vcpu"],
                 f"{cloud['cpu_reduction_pct']}%"),
                ("RAM",   f"{cloud['original_ram']} GB", f"{cloud['recommended_ram']} GB",
                 f"{cloud['ram_reduction_pct']}%"),
            ]
        )

        # Provider comparison
        prov_rows = []
        for prov, cdata in cloud["costs"].items():
            sel = cdata["selected"]
            sav = onprem_yr - sel
            pct = (sav / onprem_yr * 100) if onprem_yr else 0
            inst = cloud["instances"].get(prov, {})
            prov_rows.append((
                f"{'⭐ ' if prov == bp else ''}{prov}",
                inst.get("instance", "N/A"),
                f"{inst.get('vcpu','?')} vCPU / {inst.get('ram_gb','?')} GB",
                fmt(sel),
                fmt(sav) + f" ({pct:.1f}%)"
            ))

        prov_table = table(
            ["Provider", "Instance", "Specs", "Annual Cost", "Savings vs On-Prem"],
            prov_rows
        )

        phase2_html = cost_metrics + rs_html + "<h4>Provider Comparison</h4>" + prov_table
    else:
        phase2_html = '<p class="na">Cloud analysis not available. Run cloud analysis in Phase 1.</p>'

    # ── Phase 3 — Risk Analysis ───────────────────────────────────────────────
    if risk and tco and cloud:
        bp          = cloud["best_provider"]
        cloud_yr    = cloud["costs"][bp]["selected"]
        onprem_yr   = tco["annual_operational_cost"]
        risk_data   = risk["risk"]
        adj_cost    = risk["adj_cloud_cost"]
        adj_sav     = onprem_yr - adj_cost
        adj_pct     = (adj_sav / onprem_yr * 100) if onprem_yr else 0

        risk_metrics = metric_grid([
            ("Downtime Risk Cost",   fmt(risk_data["downtime_cost"]),   f"p={risk['inputs']['downtime_risk']:.0%}"),
            ("Compliance Risk Cost", fmt(risk_data["compliance_cost"]), f"p={risk['inputs']['compliance_risk']:.0%}"),
            ("Skill Gap Risk Cost",  fmt(risk_data["skill_cost"]),      f"p={risk['inputs']['skill_risk']:.0%}"),
            ("Total Risk Cost",      fmt(risk_data["total_risk_cost"]), None),
            ("Base Cloud Cost",      fmt(cloud_yr),                      None),
            ("Risk-Adjusted Cost",   fmt(adj_cost),                      None),
            ("Adjusted Savings",     fmt(adj_sav),                       f"{adj_pct:.1f}% vs on-prem"),
        ])

        risk_table = table(
            ["Risk Factor", "Probability", "Max Cost", "Expected Cost"],
            [
                ("Downtime",   f"{risk['inputs']['downtime_risk']:.0%}",
                 fmt(risk['inputs']['downtime_cost']),    fmt(risk_data["downtime_cost"])),
                ("Compliance", f"{risk['inputs']['compliance_risk']:.0%}",
                 fmt(risk['inputs']['compliance_penalty']), fmt(risk_data["compliance_cost"])),
                ("Skill Gap",  f"{risk['inputs']['skill_risk']:.0%}",
                 fmt(risk['inputs']['training_cost']),    fmt(risk_data["skill_cost"])),
            ]
        )

        verdict = (
            f'<div class="verdict-pass">✅ Migration recommended even after risk adjustment. '
            f'Net saving: {fmt(adj_sav)}/year ({adj_pct:.1f}%)</div>'
            if adj_sav > 0 else
            f'<div class="verdict-fail">⚠️ On-premise is more cost-effective after risk adjustment '
            f'by {fmt(abs(adj_sav))}/year. Review risk mitigations.</div>'
        )

        phase3_html = risk_metrics + "<h4>Risk Factor Detail</h4>" + risk_table + verdict
    else:
        phase3_html = '<p class="na">Risk analysis not available.</p>'

    # ── Phase 4 — Rule-Based Strategy ─────────────────────────────────────────
    if strategy:
        strat_name = strategy["strategy"]
        dr         = strategy["dr_plan"]
        roadmap    = strategy["roadmap"]
        inputs     = strategy["inputs"]

        strat_color = {
            "Lift-and-Shift":         "#1d4ed8",
            "Hybrid Migration":       "#c2410c",
            "Cloud-Native Migration": "#15803d"
        }.get(strat_name, "#1d4ed8")

        dr_color = {"Hot DR": "#dc2626", "Warm DR": "#d97706", "Cold DR": "#16a34a"}.get(dr, "#2563eb")

        inputs_table = table(
            ["Input Factor", "Selected Value"],
            [
                ("Compliance Level",  inputs["compliance"].capitalize()),
                ("Downtime Tolerance", inputs["downtime"].capitalize()),
                ("Growth Rate",        inputs["growth"].capitalize()),
            ]
        )

        phase4_html = f"""
        <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
          <div style="flex:1;min-width:200px;background:#f8fafc;border-radius:8px;padding:16px;border-left:4px solid {strat_color};">
            <div style="font-size:.8rem;color:#64748b;margin-bottom:6px;">MIGRATION STRATEGY</div>
            <div style="font-weight:700;font-size:1.1rem;color:{strat_color};">{strat_name}</div>
          </div>
          <div style="flex:1;min-width:200px;background:#f8fafc;border-radius:8px;padding:16px;border-left:4px solid {dr_color};">
            <div style="font-size:.8rem;color:#64748b;margin-bottom:6px;">DISASTER RECOVERY</div>
            <div style="font-weight:700;font-size:1.1rem;color:{dr_color};">🛡️ {dr}</div>
          </div>
        </div>
        <h4>Decision Inputs</h4>
        {inputs_table}
        <h4>Migration Roadmap</h4>
        {roadmap_steps(roadmap)}
        """
    else:
        phase4_html = '<p class="na">Strategy recommendation not available. Complete Phase 4 tab.</p>'

    # ── Phase 5 — ML Prediction ────────────────────────────────────────────────
    if ml:
        ml_strat  = ml["strategy"]
        ml_conf   = ml["confidence"]
        ml_factors = ml["top_factors"]
        ml_path    = ml["decision_path"]
        ml_inputs  = ml.get("inputs", {})

        ml_color = {
            "Hybrid":         "#c2410c",
            "Cloud-Native":   "#15803d",
            "Lift-and-Shift": "#1d4ed8"
        }.get(ml_strat, "#2563eb")

        factors_html = "".join(
            f'<div class="factor-item"><span class="factor-rank">#{i}</span>{f}</div>'
            for i, f in enumerate(ml_factors, 1)
        )

        path_html = "".join(
            f'<div class="path-rule">→ {rule}</div>'
            for rule in ml_path
        )

        inputs_table = table(
            ["Feature", "Value"],
            [(k.replace("_", " ").title(), str(v)) for k, v in ml_inputs.items()]
        ) if ml_inputs else ""

        phase5_html = f"""
        <div style="background:#f8fafc;border-radius:8px;padding:20px;
                    border-left:4px solid {ml_color};margin-bottom:20px;text-align:center;">
          <div style="font-size:.8rem;color:#64748b;margin-bottom:8px;">ML PREDICTED STRATEGY</div>
          <div style="font-size:1.4rem;font-weight:700;color:{ml_color};">{ml_strat}</div>
          <div style="color:#475569;margin-top:6px;">Confidence: <strong>{ml_conf}</strong></div>
        </div>

        {"<h4>Input Features Used</h4>" + inputs_table if inputs_table else ""}

        <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:16px;">
          <div style="flex:1;min-width:240px;">
            <h4>Top Influencing Factors (Global XAI)</h4>
            <div class="factors-list">{factors_html}</div>
          </div>
          <div style="flex:1;min-width:240px;">
            <h4>Decision Path (Local XAI)</h4>
            <div class="path-list">{path_html}</div>
          </div>
        </div>
        """
    else:
        phase5_html = '<p class="na">ML prediction not available. Complete Phase 5 tab.</p>'

    # ── Executive Summary ──────────────────────────────────────────────────────
    exec_rows = []
    if tco:
        exec_rows.append(("On-Prem 5-Year TCO", fmt(tco["tco_5yr"]), "Baseline cost"))
    if tco and cloud:
        bp       = cloud["best_provider"]
        cy       = cloud["costs"][bp]["selected"]
        c5yr     = cy * 5
        onp5yr   = tco["tco_5yr"]
        sav      = onp5yr - c5yr
        exec_rows.append(("Cloud 5-Year Cost",    fmt(c5yr),  f"Best: {bp}"))
        exec_rows.append(("Projected 5-Year Saving", fmt(sav), f"{(sav/onp5yr*100):.1f}%"))
    if risk and tco and cloud:
        exec_rows.append(("Risk-Adjusted Annual Cloud", fmt(risk["adj_cloud_cost"]), "Includes all risk costs"))
    if strategy:
        exec_rows.append(("Recommended Strategy", strategy["strategy"], "Rule engine"))
    if ml:
        exec_rows.append(("ML Predicted Strategy", ml["strategy"], f"Confidence: {ml['confidence']}"))

    exec_table = table(["Metric", "Value", "Notes"], exec_rows) if exec_rows else \
        '<p class="na">Complete all phases to populate the executive summary.</p>'

    # ── Assemble full HTML ─────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CMDSS Report — {org_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      font-size: 14px;
      line-height: 1.6;
    }}

    /* ── Cover ── */
    .cover {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
      color: white;
      padding: 60px 64px 48px;
      page-break-after: always;
    }}
    .cover-logo {{ font-size: 2.8rem; margin-bottom: 12px; }}
    .cover-title {{ font-size: 2rem; font-weight: 700; margin-bottom: 6px; }}
    .cover-sub {{ font-size: 1rem; color: #94a3b8; margin-bottom: 40px; }}
    .cover-org {{ font-size: 1.3rem; font-weight: 600; color: #60a5fa; margin-bottom: 4px; }}
    .cover-meta {{ color: #64748b; font-size: .9rem; }}
    .cover-divider {{ border: none; border-top: 1px solid #334155; margin: 32px 0; }}
    .cover-phases {{
      display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px;
    }}
    .cover-phase {{
      background: rgba(255,255,255,.08);
      border: 1px solid rgba(255,255,255,.15);
      border-radius: 6px;
      padding: 8px 16px;
      font-size: .82rem;
      color: #cbd5e1;
    }}

    /* ── Page wrapper ── */
    .page {{ max-width: 960px; margin: 0 auto; padding: 32px 24px; }}

    /* ── Executive Summary ── */
    .exec-summary {{
      background: white;
      border-radius: 12px;
      padding: 28px 32px;
      margin-bottom: 28px;
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
      border-top: 4px solid #2563eb;
    }}
    .exec-summary h2 {{ font-size: 1.2rem; color: #0f172a; margin-bottom: 16px; }}

    /* ── Section ── */
    .section {{
      background: white;
      border-radius: 12px;
      margin-bottom: 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
      overflow: hidden;
    }}
    .section-header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
      color: white;
      padding: 16px 24px;
      font-size: 1rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .section-icon {{ font-size: 1.2rem; }}
    .section-body {{ padding: 24px; }}

    /* ── Metric grid ── */
    .metric-grid {{
      display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
    }}
    .metric-card {{
      flex: 1; min-width: 140px;
      background: #f8fafc;
      border-radius: 8px;
      padding: 14px 16px;
      border: 1px solid #e2e8f0;
    }}
    .metric-label {{ font-size: .75rem; color: #64748b; text-transform: uppercase;
                     letter-spacing: .04em; margin-bottom: 4px; }}
    .metric-value {{ font-size: 1.15rem; font-weight: 700; color: #0f172a; }}
    .metric-sub   {{ font-size: .75rem; color: #2563eb; margin-top: 2px; }}

    /* ── Tables ── */
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px; font-size: .88rem; }}
    th {{
      background: #0f172a; color: white; text-align: left;
      padding: 10px 14px; font-weight: 600; font-size: .8rem;
    }}
    td {{ padding: 9px 14px; border-bottom: 1px solid #e2e8f0; color: #334155; }}
    tr:nth-child(even) td {{ background: #f8fafc; }}
    tr:last-child td {{ border-bottom: none; }}

    /* ── Roadmap ── */
    .roadmap-step {{
      display: flex; align-items: flex-start; gap: 12px;
      padding: 12px 16px; background: #f8fafc;
      border-left: 3px solid #2563eb;
      border-radius: 0 6px 6px 0;
      margin: 6px 0;
    }}
    .step-num {{
      background: #2563eb; color: white; border-radius: 50%;
      width: 24px; height: 24px; display: flex; align-items: center;
      justify-content: center; font-size: .75rem; font-weight: 700;
      flex-shrink: 0;
    }}
    .step-text {{ color: #1e293b; font-size: .88rem; padding-top: 2px; }}

    /* ── XAI ── */
    .factors-list, .path-list {{ margin-top: 8px; }}
    .factor-item {{
      display: flex; align-items: center; gap: 10px;
      padding: 8px 12px; background: #f8fafc;
      border-radius: 6px; margin: 4px 0; font-size: .85rem;
    }}
    .factor-rank {{
      background: #2563eb; color: white; border-radius: 50%;
      width: 22px; height: 22px; display: flex; align-items: center;
      justify-content: center; font-size: .72rem; font-weight: 700;
      flex-shrink: 0;
    }}
    .path-rule {{
      font-family: monospace; font-size: .82rem;
      color: #1e40af; background: #eff6ff;
      border: 1px solid #bfdbfe; border-radius: 4px;
      padding: 7px 12px; margin: 4px 0;
    }}

    /* ── Verdict banners ── */
    .verdict-pass {{
      background: #f0fdf4; border: 1px solid #86efac;
      border-left: 4px solid #16a34a; border-radius: 6px;
      padding: 12px 16px; color: #166534; margin-top: 12px; font-weight: 500;
    }}
    .verdict-fail {{
      background: #fff7ed; border: 1px solid #fdba74;
      border-left: 4px solid #d97706; border-radius: 6px;
      padding: 12px 16px; color: #92400e; margin-top: 12px; font-weight: 500;
    }}

    /* ── Misc ── */
    .badge {{
      display: inline-block; color: white; padding: 3px 12px;
      border-radius: 20px; font-size: .78rem; font-weight: 600;
    }}
    .na {{ color: #94a3b8; font-style: italic; padding: 8px 0; }}
    h4 {{ font-size: .92rem; font-weight: 600; color: #0f172a;
          margin: 16px 0 8px; text-transform: uppercase;
          letter-spacing: .04em; border-bottom: 1px solid #e2e8f0;
          padding-bottom: 4px; }}

    /* ── Footer ── */
    .report-footer {{
      text-align: center; color: #94a3b8; font-size: .78rem;
      padding: 24px 0 40px; border-top: 1px solid #e2e8f0; margin-top: 8px;
    }}

    /* ── Print ── */
    @media print {{
      body {{ background: white; }}
      .cover {{ page-break-after: always; }}
      .section {{ page-break-inside: avoid; box-shadow: none; border: 1px solid #e2e8f0; }}
      .exec-summary {{ box-shadow: none; border: 1px solid #e2e8f0; }}
    }}
  </style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <div class="cover-logo">☁️</div>
  <div class="cover-title">Cloud Migration Decision Support System</div>
  <div class="cover-sub">Infrastructure Analysis &amp; Migration Intelligence Report</div>
  <hr class="cover-divider">
  <div class="cover-org">{org_name}</div>
  <div class="cover-meta">
    Generated: {generated_at} &nbsp;·&nbsp;
    Pricing Model: {pricing_label}
  </div>
  <div class="cover-phases">
    <div class="cover-phase">📦 Phase 1: TCO Engine</div>
    <div class="cover-phase">💰 Phase 2: Cost Analysis</div>
    <div class="cover-phase">⚠️ Phase 3: Risk Analysis</div>
    <div class="cover-phase">🧭 Phase 4: Rule Engine</div>
    <div class="cover-phase">🤖 Phase 5: ML Prediction</div>
  </div>
</div>

<!-- CONTENT -->
<div class="page">

  <!-- Executive Summary -->
  <div class="exec-summary">
    <h2>📋 Executive Summary</h2>
    {exec_table}
  </div>

  {section("Phase 1 — On-Premise TCO", "📦", phase1_html)}
  {section("Phase 2 — Cost Analysis &amp; Cloud Comparison", "💰", phase2_html)}
  {section("Phase 3 — Risk-Adjusted Analysis", "⚠️", phase3_html)}
  {section("Phase 4 — Rule-Based Strategy Recommendation", "🧭", phase4_html)}
  {section("Phase 5 — Machine Learning Prediction", "🤖", phase5_html)}

  <div class="report-footer">
    Cloud Migration Decision Support System &nbsp;·&nbsp;
    Generated {generated_at} &nbsp;·&nbsp;
    {org_name} &nbsp;·&nbsp; Pricing: {pricing_label}
  </div>
</div>

</body>
</html>"""

    return html


# ── CSV Export ────────────────────────────────────────────────────────────────

def generate_csv_export(report_data: dict) -> str:
    """
    Produce a flat CSV string covering all key metrics from all phases.

    Returns:
        CSV string — ready to download as .csv
    """
    output = io.StringIO()
    writer = csv.writer(output)

    tco      = report_data.get("tco")
    cloud    = report_data.get("cloud")
    risk     = report_data.get("risk")
    strategy = report_data.get("strategy")
    ml       = report_data.get("ml")

    writer.writerow(["CMDSS Export", report_data.get("org_name", "Organisation"),
                     datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow([])

    # Phase 1
    writer.writerow(["=== PHASE 1: ON-PREMISE TCO ==="])
    writer.writerow(["Metric", "Value"])
    if tco:
        for k, v in [
            ("Servers",              tco["servers"]),
            ("Storage (TB)",         tco["storage_tb"]),
            ("Hardware CapEx (₹)",   tco["hardware_cost"]),
            ("Storage CapEx (₹)",    tco["storage_capex"]),
            ("Total CapEx (₹)",      tco["total_capex"]),
            ("Annual Maintenance (₹)", tco["annual_maintenance"]),
            ("Annual Power (₹)",     tco["annual_power"]),
            ("Annual IT Staff (₹)",  tco["annual_staff"]),
            ("Annual Storage OpEx (₹)", tco["annual_storage_opex"]),
            ("Annual OpEx (₹)",      tco["annual_operational_cost"]),
            ("3-Year TCO (₹)",       tco["tco_3yr"]),
            ("5-Year TCO (₹)",       tco["tco_5yr"]),
        ]:
            writer.writerow([k, round(v, 2)])
    else:
        writer.writerow(["N/A", ""])
    writer.writerow([])

    # Phase 2
    writer.writerow(["=== PHASE 2: CLOUD COST ANALYSIS ==="])
    writer.writerow(["Metric", "Value"])
    if tco and cloud:
        bp       = cloud["best_provider"]
        cloud_yr = cloud["costs"][bp]["selected"]
        onp_yr   = tco["annual_operational_cost"]
        onp_5yr  = tco["tco_5yr"]
        cloud_5yr = cloud_yr * 5
        for k, v in [
            ("Best Provider",          bp),
            ("Pricing Model",          report_data.get("pricing_model", "")),
            ("Workload Type",          cloud.get("workload_type", "")),
            ("Recommended vCPU",       cloud["recommended_vcpu"]),
            ("Recommended RAM (GB)",   cloud["recommended_ram"]),
            ("CPU Reduction (%)",      cloud["cpu_reduction_pct"]),
            ("RAM Reduction (%)",      cloud["ram_reduction_pct"]),
            ("On-Prem Annual (₹)",     round(onp_yr, 2)),
            ("Best Cloud Annual (₹)",  round(cloud_yr, 2)),
            ("Annual Saving (₹)",      round(onp_yr - cloud_yr, 2)),
            ("On-Prem 5yr (₹)",        round(onp_5yr, 2)),
            ("Cloud 5yr (₹)",          round(cloud_5yr, 2)),
            ("5yr Saving (₹)",         round(onp_5yr - cloud_5yr, 2)),
        ]:
            writer.writerow([k, v])
        writer.writerow([])
        writer.writerow(["Provider", "Instance", "vCPU", "RAM (GB)",
                         "On-Demand (₹)", "Reserved 1yr (₹)", "Reserved 3yr (₹)", "Selected (₹)"])
        for prov, cdata in cloud["costs"].items():
            inst = cloud["instances"].get(prov, {})
            writer.writerow([
                prov,
                inst.get("instance", ""),
                inst.get("vcpu", ""),
                inst.get("ram_gb", ""),
                round(cdata["on_demand"], 2),
                round(cdata["reserved_1yr"], 2),
                round(cdata["reserved_3yr"], 2),
                round(cdata["selected"], 2),
            ])
    else:
        writer.writerow(["N/A", ""])
    writer.writerow([])

    # Phase 3
    writer.writerow(["=== PHASE 3: RISK ANALYSIS ==="])
    writer.writerow(["Metric", "Value"])
    if risk:
        rd = risk["risk"]
        ri = risk["inputs"]
        for k, v in [
            ("Downtime Risk Probability",   ri["downtime_risk"]),
            ("Downtime Max Cost (₹)",        ri["downtime_cost"]),
            ("Downtime Expected Cost (₹)",   round(rd["downtime_cost"], 2)),
            ("Compliance Risk Probability",  ri["compliance_risk"]),
            ("Compliance Penalty (₹)",       ri["compliance_penalty"]),
            ("Compliance Expected Cost (₹)", round(rd["compliance_cost"], 2)),
            ("Skill Gap Risk Probability",   ri["skill_risk"]),
            ("Training Cost (₹)",            ri["training_cost"]),
            ("Skill Gap Expected Cost (₹)",  round(rd["skill_cost"], 2)),
            ("Total Risk Cost (₹)",          round(rd["total_risk_cost"], 2)),
            ("Risk-Adjusted Cloud Cost (₹)", round(risk["adj_cloud_cost"], 2)),
        ]:
            writer.writerow([k, v])
    else:
        writer.writerow(["N/A", ""])
    writer.writerow([])

    # Phase 4
    writer.writerow(["=== PHASE 4: RULE-BASED STRATEGY ==="])
    writer.writerow(["Metric", "Value"])
    if strategy:
        writer.writerow(["Compliance Level",   strategy["inputs"]["compliance"]])
        writer.writerow(["Downtime Tolerance", strategy["inputs"]["downtime"]])
        writer.writerow(["Growth Rate",        strategy["inputs"]["growth"]])
        writer.writerow(["Recommended Strategy", strategy["strategy"]])
        writer.writerow(["DR Plan",            strategy["dr_plan"]])
        writer.writerow([])
        writer.writerow(["Roadmap Step", "Description"])
        for step in strategy["roadmap"]:
            writer.writerow(["", step])
    else:
        writer.writerow(["N/A", ""])
    writer.writerow([])

    # Phase 5
    writer.writerow(["=== PHASE 5: ML PREDICTION ==="])
    writer.writerow(["Metric", "Value"])
    if ml:
        writer.writerow(["ML Strategy",  ml["strategy"]])
        writer.writerow(["Confidence",   ml["confidence"]])
        writer.writerow([])
        writer.writerow(["Input Feature", "Value"])
        for k, v in ml.get("inputs", {}).items():
            writer.writerow([k.replace("_", " ").title(), v])
        writer.writerow([])
        writer.writerow(["Top Factor Rank", "Feature"])
        for i, f in enumerate(ml["top_factors"], 1):
            writer.writerow([f"#{i}", f])
        writer.writerow([])
        writer.writerow(["Decision Path Rule"])
        for rule in ml["decision_path"]:
            writer.writerow([rule])
    else:
        writer.writerow(["N/A", ""])

    return output.getvalue()