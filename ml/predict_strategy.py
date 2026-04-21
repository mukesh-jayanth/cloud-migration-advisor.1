"""
predict_strategy.py
Phase 5 — Friction Narrative & Failure Probability Predictor

This module evaluates the RISK of the strategy chosen by the rule engine,
rather than picking a strategy itself.  Its responsibilities:

  1. Friction Report — identifies mismatches between strategy, budget,
     and infrastructure state (budget–compliance deadlocks, payback
     fragility, zombie waste carry-over).
  2. Failure Probability — estimates the likelihood of project failure
     or abandonment based on accumulated friction signals.

The actual migration strategy decision is made by the rule_engine and
decision_engine. This module provides the "executive verdict" layer.

Placement: Phase 5 — AI System Auditor (Friction & Failure Predictor)
"""

import math
from logger_config import get_logger

logger = get_logger(__name__)


from config_loader import get_config_val

# ─────────────────────────────────────────────────────────────────────────────
# Strategy Cost Tiers & Labor Multipliers
# ─────────────────────────────────────────────────────────────────────────────

STRATEGY_COST_TIER = get_config_val('strategy_prediction.strategy_cost_tier', {
    "Lift-and-Shift":         1,
    "Retain On-Premise":      1,
    "Hybrid Migration":       2,
    "Cloud-Native Migration": 3,
})

STRATEGY_LABOR_MULT = get_config_val('strategy_prediction.strategy_labor_mult', {
    "Lift-and-Shift":         1.0,
    "Retain On-Premise":      1.0,
    "Hybrid Migration":       3.0,
    "Cloud-Native Migration": 10.0,
})

BASE_FAILURE_RATES = get_config_val('strategy_prediction.base_failure_rates', {
    "Lift-and-Shift":         0.08,
    "Retain On-Premise":      0.05,
    "Hybrid Migration":       0.22,
    "Cloud-Native Migration": 0.38,
})

BUDGET_LABELS = {
    "low":    "Low Budget / Cost-Sensitive",
    "medium": "Moderate Budget",
    "high":   "Flexible / High Budget",
}


# ─────────────────────────────────────────────────────────────────────────────
# Failure Probability Calculator
# ─────────────────────────────────────────────────────────────────────────────

