import pandas as pd
import random
import os

# ─────────────────────────────────────────────
#  Dataset Generation Engine
#  Phase 4 — Cloud Migration ML Model
#  Generates synthetic enterprise scenarios
#  with richer expert labeling logic
# ─────────────────────────────────────────────

random.seed(42)  # Reproducibility

data = []

for _ in range(2000):  # Increased from 500 → 2000 for a more stable model

    # ── Input Features ──────────────────────────────────────
    server_count       = random.randint(5, 500)
    avg_cpu_util       = random.randint(10, 90)
    storage_tb         = random.uniform(1, 100)
    downtime_tolerance = random.uniform(0.5, 24)
    compliance_level   = random.choice([1, 2, 3])   # 1=low, 2=medium, 3=high
    growth_rate        = random.randint(0, 40)
    budget_sensitivity = random.choice([1, 2, 3])   # 1=tight, 2=medium, 3=flexible

    # ── Expert Labeling Logic (Richer — 6 conditions) ───────
    #
    #  Priority order matters: conditions are evaluated top-down.
    #  The first matching condition wins.
    #
    #  Hybrid       → high compliance or mixed cloud need
    #  Cloud-Native → high growth, flexible budget, or agile profile
    #  Lift-and-Shift → large legacy estate, low utilisation, tight budget

    if compliance_level == 3 and downtime_tolerance < 2:
        # High compliance + very low downtime tolerance → careful Hybrid approach
        strategy = "Hybrid"

    elif compliance_level == 2 and downtime_tolerance < 3 and budget_sensitivity == 1:
        # Medium compliance, low downtime tolerance, tight budget → Hybrid compromise
        strategy = "Hybrid"

    elif growth_rate > 25 and budget_sensitivity >= 2:
        # High growth + enough budget → invest in Cloud-Native
        strategy = "Cloud-Native"

    elif compliance_level == 1 and growth_rate > 15 and budget_sensitivity == 3:
        # Low compliance, moderate growth, flexible budget → go Cloud-Native
        strategy = "Cloud-Native"

    elif server_count > 200 and avg_cpu_util < 40:
        # Large server estate, underutilised → simple Lift-and-Shift rehost
        strategy = "Lift-and-Shift"

    elif downtime_tolerance > 10 and server_count < 50 and budget_sensitivity == 1:
        # High downtime tolerance, small estate, tight budget → Lift-and-Shift
        strategy = "Lift-and-Shift"

    else:
        # Default: Hybrid — covers mixed or ambiguous enterprise profiles
        strategy = "Hybrid"

    data.append([
        server_count,
        avg_cpu_util,
        storage_tb,
        downtime_tolerance,
        compliance_level,
        growth_rate,
        budget_sensitivity,
        strategy
    ])

# ── Build DataFrame ──────────────────────────────────────────
df = pd.DataFrame(data, columns=[
    "server_count",
    "avg_cpu_util",
    "storage_tb",
    "downtime_tolerance",
    "compliance_level",
    "growth_rate",
    "budget_sensitivity",
    "strategy"
])

# ── Save ─────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
df.to_csv("data/synthetic_data.csv", index=False)

# ── Summary ──────────────────────────────────────────────────
print("=" * 45)
print("  Synthetic Dataset Created")
print("=" * 45)
print(f"  Total Records : {len(df)}")
print()
print("  Strategy Distribution:")
for strategy, count in df["strategy"].value_counts().items():
    pct = round(count / len(df) * 100, 1)
    print(f"    {strategy:<20} {count:>4} records  ({pct}%)")
print()
print("  Saved → data/synthetic_data.csv")
print("=" * 45)