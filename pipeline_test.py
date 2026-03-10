from engines.cost_engine import calculate_onprem_tco
from engines.risk_engine import calculate_risk_adjustment, risk_adjusted_tco
from engines.decision_engine import recommend_strategy


# ----------------------------
# Phase 1: Cost Engine
# ----------------------------

result = calculate_onprem_tco(
    file_path="C:/Users/Mukesh Jayanth/Downloads/onprem_infrastructure_financials_updated.xlsx"
)

print("\nPHASE 1 OUTPUT")
print(result)

onprem_cost = result["tco_3yr"]


# Example cloud cost (you can adjust this later)
cloud_cost = 400000


# ----------------------------
# Phase 2: Risk Engine
# ----------------------------

risk_result = calculate_risk_adjustment(
    downtime_risk=0.2,
    downtime_cost=10000,
    compliance_risk=0.1,
    compliance_penalty=50000,
    skill_risk=0.3,
    training_cost=5000
)

risk_cost = risk_result["total_risk_cost"]

risk_adjusted_cloud_cost = risk_adjusted_tco(
    cloud_cost,
    risk_cost
)

print("\nPHASE 2 OUTPUT")
print("Risk Breakdown:", risk_result)
print("Risk Adjusted Cloud Cost:", risk_adjusted_cloud_cost)


# ----------------------------
# Phase 3: Decision Engine
# ----------------------------

cloud_costs = {
    "Cloud": risk_adjusted_cloud_cost
}

decision = recommend_strategy(onprem_cost, cloud_costs)

print("\nPHASE 3 OUTPUT")
print(decision)