"""
rule_engine.py
Phase 3 — Rule-Based Recommendation Engine

Acts as an expert consultant layer on top of the cost/risk analysis,
recommending migration strategy, disaster recovery approach, and a
phased migration roadmap based on predefined business rules.

Input convention (aligned with Phase 2)
-----------------------------------------
All categorical inputs use consistent lowercase strings:
    "low" | "medium" | "high"

This matches the probability-based float inputs of risk_engine.py,
where "low" ~ 0.0–0.33, "medium" ~ 0.34–0.66, "high" ~ 0.67–1.0.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_LEVELS = {"low", "medium", "high"}

VALID_STRATEGIES = {
    "Lift-and-Shift",
    "Hybrid Migration",
    "Cloud-Native Migration",
}

# ---------------------------------------------------------------------------
# Rule Tables
# ---------------------------------------------------------------------------

# Each rule is a dict with:
#   "condition" : callable(compliance_level, downtime_tolerance, growth_rate) -> bool
#   "strategy"  : str — the strategy to return if condition is True
#
# Rules are evaluated top-to-bottom; the first match wins.
# The final rule must always be a guaranteed fallback (condition: lambda: True).

STRATEGY_RULES = [
    {
        # High compliance + low downtime tolerance → keep sensitive workloads on-prem
        "condition": lambda c, d, g: c == "high" and d == "low",
        "strategy": "Hybrid Migration",
    },
    {
        # High growth rate → needs scalable, cloud-native infrastructure
        "condition": lambda c, d, g: g == "high",
        "strategy": "Cloud-Native Migration",
    },
    {
        # Default fallback
        "condition": lambda c, d, g: True,
        "strategy": "Lift-and-Shift",
    },
]

# Each rule is a tuple of (level, dr_strategy).
# downtime_tolerance drives DR urgency — lower tolerance needs hotter standby.

DR_RULES = [
    ("low",    "Hot DR"),    # Near-zero downtime tolerance → always-on standby
    ("medium", "Warm DR"),   # Moderate tolerance → pre-provisioned standby
    ("high",   "Cold DR"),   # High tolerance → backup-based recovery
]

# ---------------------------------------------------------------------------
# Roadmaps
# ---------------------------------------------------------------------------

MIGRATION_ROADMAPS = {
    "Lift-and-Shift": [
        "Phase 1: Assess current infrastructure and map dependencies",
        "Phase 2: Replicate on-prem environment in the cloud (rehost)",
        "Phase 3: Validate performance and run parallel testing",
        "Phase 4: Cut over traffic and decommission on-prem workloads",
        "Phase 5: Post-migration monitoring and cost optimisation",
    ],
    "Hybrid Migration": [
        "Phase 1: Identify and classify sensitive vs scalable workloads",
        "Phase 2: Retain regulated and high-compliance systems on-premises",
        "Phase 3: Migrate scalable and non-sensitive services to cloud",
        "Phase 4: Establish secure connectivity between on-prem and cloud",
        "Phase 5: Unified monitoring, governance, and cost management",
    ],
    "Cloud-Native Migration": [
        "Phase 1: Containerize existing applications (Docker / Kubernetes)",
        "Phase 2: Decompose monoliths into microservices architecture",
        "Phase 3: Deploy to cloud with CI/CD pipelines",
        "Phase 4: Implement autoscaling and managed cloud services",
        "Phase 5: Continuous optimisation — cost, resilience, performance",
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_level(value: str, name: str) -> str:
    """
    Normalise and validate a categorical level input.

    Strips whitespace and lowercases the value, then checks it is one
    of the accepted levels: "low", "medium", "high".

    Args:
        value (str): The input value to validate.
        name  (str): The parameter name (used in error messages).

    Returns:
        str: Normalised lowercase value.

    Raises:
        TypeError:  If value is not a string.
        ValueError: If value is not "low", "medium", or "high".
    """
    if not isinstance(value, str):
        raise TypeError(
            f"'{name}' must be a string ('low', 'medium', or 'high'), "
            f"got {type(value).__name__!r}."
        )
    normalised = value.strip().lower()
    if normalised not in VALID_LEVELS:
        raise ValueError(
            f"'{name}' must be one of {sorted(VALID_LEVELS)}, "
            f"got {value!r}."
        )
    return normalised

# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def recommend_strategy(
    compliance_level: str,
    downtime_tolerance: str,
    growth_rate: str
) -> str:
    """
    Recommend a migration strategy based on business rules.

    Evaluates a prioritised rule table top-to-bottom and returns the
    strategy for the first matching rule.

    Args:
        compliance_level   (str): Regulatory/compliance requirement   ["low"|"medium"|"high"]
        downtime_tolerance (str): Acceptable downtime during migration ["low"|"medium"|"high"]
        growth_rate        (str): Expected business growth rate        ["low"|"medium"|"high"]

    Returns:
        str: One of "Lift-and-Shift", "Hybrid Migration",
             "Cloud-Native Migration".

    Raises:
        TypeError:   If any argument is not a string.
        ValueError:  If any argument is not "low", "medium", or "high".
        RuntimeError: If no rule matches (guards against rule table
                      misconfiguration).

    Example:
        >>> recommend_strategy("high", "low", "medium")
        'Hybrid Migration'

        >>> recommend_strategy("low", "medium", "high")
        'Cloud-Native Migration'

        >>> recommend_strategy("low", "high", "low")
        'Lift-and-Shift'
    """
    compliance_level   = _validate_level(compliance_level,   "compliance_level")
    downtime_tolerance = _validate_level(downtime_tolerance, "downtime_tolerance")
    growth_rate        = _validate_level(growth_rate,        "growth_rate")

    for rule in STRATEGY_RULES:
        if rule["condition"](compliance_level, downtime_tolerance, growth_rate):
            return rule["strategy"]

    # Guard — unreachable if STRATEGY_RULES has a True fallback
    raise RuntimeError(
        "No strategy rule matched. Ensure STRATEGY_RULES contains a "
        "guaranteed fallback condition (lambda c, d, g: True)."
    )


def recommend_dr(downtime_tolerance: str) -> str:
    """
    Recommend a Disaster Recovery (DR) strategy.

    Maps downtime tolerance to a DR tier:
        "low"    → Hot DR   (always-on standby, minimal RTO)
        "medium" → Warm DR  (pre-provisioned standby)
        "high"   → Cold DR  (backup-based recovery, higher RTO acceptable)

    Args:
        downtime_tolerance (str): Acceptable downtime level ["low"|"medium"|"high"]

    Returns:
        str: One of "Hot DR", "Warm DR", "Cold DR".

    Raises:
        TypeError:  If downtime_tolerance is not a string.
        ValueError: If downtime_tolerance is not "low", "medium", or "high".

    Example:
        >>> recommend_dr("low")
        'Hot DR'

        >>> recommend_dr("medium")
        'Warm DR'

        >>> recommend_dr("high")
        'Cold DR'
    """
    downtime_tolerance = _validate_level(downtime_tolerance, "downtime_tolerance")

    for level, dr_strategy in DR_RULES:
        if downtime_tolerance == level:
            return dr_strategy

    # Guard — unreachable after validation, but kept for safety
    raise RuntimeError(
        f"No DR rule matched for downtime_tolerance={downtime_tolerance!r}."
    )


def get_migration_roadmap(strategy: str) -> list:
    """
    Return the phased migration roadmap for a given strategy.

    Args:
        strategy (str): Migration strategy — must be one of the values
                        returned by recommend_strategy().

    Returns:
        list[str]: Ordered list of migration phases.

    Raises:
        TypeError:  If strategy is not a string.
        ValueError: If strategy is not a recognised migration strategy.

    Example:
        >>> get_migration_roadmap("Hybrid Migration")
        [
            'Phase 1: Identify and classify sensitive vs scalable workloads',
            'Phase 2: Retain regulated and high-compliance systems on-premises',
            ...
        ]
    """
    if not isinstance(strategy, str):
        raise TypeError(
            f"'strategy' must be a string, got {type(strategy).__name__!r}."
        )
    if strategy not in MIGRATION_ROADMAPS:
        raise ValueError(
            f"Unknown strategy {strategy!r}. "
            f"Valid options: {sorted(MIGRATION_ROADMAPS.keys())}."
        )

    return MIGRATION_ROADMAPS[strategy]


# ---------------------------------------------------------------------------
# Quick smoke-test  (python rule_engine.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        ("high",   "low",    "medium"),   # → Hybrid Migration
        ("low",    "medium", "high"),     # → Cloud-Native Migration
        ("low",    "high",   "low"),      # → Lift-and-Shift
    ]

    print("=== Phase 3 — Rule Engine Output ===\n")

    for compliance, downtime, growth in test_cases:
        strategy = recommend_strategy(compliance, downtime, growth)
        dr       = recommend_dr(downtime)
        roadmap  = get_migration_roadmap(strategy)

        print(f"  Inputs  → compliance={compliance!r:8}  downtime={downtime!r:8}  growth={growth!r}")
        print(f"  Strategy: {strategy}")
        print(f"  DR Plan : {dr}")
        print(f"  Roadmap :")
        for phase in roadmap:
            print(f"    - {phase}")
        print()