def calculate_failure_probability(
    strategy:          str,
    budget_level:      str,
    servers:           int,
    migration_premium: float = None,
    annual_saving:     float = None,
    has_skilled_team:  bool  = False,
    has_cicd:          bool  = False,
    zombie_count:      int   = 0,
    nlp_risk_score:    int   = 0,
) -> dict:
    """
    Estimate the probability of migration project failure or abandonment.

    Factors that INCREASE failure probability:
        - High-complexity strategy (Cloud-Native)
        - Low budget with high-cost strategy (budget–strategy mismatch)
        - Large server count (more moving parts)
        - Long payback period (>3 years)
        - Zombie servers (migrating waste)
        - NLP-detected risk concerns

    Factors that DECREASE failure probability:
        - Skilled team (cloud expertise)
        - Automated CI/CD pipelines
        - Positive ROI with short payback

    Returns:
        {
            "base_rate"         : float,  # starting failure rate for strategy
            "adjustments"       : list[dict],  # each adjustment with reason
            "final_probability" : float,  # 0.0–1.0
            "risk_tier"         : str,    # "Low" | "Medium" | "High" | "Critical"
            "verdict"           : str,    # human-readable executive verdict
        }
    """
    base_rate   = BASE_FAILURE_RATES.get(strategy, 0.20)
    adjustments = []
    prob        = base_rate

    cost_tier  = STRATEGY_COST_TIER.get(strategy, 1)
    labor_mult = STRATEGY_LABOR_MULT.get(strategy, 1.0)

    # ── Budget–Strategy Mismatch ─────────────────────────────────────────
    if budget_level == "low" and cost_tier >= 3:
        adj = 0.25
        prob += adj
        adjustments.append({
            "factor": "Budget–Strategy Deadlock",
            "adjustment": f"+{adj:.0%}",
            "reason": (
                f"Low budget with {strategy} (×{labor_mult:.0f} labour multiplier) "
                f"creates a high probability of project stall. "
                f"Projects of this type routinely exceed estimates by 3–5×."
            ),
        })
    elif budget_level == "low" and cost_tier >= 2:
        adj = 0.10
        prob += adj
        adjustments.append({
            "factor": "Budget Pressure",
            "adjustment": f"+{adj:.0%}",
            "reason": (
                f"Low budget with {strategy} increases risk of corner-cutting. "
                f"Allocate ≥30% contingency reserve."
            ),
        })

    # ── Server Count Complexity ──────────────────────────────────────────
    if servers >= 100:
        adj = 0.12
        prob += adj
        adjustments.append({
            "factor": "Large Estate Complexity",
            "adjustment": f"+{adj:.0%}",
            "reason": (
                f"{servers} servers increases coordination overhead. "
                "Phased migration in batches of ≤25 is strongly recommended."
            ),
        })
    elif servers >= 50:
        adj = 0.05
        prob += adj
        adjustments.append({
            "factor": "Medium Estate Complexity",
            "adjustment": f"+{adj:.0%}",
            "reason": f"{servers} servers — moderate coordination risk.",
        })

    # ── Payback Period Fragility ─────────────────────────────────────────
    if migration_premium is not None and annual_saving is not None:
        if annual_saving <= 0:
            adj = 0.20
            prob += adj
            adjustments.append({
                "factor": "Negative ROI",
                "adjustment": f"+{adj:.0%}",
                "reason": (
                    "Cloud annual cost exceeds on-prem — migration has no positive ROI. "
                    "This is the strongest predictor of project abandonment."
                ),
            })
        else:
            payback_years = migration_premium / annual_saving
            if payback_years > 5:
                adj = 0.15
                prob += adj
                adjustments.append({
                    "factor": "Very Long Payback",
                    "adjustment": f"+{adj:.0%}",
                    "reason": (
                        f"Payback period of ~{payback_years:.1f} years. "
                        "Cloud pricing cycles invalidate 5+ year projections."
                    ),
                })
            elif payback_years > 3:
                adj = 0.08
                prob += adj
                adjustments.append({
                    "factor": "Long Payback Period",
                    "adjustment": f"+{adj:.0%}",
                    "reason": (
                        f"Payback period of ~{payback_years:.1f} years "
                        "(industry guideline: ≤2 years)."
                    ),
                })

    # ── Zombie Servers ───────────────────────────────────────────────────
    if zombie_count > 0:
        adj = min(0.15, zombie_count * 0.04)
        prob += adj
        adjustments.append({
            "factor": "Zombie Server Waste",
            "adjustment": f"+{adj:.0%}",
            "reason": (
                f"{zombie_count} zombie server(s) detected. Migrating idle "
                "infrastructure locks in wasted cloud spend and inflates bills."
            ),
        })

    # ── NLP-Detected Concerns ────────────────────────────────────────────
    if nlp_risk_score >= 6:
        adj = 0.10
        prob += adj
        adjustments.append({
            "factor": "Multiple Unstructured Risks",
            "adjustment": f"+{adj:.0%}",
            "reason": (
                f"NLP analysis flagged {nlp_risk_score} risk points from "
                "stakeholder concerns. Multiple overlapping fears compound "
                "the probability of execution failure."
            ),
        })
    elif nlp_risk_score >= 3:
        adj = 0.05
        prob += adj
        adjustments.append({
            "factor": "Stakeholder Risk Concerns",
            "adjustment": f"+{adj:.0%}",
            "reason": "NLP analysis detected moderate-level migration concerns.",
        })

    # ── Risk-Reducing Factors ────────────────────────────────────────────
    if has_skilled_team:
        adj = -0.12
        prob += adj
        adjustments.append({
            "factor": "Skilled Cloud Team",
            "adjustment": f"{adj:.0%}",
            "reason": "Experienced team reduces execution risk significantly.",
        })

    if has_cicd:
        adj = -0.08
        prob += adj
        adjustments.append({
            "factor": "CI/CD Automation",
            "adjustment": f"{adj:.0%}",
            "reason": (
                "Automated deployment pipelines reduce manual error risk "
                "and enable faster rollback."
            ),
        })

    # ── Clamp to [0.02, 0.95] ────────────────────────────────────────────
    final_prob = max(0.02, min(0.95, prob))

    # ── Risk tier ────────────────────────────────────────────────────────
    if final_prob >= 0.60:
        risk_tier = "Critical"
    elif final_prob >= 0.35:
        risk_tier = "High"
    elif final_prob >= 0.15:
        risk_tier = "Medium"
    else:
        risk_tier = "Low"

    # ── Executive verdict ────────────────────────────────────────────────
    icon = {"Low": "✅", "Medium": "⚠️", "High": "🔴", "Critical": "⛔"}[risk_tier]

    if risk_tier == "Critical":
        verdict = (
            f"{icon} CRITICAL RISK ({final_prob:.0%} failure probability): "
            f"The {strategy} strategy has a very high likelihood of project "
            f"failure or abandonment given current constraints. "
            f"Strongly recommend re-evaluating the strategy or addressing "
            f"the {len(adjustments)} identified risk factors before proceeding."
        )
    elif risk_tier == "High":
        verdict = (
            f"{icon} HIGH RISK ({final_prob:.0%} failure probability): "
            f"The {strategy} strategy carries significant execution risk. "
            f"{len([a for a in adjustments if not a['adjustment'].startswith('-')])} "
            f"risk factor(s) are actively increasing failure probability."
        )
    elif risk_tier == "Medium":
        verdict = (
            f"{icon} MODERATE RISK ({final_prob:.0%} failure probability): "
            f"The {strategy} strategy is viable but has friction points. "
            f"Address the identified concerns to improve success odds."
        )
    else:
        verdict = (
            f"{icon} LOW RISK ({final_prob:.0%} failure probability): "
            f"The {strategy} strategy is well-supported by current conditions. "
            f"Proceed with standard migration governance."
        )

    return {
        "base_rate":          round(base_rate, 3),
        "adjustments":        adjustments,
        "final_probability":  round(final_prob, 3),
        "risk_tier":          risk_tier,
        "verdict":            verdict,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Friction Report Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_friction_report(
    strategy:          str,
    budget_level:      str,
    cloud_annual:      float,
    onprem_annual:     float,
    servers:           int,
    migration_premium: float = None,
    zombie_report:     dict  = None,
) -> dict:
    """
    Generate a Friction Report — risk narrative identifying mismatches
    between the recommended strategy, budget, and infrastructure state.

    Returns:
        {
            "risk_level"     : "Low" | "Medium" | "High" | "Critical",
            "risk_score"     : int,
            "warnings"       : list[str],
            "narrative"      : str,
            "recommendations": list[str],
        }
    """
    warnings        = []
    recommendations = []
    risk_score      = 0

    cost_tier  = STRATEGY_COST_TIER.get(strategy, 1)
    labor_mult = STRATEGY_LABOR_MULT.get(strategy, 1.0)

    # ── Budget vs Strategy mismatch ──────────────────────────────────────
    if budget_level == "low" and cost_tier >= 3:
        annual_saving = onprem_annual - cloud_annual
        if migration_premium and annual_saving > 0:
            labor_pct = (migration_premium / (annual_saving * 3)) * 100
            warnings.append(
                f"High probability of project stall: Refactor labor costs "
                f"({labor_mult:.0f}x multiplier) exceed budget flexibility by "
                f"~{labor_pct:.0f}% of 3-year savings."
            )
        else:
            warnings.append(
                f"High probability of project stall: {strategy} requires a "
                f"{labor_mult:.0f}x labor multiplier but budget is marked Low. "
                "Projects of this type routinely exceed initial estimates by 3-5×."
            )
        recommendations.append(
            "Consider starting with Lift-and-Shift (Rehost) to achieve quick wins "
            "before investing in refactoring."
        )
        risk_score += 3

    elif budget_level == "low" and cost_tier == 2:
        warnings.append(
            f"Moderate risk: {strategy} has a {labor_mult:.1f}x labor overhead. "
            "Low-budget projects should allocate a contingency reserve of ≥30%."
        )
        recommendations.append(
            "Allocate a 30% cost contingency before committing to this strategy."
        )
        risk_score += 1

    # ── Savings viability ────────────────────────────────────────────────
    annual_saving = onprem_annual - cloud_annual
    if annual_saving <= 0:
        warnings.append(
            "⛔ Cloud annual cost exceeds on-prem cost. Migration has no positive ROI. "
            "Review instance selection and pricing model."
        )
        risk_score += 4
    elif migration_premium and annual_saving > 0:
        payback_years = migration_premium / annual_saving
        if payback_years > 5:
            warnings.append(
                f"⛔ Very long payback: {payback_years:.1f} years. "
                "Most cloud pricing cycles invalidate 5+ year projections."
            )
            risk_score += 3
        elif payback_years > 3:
            warnings.append(
                f"Long payback period: migration investment recovers in "
                f"~{payback_years:.1f} years. Industry guideline is ≤2 years."
            )
            risk_score += 2

    # ── Zombie server carry-over ─────────────────────────────────────────
    if zombie_report and zombie_report.get("zombie_count", 0) > 0:
        zc  = zombie_report["zombie_count"]
        pct = zombie_report["potential_savings_pct"]
        warnings.append(
            f"{zc} zombie server(s) detected ({pct}% wasted capacity). "
            "Migrating these to cloud without right-sizing will lock in wasted spend."
        )
        recommendations.append(
            f"Right-size or decommission all {zc} zombie server(s) BEFORE migration "
            "to avoid paying for idle capacity twice."
        )
        risk_score += max(1, zc // 2)

    # ── Risk level ───────────────────────────────────────────────────────
    if risk_score >= 5:
        risk_level = "Critical"
    elif risk_score >= 3:
        risk_level = "High"
    elif risk_score >= 1:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # ── Narrative ────────────────────────────────────────────────────────
    icon = {"Low": "✅", "Medium": "⚠️", "High": "🔴", "Critical": "⛔"}[risk_level]

    if not warnings:
        narrative = (
            f"{icon} {risk_level} Risk: The selected strategy ({strategy}) is "
            f"well-matched to your budget and infrastructure profile. "
            f"Proceed with standard migration governance."
        )
    else:
        narrative = (
            f"{icon} {risk_level} Risk — {len(warnings)} concern(s) identified:\n"
            + "\n".join(f"  • {w}" for w in warnings)
        )
        if recommendations:
            narrative += (
                "\n\nRecommended Mitigations:\n"
                + "\n".join(f"  → {r}" for r in recommendations)
            )

    return {
        "risk_level":      risk_level,
        "risk_score":      risk_score,
        "warnings":        warnings,
        "narrative":       narrative,
        "recommendations": recommendations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full System Audit
# ─────────────────────────────────────────────────────────────────────────────

def run_system_audit(
    strategy:          str,
    budget_level:      str,
    cloud_annual:      float,
    onprem_annual:     float,
    servers:           int,
    server_list:       list[dict] = None,
    migration_premium: float      = None,
    has_skilled_team:  bool       = False,
    has_cicd:          bool       = False,
    nlp_risk_score:    int        = 0,
) -> dict:
    """
    Run the full AI System Audit:
      1. Friction Report Generation
      2. Failure Probability Calculation

    Returns combined audit result.
    """
    # Import here to avoid circular imports
    from ml.zombie_detector import detect_zombie_servers

    zombie_report = detect_zombie_servers(server_list) if server_list else None
    zombie_count  = zombie_report["zombie_count"] if zombie_report else 0

    friction_report = generate_friction_report(
        strategy          = strategy,
        budget_level      = budget_level,
        cloud_annual      = cloud_annual,
        onprem_annual     = onprem_annual,
        servers           = servers,
        migration_premium = migration_premium,
        zombie_report     = zombie_report,
    )

    annual_saving = onprem_annual - cloud_annual

    failure_prob = calculate_failure_probability(
        strategy          = strategy,
        budget_level      = budget_level,
        servers           = servers,
        migration_premium = migration_premium,
        annual_saving     = annual_saving,
        has_skilled_team  = has_skilled_team,
        has_cicd          = has_cicd,
        zombie_count      = zombie_count,
        nlp_risk_score    = nlp_risk_score,
    )

    return {
        "zombie_detection":   zombie_report,
        "friction_report":    friction_report,
        "failure_probability": failure_prob,
        "overall_risk":       failure_prob["risk_tier"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== AI System Auditor — Friction & Failure Predictor Demo ===\n")

    # Demo friction report
    fr = generate_friction_report(
        strategy          = "Cloud-Native Migration",
        budget_level      = "low",
        cloud_annual      = 120_000,
        onprem_annual     = 150_000,
        servers           = 50,
        migration_premium = 600_000,
    )
    print(f"Friction Report [{fr['risk_level']}]:\n{fr['narrative']}\n")

    # Demo failure probability
    fp = calculate_failure_probability(
        strategy          = "Cloud-Native Migration",
        budget_level      = "low",
        servers           = 50,
        migration_premium = 600_000,
        annual_saving     = 30_000,
        has_skilled_team  = False,
        has_cicd          = False,
        zombie_count      = 2,
        nlp_risk_score    = 5,
    )
    print(f"Failure Probability: {fp['final_probability']:.0%}")
    print(f"Risk Tier: {fp['risk_tier']}")
    print(f"Verdict: {fp['verdict']}")
    print(f"\nAdjustments:")
    for a in fp["adjustments"]:
        print(f"  {a['adjustment']:>5}  {a['factor']}: {a['reason']}")