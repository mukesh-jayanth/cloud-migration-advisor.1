def recommend_strategy(onprem_cost, cloud_costs):

    results = {}

    for provider, cost in cloud_costs.items():

        difference = onprem_cost - cost

        if difference > 0:
            recommendation = "Migrate to Cloud"
            reason = f"{provider} is cheaper by ${difference:,.2f}"

        elif difference < 0:
            recommendation = "Stay On-Prem"
            reason = f"On-Prem is cheaper than {provider} by ${abs(difference):,.2f}"

        else:
            recommendation = "Either option"
            reason = "Costs are equal"

        confidence = min(abs(difference) / onprem_cost * 100, 100)

        results[provider] = {
            "recommendation": recommendation,
            "reason": reason,
            "confidence": round(confidence, 2),
            "cloud_cost": cost
        }

    return results