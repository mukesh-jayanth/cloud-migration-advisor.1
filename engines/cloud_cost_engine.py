import math
import logging
from engines.instance_selector import find_best_instances, validate_inputs

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8760
SAFETY_BUFFER = 1.3

# -------------------------------
# Pricing Model Multipliers
# Reflects real cloud economics — reserved instances are cheaper
# Use this to compare on-demand vs committed-use pricing
# -------------------------------
PRICING_MODELS = {
    "on_demand":    1.00,   # Full hourly rate, no commitment
    "reserved_1yr": 0.65,   # ~35% discount for 1-year commitment
    "reserved_3yr": 0.45,   # ~55% discount for 3-year commitment
}


# -------------------------------
# Cloud Cost Engine
# -------------------------------
def calculate_yearly_cost(
    price_per_hour: float,
    servers: int,
    pricing_model: str = "on_demand"
) -> float:
    """
    Calculate annual cloud cost for a given instance.

    Args:
        price_per_hour : On-demand hourly rate from dataset
        servers        : Number of server instances
        pricing_model  : One of 'on_demand', 'reserved_1yr', 'reserved_3yr'

    Returns:
        Annual cost in USD
    """
    if pricing_model not in PRICING_MODELS:
        raise ValueError(
            f"Invalid pricing_model '{pricing_model}'. "
            f"Choose from: {list(PRICING_MODELS.keys())}"
        )

    multiplier = PRICING_MODELS[pricing_model]
    return price_per_hour * HOURS_PER_YEAR * servers * multiplier


def calculate_provider_costs(
    instances: dict,
    servers: int,
    pricing_model: str = "on_demand"
) -> dict:
    """
    Calculate annual costs per provider across all pricing models.

    Returns:
        dict of provider → {
            on_demand, reserved_1yr, reserved_3yr,
            selected (based on pricing_model arg)
        }
    """
    costs = {}

    for provider, data in instances.items():
        provider_costs = {}

        for model in PRICING_MODELS:
            provider_costs[model] = round(
                calculate_yearly_cost(data["price_per_hour"], servers, model),
                2
            )

        # Tag which model was selected for comparison
        provider_costs["selected"] = provider_costs[pricing_model]
        costs[provider] = provider_costs

    return costs


# -------------------------------
# Provider Comparison Engine
# -------------------------------
def choose_best_provider(costs: dict) -> tuple[str, dict]:
    """
    Select the provider with the lowest cost under the selected pricing model.

    Returns:
        (best_provider_name, full costs dict with savings vs others)
    """
    # Stable tie-breaking: sort by cost, then provider name alphabetically
    sorted_providers = sorted(
        costs.items(),
        key=lambda x: (x[1]["selected"], x[0])
    )
    best_provider = sorted_providers[0][0]
    best_cost = costs[best_provider]["selected"]

    # Annotate savings vs best for each provider
    annotated = {}
    for provider, data in costs.items():
        diff = data["selected"] - best_cost
        annotated[provider] = {
            **data,
            "vs_best": round(diff, 2),      # 0 for winner, positive = more expensive
            "is_best": provider == best_provider
        }

    return best_provider, annotated


# -------------------------------
# Infrastructure Right-Sizing Engine
# -------------------------------
def recommend_resources(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float
) -> tuple[int, int]:
    """
    Right-size infrastructure based on actual utilization + safety buffer.

    Formula:
        required = current × (utilization / 100) × SAFETY_BUFFER
        Then rounded up to nearest standard cloud size.

    Args:
        current_vcpu     : Current number of vCPUs
        current_ram      : Current RAM in GB
        cpu_utilization  : Actual CPU usage percentage (1–100)
        ram_utilization  : Actual RAM usage percentage (1–100)

    Returns:
        (recommended_vcpu, recommended_ram)
    """
    cpu_util = cpu_utilization / 100
    ram_util = ram_utilization / 100

    required_cpu = current_vcpu * cpu_util * SAFETY_BUFFER
    required_ram = current_ram * ram_util * SAFETY_BUFFER

    recommended_cpu = math.ceil(required_cpu)

    # Snap RAM to nearest standard cloud size
    standard_sizes = [1, 2, 4, 8, 16, 32, 64, 128]
    recommended_ram = min(
        standard_sizes,
        key=lambda x: abs(x - math.ceil(required_ram))
    )

    return recommended_cpu, recommended_ram


# -------------------------------
# Full Decision Pipeline
# -------------------------------
def run_cloud_analysis(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float,
    servers: int,
    pricing_model: str = "on_demand"
) -> dict:
    """
    End-to-end cloud analysis pipeline.

    Steps:
      1. Validate inputs
      2. Right-size infrastructure
      3. Select best instances per provider
      4. Calculate costs (all pricing models)
      5. Choose best provider

    Args:
        current_vcpu     : Existing server vCPU count
        current_ram      : Existing server RAM in GB
        cpu_utilization  : Measured CPU usage % (1–100)
        ram_utilization  : Measured RAM usage % (1–100)
        servers          : Number of servers to migrate
        pricing_model    : Pricing commitment level

    Returns:
        Full analysis result dict

    Raises:
        ValueError: On invalid inputs or no matching instances
    """

    # Step 1: Validate all inputs upfront
    validate_inputs(
        current_vcpu, current_ram,
        cpu_utilization, ram_utilization,
        servers
    )

    # Step 2: Right-size infrastructure
    vcpu, ram = recommend_resources(
        current_vcpu, current_ram,
        cpu_utilization, ram_utilization
    )

    # Step 3: Find best instances (raises ValueError if none found)
    instances, workload_type = find_best_instances(vcpu, ram)

    # Step 4: Calculate costs across all pricing models
    costs = calculate_provider_costs(instances, servers, pricing_model)

    # Step 5: Choose best provider + annotate savings
    best_provider, annotated_costs = choose_best_provider(costs)

    return {
        # Right-sizing results
        "original_vcpu": current_vcpu,
        "original_ram": current_ram,
        "recommended_vcpu": vcpu,
        "recommended_ram": ram,
        "cpu_reduction_pct": round((1 - vcpu / current_vcpu) * 100, 1),
        "ram_reduction_pct": round((1 - ram / current_ram) * 100, 1),

        # Workload profile
        "workload_type": workload_type,

        # Instance selections
        "instances": instances,

        # Cost breakdown
        "pricing_model": pricing_model,
        "costs": annotated_costs,

        # Final recommendation
        "best_provider": best_provider,
        "best_yearly_cost": annotated_costs[best_provider]["selected"],
        "best_monthly_cost": round(annotated_costs[best_provider]["selected"] / 12, 2),
    }