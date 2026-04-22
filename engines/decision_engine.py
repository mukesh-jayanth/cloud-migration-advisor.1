"""
decision_engine.py
Financial Decision Engine — Post-Strategy Migration Economics

This engine:
  1. Compares on-prem vs cloud base costs.
  2. After a strategy is determined, computes the *real* Year-1 cost
     including strategy-dependent labor multipliers and double-run windows.
  3. Calculates the ROI timeline — the exact month where cumulative cloud
     savings finally exceed the migration investment (break-even point).
  4. Performs Fragility Analysis — flags plans where a 10% price increase
     or 2-month migration delay would negate all savings.
"""

from engines.cloud_cost_engine import PRICING_MODELS
from engines.cost_engine import (
    calculate_migration_economics,
    MIGRATION_ECONOMICS,
)
import math

# -----------------------------------------------------------------------
# Confidence Thresholds
# Based on percentage savings vs on-prem (BEFORE migration costs)
# -----------------------------------------------------------------------
CONFIDENCE_THRESHOLDS = {
    "High":   20.0,   # Cloud is 20%+ cheaper → clear win
    "Medium":  5.0,   # Cloud is 5–20% cheaper → likely worth it
    "Low":     0.0,   # Cloud is 0–5% cheaper  → marginal, evaluate carefully
}

# Fragility thresholds
PRICE_SHOCK_PCT       = 0.10   # 10% cloud price increase scenario
DELAY_SHOCK_MONTHS    =  2     # 2-month migration delay


def _get_confidence(savings_pct: float) -> str:
    if savings_pct < 0:
        return "Stay On-Prem"
    elif savings_pct >= CONFIDENCE_THRESHOLDS["High"]:
        return "High"
    elif savings_pct >= CONFIDENCE_THRESHOLDS["Medium"]:
        return "Medium"
    else:
        return "Low"


def _get_strategy_key(strategy_name: str) -> str:
    """Map full strategy names to MIGRATION_ECONOMICS keys."""
    mapping = {
        "Lift-and-Shift":       "Rehost",
        "Hybrid Migration":     "Hybrid",
        "Cloud-Native Migration": "Refactor",
        "Retain On-Premise":    "Rehost",   # treat retain similarly to rehost for costing
    }
    return mapping.get(strategy_name, "Rehost")


# -----------------------------------------------------------------------
# ROI Timeline Calculator
# -----------------------------------------------------------------------

def calculate_roi_timeline(
    onprem_annual:      float,
    cloud_annual:       float,
    migration_premium:  float,
    projection_years:   int = 5,
) -> dict:
    """
    Compute month-by-month cumulative savings and find the break-even point.

    Args:
        onprem_annual     : Annual on-prem cost (used as savings reference)
        cloud_annual      : Annual cloud cost after migration
        migration_premium : Total upfront migration cost (labor + double-run)
        projection_years  : How many years to project

    Returns:
        {
            "break_even_month"     : int | None,
            "cumulative_by_year"   : list[float],   # one value per year
            "monthly_series"       : list[float],   # month 1..N cumulative savings
            "is_viable"            : bool,
            "fragility_10pct_price": str,            # impact of 10% cloud price rise
            "fragility_2mo_delay"  : str,            # impact of 2-month delay
        }
    """
    annual_saving   = onprem_annual - cloud_annual
    monthly_saving  = annual_saving / 12.0

    total_months    = projection_years * 12
    monthly_series  = []
    break_even_month = None

    for m in range(1, total_months + 1):
        net = (monthly_saving * m) - migration_premium
        monthly_series.append(round(net, 2))
        if break_even_month is None and net >= 0:
            break_even_month = m

    cumulative_by_year = [
        round((annual_saving * y) - migration_premium, 2)
        for y in range(1, projection_years + 1)
    ]

    is_viable = break_even_month is not None

    # ── Fragility 1: 10% cloud price increase ──────────────────────────────
    shocked_cloud_annual  = cloud_annual * (1 + PRICE_SHOCK_PCT)
    shocked_annual_saving = onprem_annual - shocked_cloud_annual
    if shocked_annual_saving > 0:
        shocked_bem = math.ceil((migration_premium / shocked_annual_saving) * 12) \
            if shocked_annual_saving > 0 else None
        if break_even_month and shocked_bem:
            delay_delta = shocked_bem - break_even_month
            frag_price = (
                f"Break-even shifts from month {break_even_month} to "
                f"month {shocked_bem} (+{delay_delta} months). "
                + ("⚠️ HIGH FRAGILITY" if delay_delta > 12 else "Manageable impact.")
            )
        elif not shocked_annual_saving > 0:
            frag_price = "⛔ CRITICAL: A 10% price increase eliminates all savings — plan becomes unviable."
        else:
            frag_price = "10% price increase: plan already non-viable at base rates."
    else:
        frag_price = "⛔ CRITICAL: A 10% price increase eliminates all savings — plan becomes unviable."

    # ── Fragility 2: 2-month migration delay ───────────────────────────────
    extra_double_run = onprem_annual * (DELAY_SHOCK_MONTHS / 12.0)
    delayed_premium  = migration_premium + extra_double_run
    if annual_saving > 0:
        delayed_bem = math.ceil((delayed_premium / annual_saving) * 12)
        delay_delta = delayed_bem - (break_even_month or 0)
        frag_delay  = (
            f"2-month delay adds {_fmt_currency(extra_double_run)} to migration cost. "
            f"Break-even shifts to month {delayed_bem} "
            + ("⚠️ HIGH FRAGILITY — review contingency budget." if delay_delta > 6 else "(Low impact).")
        )
    else:
        frag_delay = "⛔ Plan is already non-viable; any delay compounds losses."

    return {
        "break_even_month":       break_even_month,
        "cumulative_by_year":     cumulative_by_year,
        "monthly_series":         monthly_series,
        "is_viable":              is_viable,
        "fragility_10pct_price":  frag_price,
        "fragility_2mo_delay":    frag_delay,
        "annual_saving":          round(annual_saving, 2),
        "migration_premium":      round(migration_premium, 2),
    }


