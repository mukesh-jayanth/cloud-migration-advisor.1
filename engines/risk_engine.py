"""
risk_engine.py
Phase 2 — Risk-Weighted Analysis

Calculates risk-adjusted Total Cost of Ownership (TCO) for cloud migration
by quantifying financial impact of downtime, compliance, and skill-gap risks.
"""


def calculate_risk_adjustment(
    downtime_risk: float,
    downtime_cost: float,
    compliance_risk: float,
    compliance_penalty: float,
    skill_risk: float,
    training_cost: float
) -> dict:
    """
    Calculate the expected financial impact of migration risks.

    Each risk is expressed as a probability (0.0 – 1.0) multiplied by
    its associated cost to produce an expected monetary value.

    Args:
        downtime_risk       (float): Probability of significant downtime     [0.0 – 1.0]
        downtime_cost       (float): Financial cost if downtime occurs        [USD, >= 0]
        compliance_risk     (float): Probability of a compliance violation    [0.0 – 1.0]
        compliance_penalty  (float): Financial penalty if violation occurs    [USD, >= 0]
        skill_risk          (float): Probability of skill-gap issues          [0.0 – 1.0]
        training_cost       (float): Cost to close the skill gap              [USD, >= 0]

    Returns:
        dict: {
            "total_risk_cost"  (float): Sum of all expected risk costs,
            "downtime_cost"    (float): Expected cost from downtime risk,
            "compliance_cost"  (float): Expected cost from compliance risk,
            "skill_cost"       (float): Expected cost from skill-gap risk
        }

    Raises:
        TypeError:  If any argument is not a numeric type.
        ValueError: If a risk probability is outside [0.0, 1.0],
                    or if any cost value is negative.

    Example:
        >>> result = calculate_risk_adjustment(
        ...     downtime_risk=0.10,    downtime_cost=50000,
        ...     compliance_risk=0.05,  compliance_penalty=100000,
        ...     skill_risk=0.20,       training_cost=15000
        ... )
        >>> result["total_risk_cost"]
        13000.0
    """
    args = {
        "downtime_risk": downtime_risk,
        "downtime_cost": downtime_cost,
        "compliance_risk": compliance_risk,
        "compliance_penalty": compliance_penalty,
        "skill_risk": skill_risk,
        "training_cost": training_cost,
    }

    # --- Type validation ---
    for name, value in args.items():
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"'{name}' must be a numeric value (int or float), "
                f"got {type(value).__name__!r}."
            )

    # --- Risk probability range validation ---
    for name in ("downtime_risk", "compliance_risk", "skill_risk"):
        value = args[name]
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"'{name}' must be a probability between 0.0 and 1.0, got {value}."
            )

    # --- Cost non-negativity validation ---
    for name in ("downtime_cost", "compliance_penalty", "training_cost"):
        value = args[name]
        if value < 0:
            raise ValueError(
                f"'{name}' must be a non-negative value, got {value}."
            )

    # --- Core calculation ---
    downtime_risk_cost    = downtime_risk    * downtime_cost
    compliance_risk_cost  = compliance_risk  * compliance_penalty
    skill_risk_cost       = skill_risk       * training_cost

    total_risk_cost = (
        downtime_risk_cost +
        compliance_risk_cost +
        skill_risk_cost
    )

    return {
        "total_risk_cost":  total_risk_cost,
        "downtime_cost":    downtime_risk_cost,
        "compliance_cost":  compliance_risk_cost,
        "skill_cost":       skill_risk_cost
    }


def risk_adjusted_tco(
    base_cloud_cost: float,
    risk_adjustment: dict
) -> float:
    """
    Compute the risk-adjusted Total Cost of Ownership (TCO).

    Adds the total expected risk cost to the base cloud cost to produce
    a more realistic migration cost estimate.

    Args:
        base_cloud_cost  (float): Raw estimated cloud cost             [USD, >= 0]
        risk_adjustment  (dict):  Output of calculate_risk_adjustment()

    Returns:
        float: Risk-adjusted cloud cost (base + total risk cost)       [USD]

    Raises:
        TypeError:  If base_cloud_cost is not numeric, or risk_adjustment
                    is not a dict.
        ValueError: If base_cloud_cost is negative, or risk_adjustment
                    does not contain the key 'total_risk_cost'.
        ValueError: If 'total_risk_cost' is negative.

    Example:
        >>> risk_adjusted_tco(400000, {"total_risk_cost": 8500, ...})
        408500.0
    """
    # --- Type validation ---
    if not isinstance(base_cloud_cost, (int, float)):
        raise TypeError(
            f"'base_cloud_cost' must be a numeric value, "
            f"got {type(base_cloud_cost).__name__!r}."
        )
    if not isinstance(risk_adjustment, dict):
        raise TypeError(
            f"'risk_adjustment' must be a dict (output of calculate_risk_adjustment()), "
            f"got {type(risk_adjustment).__name__!r}."
        )

    # --- Value validation ---
    if base_cloud_cost < 0:
        raise ValueError(
            f"'base_cloud_cost' must be non-negative, got {base_cloud_cost}."
        )
    if "total_risk_cost" not in risk_adjustment:
        raise ValueError(
            "'risk_adjustment' dict must contain the key 'total_risk_cost'. "
            "Pass the direct output of calculate_risk_adjustment()."
        )
    if risk_adjustment["total_risk_cost"] < 0:
        raise ValueError(
            f"'total_risk_cost' must be non-negative, "
            f"got {risk_adjustment['total_risk_cost']}."
        )

    return float(base_cloud_cost + risk_adjustment["total_risk_cost"])


# ---------------------------------------------------------------------------
# Quick smoke-test  (python risk_engine.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    risk = calculate_risk_adjustment(
        downtime_risk=0.10,    downtime_cost=50_000,
        compliance_risk=0.05,  compliance_penalty=100_000,
        skill_risk=0.20,       training_cost=15_000,
    )

    adjusted = risk_adjusted_tco(400_000, risk)

    print("=== Phase 2 — Risk Engine Output ===")
    print(f"  Downtime Cost   : ${risk['downtime_cost']:>10,.2f}")
    print(f"  Compliance Cost : ${risk['compliance_cost']:>10,.2f}")
    print(f"  Skill Cost      : ${risk['skill_cost']:>10,.2f}")
    print(f"  Total Risk Cost : ${risk['total_risk_cost']:>10,.2f}")
    print(f"  --------------------------------")
    print(f"  Base Cloud Cost : ${'400,000.00':>10}")
    print(f"  Adjusted TCO    : ${adjusted:>10,.2f}")