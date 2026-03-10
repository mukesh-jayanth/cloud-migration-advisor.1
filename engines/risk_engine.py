def calculate_risk_adjustment(
    downtime_risk,
    downtime_cost,
    compliance_risk,
    compliance_penalty,
    skill_risk,
    training_cost
):

    downtime_risk_cost = downtime_risk * downtime_cost
    compliance_risk_cost = compliance_risk * compliance_penalty
    skill_risk_cost = skill_risk * training_cost

    total_risk_cost = (
        downtime_risk_cost +
        compliance_risk_cost +
        skill_risk_cost
    )

    return {
        "total_risk_cost": total_risk_cost,
        "downtime_cost": downtime_risk_cost,
        "compliance_cost": compliance_risk_cost,
        "skill_cost": skill_risk_cost
    }


def risk_adjusted_tco(base_cloud_cost, risk_cost):

    adjusted_cost = base_cloud_cost + risk_cost

    return adjusted_cost