def _fmt_currency(usd_val: float) -> str:
    """
    Format a USD value as an INR string for embedding in narrative text.

    ⚠️  IMPORTANT: This function always expects a value denominated in USD.
    It multiplies by 84 (USD→INR) internally. Do NOT pass INR values here —
    doing so will display amounts that are 84× too large.

    The strings produced by this function are embedded directly in dict keys
    like ``fragility_10pct_price`` and ``fragility_2mo_delay``, which are
    rendered in the Streamlit UI via ``st.info()`` without further formatting.
    app.py must NOT run these strings through its own ``inr()`` helper.
    """
    val = usd_val * 84.0
    if abs(val) >= 10_000_000:
        return f"₹{val/10_000_000:.2f}Cr"
    elif abs(val) >= 100_000:
        return f"₹{val/100_000:.1f}L"
    elif abs(val) >= 1_000:
        return f"₹{val/1_000:.0f}K"
    return f"₹{val:.0f}"


# -----------------------------------------------------------------------
# Decision Engine
# -----------------------------------------------------------------------

def recommend_strategy(
    onprem_cost:      float,
    cloud_costs:      dict,
    pricing_model:    str   = "on_demand",
    strategy_name:    str   = None,
    servers:          int   = 1,
    has_skilled_team: bool  = False,
    has_cicd:         bool  = False,
) -> dict:
    """
    Compare on-prem vs cloud costs and recommend a migration strategy.
    When strategy_name is provided, also calculates Year-1 migration
    economics and the full ROI timeline.

    Args:
        onprem_cost      : Annual on-premises infrastructure cost
        cloud_costs      : Output from calculate_provider_costs()
        pricing_model    : Which model to compare against on-prem
        strategy_name    : Optional — rule-engine strategy (used for labor calc)
        servers          : Number of servers (used for labor calc)
        has_skilled_team : Reduces labor multiplier by 30%
        has_cicd         : Reduces labor multiplier by 20%

    Returns:
        dict of provider → { recommendation, reason, confidence, ... }
        Plus "_summary" and "_migration_economics" top-level keys.
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
        cloud_cost  = cost_data.get(pricing_model, cost_data.get("selected", 0))
        difference  = onprem_cost - cloud_cost      # Positive = cloud cheaper
        savings_pct = (difference / onprem_cost) * 100

        if difference > 0:
            recommendation = "Migrate to Cloud"
            reason = (
                f"{provider} saves ₹{difference * 84:,.0f}/yr "
                f"({savings_pct:.1f}% cheaper than on-prem)"
            )
        elif difference < 0:
            recommendation = "Stay On-Prem"
            reason = (
                f"On-prem is ₹{abs(difference) * 84:,.0f}/yr cheaper than {provider} "
                f"({abs(savings_pct):.1f}% more expensive in cloud)"
            )
        else:
            recommendation = "Either option"
            reason = "Costs are equal — consider non-cost factors (SLA, support, latency)"

        confidence = _get_confidence(savings_pct)

        results[provider] = {
            "recommendation": recommendation,
            "reason":         reason,
            "confidence":     confidence,
            "cloud_cost":     round(cloud_cost, 2),
            "onprem_cost":    round(onprem_cost, 2),
            "savings":        round(difference, 2),
            "savings_pct":    round(savings_pct, 2),
            "all_pricing": {
                model: round(cost_data.get(model, 0), 2)
                for model in PRICING_MODELS
            }
        }

    # ── Top-level financial summary ──────────────────────────────────────
    results["_summary"] = _build_summary(results, onprem_cost)

    # ── Post-strategy migration economics (if strategy supplied) ──────────
    if strategy_name:
        strategy_key  = _get_strategy_key(strategy_name)
        best_provider = results["_summary"].get("best_cloud_option")

        if best_provider and best_provider in results:
            cloud_annual = results[best_provider]["cloud_cost"]

            econ = calculate_migration_economics(
                strategy_key     = strategy_key,
                servers          = servers,
                onprem_annual    = onprem_cost,
                cloud_annual     = cloud_annual,
                has_skilled_team = has_skilled_team,
                has_cicd         = has_cicd,
            )

            roi = calculate_roi_timeline(
                onprem_annual    = onprem_cost,
                cloud_annual     = cloud_annual,
                migration_premium= econ["migration_premium"],
            )

            results["_migration_economics"] = {**econ, **roi}
        else:
            results["_migration_economics"] = None
    else:
        results["_migration_economics"] = None

    return results


def _build_summary(results: dict, onprem_cost: float) -> dict:
    """Generate a top-level summary across all provider recommendations."""
    migrate_providers = {
        p: r for p, r in results.items()
        if p != "_summary" and r["recommendation"] == "Migrate to Cloud"
    }

    if not migrate_providers:
        return {
            "overall_recommendation": "Stay On-Prem",
            "reason":                 "No cloud provider offers cost savings over on-premises.",
            "best_cloud_option":      None
        }

    # Best cloud = highest savings
    best = max(migrate_providers, key=lambda p: migrate_providers[p]["savings"])

    return {
        "overall_recommendation": "Migrate to Cloud",
        "best_cloud_option":      best,
        "best_savings":           migrate_providers[best]["savings"],
        "best_savings_pct":       migrate_providers[best]["savings_pct"],
        "confidence":             migrate_providers[best]["confidence"],
        "reason":                 migrate_providers[best]["reason"],
    }