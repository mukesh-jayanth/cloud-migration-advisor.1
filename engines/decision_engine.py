from engines.cloud_cost_engine import PRICING_MODELS

# -------------------------------
# Confidence Thresholds
# Based on percentage savings vs on-prem
# -------------------------------
CONFIDENCE_THRESHOLDS = {
    "High":   20.0,   # Cloud is 20%+ cheaper → clear win
    "Medium":  5.0,   # Cloud is 5–20% cheaper → likely worth it
    "Low":     0.0,   # Cloud is 0–5% cheaper  → marginal, evaluate carefully
}


def _get_confidence(savings_pct: float) -> str:
    """
    Convert a savings percentage into a human-readable confidence tier.

    Args:
        savings_pct: Positive = cloud cheaper, Negative = on-prem cheaper

    Returns:
        'High', 'Medium', 'Low', or 'Stay On-Prem'
    """
    if savings_pct < 0:
        return "Stay On-Prem"
    elif savings_pct >= CONFIDENCE_THRESHOLDS["High"]:
        return "High"
    elif savings_pct >= CONFIDENCE_THRESHOLDS["Medium"]:
        return "Medium"
    else:
        return "Low"


def _get_strategy(savings_pct: float) -> str:
    """
    Map savings percentage to a migration strategy tier.

    >20% savings  → Full Migration     (clear cost win, commit fully)
    5–20% savings → Hybrid Migration   (migrate non-critical workloads first)
    0–5%  savings → Selective Migration (only migrate where cloud adds value beyond cost)
    ≤0%   savings → Stay On-Prem       (no financial case for migration)
    """
    if savings_pct > 20:
        return "Full Migration"
    elif savings_pct > 5:
        return "Hybrid Migration"
    elif savings_pct > 0:
        return "Selective Migration"
    else:
        return "Stay On-Prem"


# -------------------------------
# Decision Engine
# -------------------------------
def recommend_strategy(
    onprem_cost: float,
    cloud_costs: dict,
    pricing_model: str = "on_demand"
) -> dict:
    """
    Compare on-prem vs cloud costs and recommend a migration strategy.

    Args:
        onprem_cost   : Annual on-premises infrastructure cost (USD)
        cloud_costs   : Output from calculate_provider_costs()
                        Each provider has keys: on_demand, reserved_1yr,
                        reserved_3yr, selected, vs_best, is_best
        pricing_model : Which model to compare against on-prem

    Returns:
        dict of provider → {
            recommendation, reason, confidence,
            cloud_cost, savings, savings_pct
        }

    Raises:
        ValueError: If onprem_cost is invalid
    """
    if onprem_cost <= 0:
        raise ValueError(f"onprem_cost must be > 0, got {onprem_cost}")

    if pricing_model not in PRICING_MODELS:
        raise ValueError(
            f"Invalid pricing_model '{pricing_model}'. "
            f"Choose from: {list(PRICING_MODELS.keys())}"
        )

    results = {}

    for provider, cost_data in cloud_costs.items():
        cloud_cost = cost_data[pricing_model]
        difference = onprem_cost - cloud_cost           # Positive = cloud cheaper
        savings_pct = (difference / onprem_cost) * 100

        # Decision
        if difference > 0:
            recommendation = "Migrate to Cloud"
            reason = (
                f"{provider} saves ${difference:,.2f}/yr "
                f"({savings_pct:.1f}% cheaper than on-prem)"
            )
        elif difference < 0:
            recommendation = "Stay On-Prem"
            reason = (
                f"On-prem is ${abs(difference):,.2f}/yr cheaper than {provider} "
                f"({abs(savings_pct):.1f}% more expensive in cloud)"
            )
        else:
            recommendation = "Either option"
            reason = "Costs are equal — consider non-cost factors (SLA, support, latency)"

        confidence = _get_confidence(savings_pct)
        strategy   = _get_strategy(savings_pct)

        # Build per-provider result
        results[provider] = {
            "recommendation": recommendation,
            "strategy": strategy,
            "reason": reason,
            "confidence": confidence,
            "cloud_cost": round(cloud_cost, 2),
            "onprem_cost": round(onprem_cost, 2),
            "savings": round(difference, 2),
            "savings_pct": round(savings_pct, 2),

            # All pricing model costs for reference — useful for UI switcher
            "all_pricing": {
                model: round(cost_data[model], 2)
                for model in PRICING_MODELS
            }
        }

    # Add a top-level summary — single best overall recommendation
    results["_summary"] = _build_summary(results, onprem_cost)

    return results


def _build_summary(results: dict, onprem_cost: float) -> dict:
    """
    Generate a top-level summary across all provider recommendations.
    """
    migrate_providers = {
        p: r for p, r in results.items()
        if p != "_summary" and r["recommendation"] == "Migrate to Cloud"
    }

    if not migrate_providers:
        return {
            "overall_recommendation": "Stay On-Prem",
            "reason": "No cloud provider offers cost savings over on-premises.",
            "best_cloud_option": None
        }

    # Best cloud = highest savings
    best = max(migrate_providers, key=lambda p: migrate_providers[p]["savings"])

    return {
        "overall_recommendation": "Migrate to Cloud",
        "best_cloud_option": best,
        "strategy": migrate_providers[best]["strategy"],
        "best_savings": migrate_providers[best]["savings"],
        "best_savings_pct": migrate_providers[best]["savings_pct"],
        "confidence": migrate_providers[best]["confidence"],
        "reason": migrate_providers[best]["reason"],
    }