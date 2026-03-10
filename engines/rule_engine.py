# rule_engine.py


# -------------------------
# Strategy Rules
# -------------------------

strategy_rules = [
    {
        "condition": lambda c, d, g: c == "High" and d < 2,
        "strategy": "Hybrid Migration"
    },
    {
        "condition": lambda c, d, g: g > 20,
        "strategy": "Cloud-Native Migration"
    },
    {
        "condition": lambda c, d, g: True,
        "strategy": "Lift-and-Shift"
    }
]


def recommend_strategy(compliance_level, downtime_tolerance, growth_rate):

    for rule in strategy_rules:
        if rule["condition"](compliance_level, downtime_tolerance, growth_rate):
            return rule["strategy"]


# -------------------------
# Disaster Recovery Rules
# -------------------------

def recommend_dr(downtime_tolerance):

    dr_rules = [
        (downtime_tolerance < 1, "Hot DR"),
        (downtime_tolerance < 4, "Warm DR"),
        (True, "Cold DR")
    ]

    for condition, result in dr_rules:
        if condition:
            return result


# -------------------------
# Migration Roadmaps
# -------------------------

migration_roadmaps = {

    "Lift-and-Shift": [
        "Phase 1: Infrastructure assessment",
        "Phase 2: Rehost workloads to cloud",
        "Phase 3: Optimize performance"
    ],

    "Hybrid Migration": [
        "Phase 1: Identify sensitive workloads",
        "Phase 2: Keep regulated systems on-prem",
        "Phase 3: Move scalable services to cloud"
    ],

    "Cloud-Native Migration": [
        "Phase 1: Containerize applications",
        "Phase 2: Deploy microservices architecture",
        "Phase 3: Implement autoscaling infrastructure"
    ]
}


def get_migration_roadmap(strategy):

    return migration_roadmaps.get(strategy, [])