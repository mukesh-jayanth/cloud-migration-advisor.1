"""
rule_engine.py
Phase 3 — Rule-Based Recommendation Engine + Technical Debt Checker

Acts as an expert consultant layer on top of the cost/risk analysis.
Two-stage processing:
  1. TechnicalDebtCheck — scans server data for hard blockers.
     If a legacy OS, stateful pattern, or hardcoded IP is detected,
     it force-overrides Cloud-Native to "Retain" or "Rehost" and
     returns a structured Friction Report explaining why.

  2. recommend_strategy — applies business rules, but respects the
     technical reality established by TechnicalDebtCheck.

"The Honest Advisor must be willing to say No."
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_LEVELS    = {"low", "medium", "high"}

VALID_STRATEGIES = {
    "Lift-and-Shift",
    "Hybrid Migration",
    "Cloud-Native Migration",
    "Retain On-Premise",
}

# ---------------------------------------------------------------------------
# Technical Debt Signatures
# ---------------------------------------------------------------------------

LEGACY_OS_PATTERNS = [
    "windows 2003", "windows 2008", "windows 2008 r2",
    "windows 2000", "windows nt",
    "rhel 5", "rhel 4", "centos 5", "centos 4",
    "ubuntu 14", "ubuntu 12", "ubuntu 10",
    "debian 7", "debian 6",
    "solaris",
]

STATEFUL_APP_PATTERNS = [
    "stateful", "session-based", "sticky session",
    "in-memory session", "local file storage",
    "nfs mount", "shared disk", "shared filesystem",
]

HARDCODED_IP_PATTERNS = [
    "hardcoded ip", "static ip dependency",
    "ip-based auth", "ip whitelist", "fixed ip",
    "hardcoded address",
]

# ---------------------------------------------------------------------------
# Rule Tables
# ---------------------------------------------------------------------------

STRATEGY_RULES = [
    {
        # High compliance + low downtime tolerance → keep sensitive workloads on-prem
        "condition": lambda c, d, g: c == "high" and d == "low",
        "strategy":  "Hybrid Migration",
    },
    {
        # High growth rate → needs scalable, cloud-native infrastructure
        # (but this can be overridden by TechnicalDebtCheck)
        "condition": lambda c, d, g: g == "high",
        "strategy":  "Cloud-Native Migration",
    },
    {
        # Default fallback
        "condition": lambda c, d, g: True,
        "strategy":  "Lift-and-Shift",
    },
]

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
    "Retain On-Premise": [
        "Phase 1: Document current state and identify modernisation debt",
        "Phase 2: Remediate blocking issues (OS upgrade, IP refactoring)",
        "Phase 3: Re-evaluate cloud readiness after remediation",
        "Phase 4: Pilot a limited cloud migration once blockers are resolved",
        "Phase 5: Full migration or hybrid after successful pilot",
    ],
}

# ---------------------------------------------------------------------------
# Technical Debt Severity → Strategy Override Map
# ---------------------------------------------------------------------------

DEBT_OVERRIDE_STRATEGY = {
    "Retain":  "Retain On-Premise",   # Hard blocker — cannot migrate at all
    "Rehost":  "Lift-and-Shift",      # Soft blocker — safe fallback is rehost only
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_level(value: str, name: str) -> str:
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


def _check_patterns(text: str, patterns: list[str]) -> list[str]:
    """Return which patterns from the list are found in text (case-insensitive)."""
    text_lower = text.lower()
    return [p for p in patterns if p in text_lower]


# ---------------------------------------------------------------------------
# TechnicalDebtCheck
# ---------------------------------------------------------------------------

def check_technical_debt(server_info: dict) -> dict:
    """
    Scan server metadata for migration blockers and return a structured
    Friction Report.

    Args:
        server_info : dict with optional string fields:
            - "os"           : Operating system name/version string
            - "app_pattern"  : Application architecture description
            - "network_config": Network configuration notes

    Returns:
        {
            "has_debt"        : bool,
            "severity"        : "none" | "soft" | "hard",
            "override"        : None | "Retain" | "Rehost",
            "override_strategy": None | "Retain On-Premise" | "Lift-and-Shift",
            "blockers"        : list[str],    # human-readable issues found
            "friction_report" : str,          # advisory narrative
        }

    Severity guide:
        hard → Cloud-Native is impossible; must Retain On-Premise.
               Triggers when: legacy OS ≤ 2008 OR hardcoded IP dependency.
        soft → Cloud-Native is high-risk; safe path is Rehost (Lift-and-Shift).
               Triggers when: stateful app patterns detected without hard flags.
        none → No detected blockers; proceed with business-driven strategy.
    """
    os_str      = str(server_info.get("os",             "")).lower()
    app_str     = str(server_info.get("app_pattern",    "")).lower()
    net_str     = str(server_info.get("network_config", "")).lower()

    blockers = []

    # ── Hard blockers ────────────────────────────────────────────────────────
    legacy_hits = _check_patterns(os_str, LEGACY_OS_PATTERNS)
    if legacy_hits:
        blockers.append(
            f"Legacy OS detected: '{', '.join(legacy_hits)}'. "
            "Cloud vendor support for this OS is either end-of-life or requires "
            "expensive custom licensing. Cloud-Native is not viable."
        )

    ip_hits = _check_patterns(net_str + " " + app_str, HARDCODED_IP_PATTERNS)
    if ip_hits:
        blockers.append(
            f"Hardcoded IP dependencies found: '{', '.join(ip_hits)}'. "
            "Cloud environments use dynamic IPs; these must be refactored "
            "before any cloud deployment is safe."
        )

    has_hard_blocker = bool(legacy_hits or ip_hits)

    # ── Soft blockers ────────────────────────────────────────────────────────
    stateful_hits = _check_patterns(app_str + " " + os_str, STATEFUL_APP_PATTERNS)
    if stateful_hits:
        blockers.append(
            f"Stateful application pattern detected: '{', '.join(stateful_hits)}'. "
            "Stateful apps require persistent storage mapping and session-affinity "
            "configuration in the cloud. Cloud-Native refactoring is high-risk "
            "without significant re-architecture effort."
        )

    has_soft_blocker = bool(stateful_hits)

    # ── Determine severity and override ─────────────────────────────────────
    if has_hard_blocker:
        severity          = "hard"
        override          = "Retain"
        override_strategy = DEBT_OVERRIDE_STRATEGY["Retain"]
    elif has_soft_blocker:
        severity          = "soft"
        override          = "Rehost"
        override_strategy = DEBT_OVERRIDE_STRATEGY["Rehost"]
    else:
        severity          = "none"
        override          = None
        override_strategy = None

    # ── Friction narrative ────────────────────────────────────────────────────
    if severity == "hard":
        narrative = (
            "⛔ HARD BLOCK: This infrastructure has critical compatibility issues "
            "that prevent viable cloud migration at this time. Attempting Cloud-Native "
            f"migration would likely result in project failure. Specific issues: "
            + " | ".join(blockers) +
            " Recommended action: Remediate blockers first, then re-evaluate."
        )
    elif severity == "soft":
        narrative = (
            "⚠️ SOFT BLOCK: Stateful architecture patterns detected. A Cloud-Native "
            "strategy carries significant risk of cost overruns and timeline slippage. "
            "The safest path is Lift-and-Shift (Rehost) first, then incrementally "
            f"modernise. Issues: " + " | ".join(blockers)
        )
    else:
        narrative = "✅ No technical debt blockers detected. Proceed with business-driven strategy."

    return {
        "has_debt":          severity != "none",
        "severity":          severity,
        "override":          override,
        "override_strategy": override_strategy,
        "blockers":          blockers,
        "friction_report":   narrative,
    }


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def recommend_strategy(
    compliance_level:   str,
    downtime_tolerance: str,
    growth_rate:        str,
    server_info:        dict = None,
) -> dict:
    """
    Recommend a migration strategy, respecting both business rules and
    technical reality established by TechnicalDebtCheck.

    Args:
        compliance_level   : "low" | "medium" | "high"
        downtime_tolerance : "low" | "medium" | "high"
        growth_rate        : "low" | "medium" | "high"
        server_info        : Optional dict for TechnicalDebtCheck.
                             Keys: "os", "app_pattern", "network_config"

    Returns:
        {
            "strategy"      : str,
            "overridden"    : bool,
            "debt_check"    : dict | None,
            "original_strategy": str | None,  # what business rules said before override
        }
    """
    compliance_level   = _validate_level(compliance_level,   "compliance_level")
    downtime_tolerance = _validate_level(downtime_tolerance, "downtime_tolerance")
    growth_rate        = _validate_level(growth_rate,        "growth_rate")

    # Step 1: Apply business rules
    business_strategy = None
    for rule in STRATEGY_RULES:
        if rule["condition"](compliance_level, downtime_tolerance, growth_rate):
            business_strategy = rule["strategy"]
            break

    if business_strategy is None:
        raise RuntimeError(
            "No strategy rule matched. Ensure STRATEGY_RULES contains a "
            "guaranteed fallback condition (lambda c, d, g: True)."
        )

    # Step 2: Technical Debt Check (optional)
    debt_check     = None
    final_strategy = business_strategy
    overridden     = False

    if server_info:
        debt_check = check_technical_debt(server_info)

        if debt_check["has_debt"] and debt_check["override_strategy"]:
            # Only override if the debt severity forces a more conservative path
            override_target = debt_check["override_strategy"]

            strategy_conservatism = {
                "Retain On-Premise":    0,
                "Lift-and-Shift":       1,
                "Hybrid Migration":     2,
                "Cloud-Native Migration": 3,
            }

            current_level  = strategy_conservatism.get(business_strategy, 3)
            override_level = strategy_conservatism.get(override_target, 0)

            if override_level < current_level:
                # Override is more conservative → apply it
                final_strategy = override_target
                overridden     = True

    return {
        "strategy":          final_strategy,
        "overridden":        overridden,
        "original_strategy": business_strategy if overridden else None,
        "debt_check":        debt_check,
    }


def recommend_dr(downtime_tolerance: str) -> str:
    """
    Recommend a Disaster Recovery (DR) strategy.

    Maps downtime tolerance to a DR tier:
        "low"    → Hot DR   (always-on standby, minimal RTO)
        "medium" → Warm DR  (pre-provisioned standby)
        "high"   → Cold DR  (backup-based recovery, higher RTO acceptable)
    """
    downtime_tolerance = _validate_level(downtime_tolerance, "downtime_tolerance")

    for level, dr_strategy in DR_RULES:
        if downtime_tolerance == level:
            return dr_strategy

    raise RuntimeError(
        f"No DR rule matched for downtime_tolerance={downtime_tolerance!r}."
    )


def get_migration_roadmap(strategy: str) -> list:
    """
    Return the phased migration roadmap for a given strategy.
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
    print("=== Phase 3 — Rule Engine: Technical Debt Override Demo ===\n")

    # Case 1: Clean infrastructure → Cloud-Native (high growth)
    r = recommend_strategy("low", "medium", "high", server_info=None)
    print(f"Clean infra, high growth  → {r['strategy']}  (overridden={r['overridden']})")

    # Case 2: Legacy Windows 2008 + high growth → should be forced to Retain
    r = recommend_strategy("low", "medium", "high", server_info={
        "os": "Windows 2008 R2",
        "app_pattern": "",
        "network_config": ""
    })
    print(
        f"Win 2008 + high growth    → {r['strategy']}  "
        f"(overridden={r['overridden']}, was {r['original_strategy']})"
    )
    if r["debt_check"]:
        print(f"  Friction: {r['debt_check']['friction_report'][:120]}...")

    # Case 3: Stateful app + high growth → Lift-and-Shift fallback
    r = recommend_strategy("low", "high", "high", server_info={
        "os": "Windows Server 2019",
        "app_pattern": "stateful, shared filesystem NFS mount",
        "network_config": ""
    })
    print(
        f"Stateful + high growth    → {r['strategy']}  "
        f"(overridden={r['overridden']}, was {r['original_strategy']})"
    )