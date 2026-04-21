"""
risk_nlp.py
Phase 3 — NLP Fear Classifier

Scans free-text user input describing migration concerns and classifies
the text into structured risk categories.  Each detected category maps
to a probability adjustment and a financial penalty, turning subjective
fears into calculated financial friction points.

Placement: Phase 3 — Risk Analysis (below the probability sliders)
"""

import re
from logger_config import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Category Definitions
# ─────────────────────────────────────────────────────────────────────────────
# Each category has:
#   - keywords       : trigger phrases (case-insensitive)
#   - risk_field      : which risk slider it maps to
#   - prob_adjustment : how much to increase the slider (additive)
#   - penalty_pct     : additional financial penalty as % of cloud cost
#   - severity        : default severity when detected
#   - mitigation      : recommended action to reduce this risk

RISK_CATEGORIES = {
    "downtime_availability": {
        "label":           "Downtime & Availability",
        "icon":            "🔴",
        "keywords":        [
            "downtime", "outage", "availability", "uptime", "sla",
            "service level", "interruption", "failover", "disaster",
            "recovery", "rto", "rpo", "business continuity",
        ],
        "risk_field":      "downtime_risk",
        "prob_adjustment": 0.15,
        "penalty_pct":     0.08,
        "severity":        "High",
        "mitigation": (
            "Implement a phased cutover with rollback windows. "
            "Negotiate SLA-backed uptime guarantees with the cloud provider. "
            "Budget for Hot DR or Warm DR standby infrastructure."
        ),
    },
    "data_security": {
        "label":           "Data Security & Compliance",
        "icon":            "🔒",
        "keywords":        [
            "data loss", "breach", "security", "gdpr", "hipaa", "pci",
            "compliance", "encryption", "privacy", "regulated",
            "data sovereignty", "audit", "iso 27001", "soc 2",
            "sensitive data", "personally identifiable", "pii",
        ],
        "risk_field":      "compliance_risk",
        "prob_adjustment": 0.20,
        "penalty_pct":     0.12,
        "severity":        "Critical",
        "mitigation": (
            "Engage a compliance consultant before migration. "
            "Use dedicated/isolated cloud tenancies for regulated workloads. "
            "Budget for encryption-at-rest, key management, and audit logging."
        ),
    },
    "cost_overruns": {
        "label":           "Cost Overruns & Budget",
        "icon":            "💸",
        "keywords":        [
            "budget", "cost", "expensive", "over budget", "price increase",
            "overspend", "hidden cost", "billing shock", "run rate",
            "afford", "tight budget", "cost-sensitive", "financial risk",
        ],
        "risk_field":      "compliance_risk",  # maps to general financial risk
        "prob_adjustment": 0.10,
        "penalty_pct":     0.10,
        "severity":        "High",
        "mitigation": (
            "Implement cloud cost governance (budgets, alerts, tagging). "
            "Start with reserved instances to cap run-rate costs. "
            "Allocate a 30% contingency reserve for migration labour."
        ),
    },
    "skill_gap": {
        "label":           "Skill Gap & Team Readiness",
        "icon":            "👥",
        "keywords":        [
            "skill gap", "training", "team", "expertise", "learning curve",
            "kubernetes", "k8s", "docker", "cloud experience",
            "staffing", "hire", "retention", "knowledge",
            "inexperienced", "unfamiliar",
        ],
        "risk_field":      "skill_risk",
        "prob_adjustment": 0.25,
        "penalty_pct":     0.06,
        "severity":        "High",
        "mitigation": (
            "Invest in cloud certification programmes before migration begins. "
            "Engage a Managed Services Provider (MSP) for the first 6–12 months. "
            "Budget for at least 2 months of parallel-running knowledge transfer."
        ),
    },
    "vendor_lockin": {
        "label":           "Vendor Lock-in",
        "icon":            "🔗",
        "keywords":        [
            "lock-in", "vendor lock", "proprietary", "portability",
            "multi-cloud", "exit strategy", "switching cost",
            "dependency", "single vendor",
        ],
        "risk_field":      "compliance_risk",
        "prob_adjustment": 0.05,
        "penalty_pct":     0.05,
        "severity":        "Medium",
        "mitigation": (
            "Prefer open-source and portable technologies (Kubernetes, Terraform). "
            "Abstract provider-specific services behind interfaces. "
            "Document an exit plan with estimated switching costs."
        ),
    },
    "timeline_delays": {
        "label":           "Timeline & Delays",
        "icon":            "⏱️",
        "keywords":        [
            "deadline", "delay", "timeline", "schedule", "late",
            "behind schedule", "overrun", "rush", "time pressure",
            "go-live", "cutover date",
        ],
        "risk_field":      "downtime_risk",
        "prob_adjustment": 0.10,
        "penalty_pct":     0.07,
        "severity":        "Medium",
        "mitigation": (
            "Build a 2-month buffer into the migration timeline. "
            "Use phased migration (start with non-critical workloads). "
            "Budget for double-run costs during the extended transition window."
        ),
    },
    "performance": {
        "label":           "Performance Degradation",
        "icon":            "📉",
        "keywords":        [
            "latency", "performance", "slow", "throughput", "response time",
            "bandwidth", "network lag", "degradation", "speed",
        ],
        "risk_field":      "downtime_risk",
        "prob_adjustment": 0.10,
        "penalty_pct":     0.05,
        "severity":        "Medium",
        "mitigation": (
            "Conduct a network latency baseline before migration. "
            "Use CDN and edge caching for latency-sensitive workloads. "
            "Right-size instance types based on actual I/O profiles, not just CPU/RAM."
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Core NLP Classifier
# ─────────────────────────────────────────────────────────────────────────────

def analyze_migration_concerns(
    text: str,
    cloud_annual: float = 0.0,
) -> dict:
    """
    Classify free-text migration concerns into structured risk categories.

    Args:
        text          : User's free-text description of migration fears
        cloud_annual  : Annual cloud cost (used to compute financial penalties)

    Returns:
        {
            "detected_categories"  : list[dict],  # matched risk categories with details
            "risk_score"           : int,          # cumulative severity score
            "risk_level"           : str,          # "Low" | "Medium" | "High" | "Critical"
            "probability_adjustments": dict,       # risk_field → total adjustment
            "total_penalty"        : float,        # total financial penalty amount
            "narrative"            : str,          # human-readable risk narrative
            "recommendations"      : list[str],   # consolidated mitigations
        }
    """
    if not text or not text.strip():
        return {
            "detected_categories":    [],
            "risk_score":             0,
            "risk_level":             "None",
            "probability_adjustments": {},
            "total_penalty":          0.0,
            "narrative":              "No migration concerns provided.",
            "recommendations":        [],
        }

    text_lower = text.lower()
    detected   = []
    adjustments = {}
    total_penalty = 0.0
    risk_score    = 0
    recommendations = []

    from config_loader import get_config_val
    severity_scores = get_config_val('risk_nlp.severity_scores', {
        "Low": 1, "Medium": 2, "High": 3, "Critical": 4
    })

    for cat_key, cat_def in RISK_CATEGORIES.items():
        matched_keywords = [kw for kw in cat_def["keywords"] if kw in text_lower]

        if matched_keywords:
            # More keyword matches = higher confidence
            match_count    = len(matched_keywords)
            confidence     = min(0.95, 0.50 + match_count * 0.15)
            severity       = cat_def["severity"]
            penalty_amount = cloud_annual * cat_def["penalty_pct"]

            detected.append({
                "category":        cat_key,
                "label":           cat_def["label"],
                "icon":            cat_def["icon"],
                "severity":        severity,
                "confidence":      round(confidence, 2),
                "matched_keywords": matched_keywords,
                "penalty_amount":  round(penalty_amount, 2),
                "prob_adjustment": cat_def["prob_adjustment"],
                "risk_field":      cat_def["risk_field"],
                "mitigation":      cat_def["mitigation"],
            })

            # Accumulate probability adjustments per risk field
            field = cat_def["risk_field"]
            adjustments[field] = adjustments.get(field, 0.0) + cat_def["prob_adjustment"]

            total_penalty += penalty_amount
            risk_score    += severity_scores.get(severity, 1)
            recommendations.append(cat_def["mitigation"])

    # Cap adjustments at 0.90 (leave room for slider override)
    for field in adjustments:
        adjustments[field] = min(0.90, round(adjustments[field], 2))

    # ── Risk level ────────────────────────────────────────────────────────
    if risk_score >= 10:
        risk_level = "Critical"
    elif risk_score >= 6:
        risk_level = "High"
    elif risk_score >= 3:
        risk_level = "Medium"
    elif risk_score >= 1:
        risk_level = "Low"
    else:
        risk_level = "None"

    # ── Narrative ─────────────────────────────────────────────────────────
    if not detected:
        narrative = (
            "✅ No specific risk concerns detected in your description. "
            "Consider reviewing common migration risks: downtime, compliance, "
            "skill gaps, and vendor lock-in."
        )
    else:
        cat_labels = [d["label"] for d in detected]
        icon = {"None": "✅", "Low": "ℹ️", "Medium": "⚠️",
                "High": "🔴", "Critical": "⛔"}[risk_level]

        narrative = (
            f"{icon} {risk_level} Risk — {len(detected)} concern(s) identified "
            f"from your description:\n"
        )
        for d in detected:
            narrative += (
                f"\n  {d['icon']} **{d['label']}** ({d['severity']}): "
                f"Matched on: {', '.join(d['matched_keywords'])}. "
                f"Suggested probability boost: +{d['prob_adjustment']:.0%}."
            )

        if total_penalty > 0 and cloud_annual > 0:
            narrative += (
                f"\n\n  📊 Total estimated financial penalty: "
                f"${total_penalty:,.0f}/yr added to risk-adjusted cloud cost."
            )

    return {
        "detected_categories":    detected,
        "risk_score":             risk_score,
        "risk_level":             risk_level,
        "probability_adjustments": adjustments,
        "total_penalty":          round(total_penalty, 2),
        "narrative":              narrative,
        "recommendations":        recommendations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== NLP Fear Classifier Demo ===\n")

    sample_text = (
        "I'm worried about data breaches and our team has no Kubernetes "
        "experience. The budget is tight and we can't afford delays. "
        "We also have strict GDPR compliance requirements."
    )

    result = analyze_migration_concerns(sample_text, cloud_annual=200_000)

    print(f"Risk Level: {result['risk_level']} (score: {result['risk_score']})")
    print(f"Categories: {len(result['detected_categories'])}")
    print(f"Total Penalty: ${result['total_penalty']:,.0f}/yr")
    print(f"\nNarrative:\n{result['narrative']}")
    print(f"\nProbability Adjustments: {result['probability_adjustments']}")
