import pandas as pd
import random

data = []

for _ in range(500):

    server_count = random.randint(5, 500)
    avg_cpu_util = random.randint(10, 90)
    storage_tb = random.uniform(1, 100)

    downtime_tolerance = random.uniform(0.5, 24)
    compliance_level = random.choice([1, 2, 3])   # 1 low, 2 medium, 3 high
    growth_rate = random.randint(0, 40)
    budget_sensitivity = random.choice([1, 2, 3]) # 1 tight, 2 medium, 3 flexible

    # Expert labeling logic
    if compliance_level == 3 and downtime_tolerance < 2:
        strategy = "Hybrid"

    elif growth_rate > 25:
        strategy = "Cloud-Native"

    else:
        strategy = "Lift-and-Shift"

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

df.to_csv("data/synthetic_data.csv", index=False)

print("Synthetic dataset created!")