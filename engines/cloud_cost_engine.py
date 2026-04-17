import math
import logging
from engines.instance_selector import find_best_instances, validate_inputs

logger = logging.getLogger(__name__)

from config_loader import get_config_val

HOURS_PER_YEAR = 8760

# -----------------------------------------------------------------------
# Dynamically loaded from config.yaml
# -----------------------------------------------------------------------
RIGHTSIZING_BUFFER       = get_config_val('cloud_cost.right_sizing_buffer', 1.20)
EGRESS_AND_IOPS_RATE     = get_config_val('cloud_cost.egress_and_iops_rate', 0.065)
MANAGED_SERVICES_PREMIUM = get_config_val('cloud_cost.managed_services_premium', 0.20)

PRICING_MODELS = get_config_val('cloud_cost.pricing_model_multipliers', {
    "on_demand":    1.00,
    "reserved_1yr": 0.65,
    "reserved_3yr": 0.45,
})

# -----------------------------------------------------------------------
# Cloud Cost Engine
# -----------------------------------------------------------------------
def calculate_yearly_cost(
    price_per_hour: float,
    servers: int,
    pricing_model: str = "on_demand",
    apply_managed_services: bool = True
) -> float:
    """
    Calculate annual cloud cost for a given instance, including realistic
    overhead coefficients (egress + managed-services premium).

    Args:
        price_per_hour         : On-demand hourly rate from dataset
        servers                : Number of server instances
        pricing_model          : One of 'on_demand', 'reserved_1yr', 'reserved_3yr'
        apply_managed_services : If True, adds 20% managed-services premium
                                 on top of base + egress. Use False for raw
                                 compute-only workloads.

    Returns:
        Annual cost (same currency as price_per_hour)
    """
    if pricing_model not in PRICING_MODELS:
        raise ValueError(
            f"Invalid pricing_model '{pricing_model}'. "
            f"Choose from: {list(PRICING_MODELS.keys())}"
        )

    multiplier   = PRICING_MODELS[pricing_model]
    base_cost    = price_per_hour * HOURS_PER_YEAR * servers * multiplier

    # Layer 1 — Connectivity & IOPS fee (egress + cross-AZ traffic)
    egress_cost  = base_cost * EGRESS_AND_IOPS_RATE

    # Layer 2 — Managed Services premium (RDS, ElastiCache, etc.)
    managed_cost = (base_cost + egress_cost) * MANAGED_SERVICES_PREMIUM if apply_managed_services else 0.0

    return base_cost + egress_cost + managed_cost


def calculate_provider_costs(
    instances: dict,
    servers: int,
    pricing_model: str = "on_demand",
    apply_managed_services: bool = True
) -> dict:
    """
    Calculate annual costs per provider across all pricing models.

    Returns:
        dict of provider → {
            on_demand, reserved_1yr, reserved_3yr,
            selected (based on pricing_model arg),
            egress_rate, managed_services_premium
        }
    """
    costs = {}

    for provider, data in instances.items():
        provider_costs = {}

        for model in PRICING_MODELS:
            provider_costs[model] = round(
                calculate_yearly_cost(data["price_per_hour"], servers, model, apply_managed_services),
                2
            )

        # Tag which model was selected for comparison
        provider_costs["selected"] = provider_costs[pricing_model]

        # Expose the overhead rates for transparency in the UI
        provider_costs["egress_rate"]             = EGRESS_AND_IOPS_RATE
        provider_costs["managed_services_premium"] = MANAGED_SERVICES_PREMIUM if apply_managed_services else 0.0

        costs[provider] = provider_costs

    return costs


# -----------------------------------------------------------------------
# Provider Comparison Engine
# -----------------------------------------------------------------------
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


# -----------------------------------------------------------------------
# Infrastructure Right-Sizing Engine
# -----------------------------------------------------------------------
def recommend_resources(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float
) -> tuple[int, int]:
    """
    Right-size infrastructure based on actual utilization + a tighter
    20% elasticity buffer (down from the old 30% safety buffer).

    Formula:
        required = current × (utilization / 100) × RIGHTSIZING_BUFFER
        Then rounded up to nearest standard cloud size.
    """
    cpu_util = cpu_utilization / 100
    ram_util = ram_utilization / 100

    required_cpu = current_vcpu * cpu_util * RIGHTSIZING_BUFFER
    required_ram = current_ram  * ram_util * RIGHTSIZING_BUFFER

    recommended_cpu = math.ceil(required_cpu)

    # Snap RAM to nearest standard cloud size
    standard_sizes  = [1, 2, 4, 8, 16, 32, 64, 128]
    recommended_ram = min(
        standard_sizes,
        key=lambda x: abs(x - math.ceil(required_ram))
    )

    return recommended_cpu, recommended_ram


# -----------------------------------------------------------------------
# Full Decision Pipeline
# -----------------------------------------------------------------------
def run_cloud_analysis(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float,
    servers: int,
    pricing_model: str = "on_demand",
    apply_managed_services: bool = True
) -> dict:
    """
    End-to-end cloud analysis pipeline.

    Steps:
      1. Validate inputs
      2. Right-size infrastructure (20% buffer)
      3. Select best instances per provider
      4. Calculate costs with egress + managed-service overhead
      5. Choose best provider

    Args:
        current_vcpu            : Existing server vCPU count
        current_ram             : Existing server RAM in GB
        cpu_utilization         : Measured CPU usage % (1–100)
        ram_utilization         : Measured RAM usage % (1–100)
        servers                 : Number of servers to migrate
        pricing_model           : Pricing commitment level
        apply_managed_services  : Whether to add 20% managed-services premium

    Returns:
        Full analysis result dict
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

    # Step 4: Calculate costs across all pricing models (with overhead)
    costs = calculate_provider_costs(instances, servers, pricing_model, apply_managed_services)

    # Step 5: Choose best provider + annotate savings
    best_provider, annotated_costs = choose_best_provider(costs)

    return {
        # Right-sizing results
        "original_vcpu": current_vcpu,
        "original_ram":  current_ram,
        "recommended_vcpu": vcpu,
        "recommended_ram":  ram,
        "cpu_reduction_pct": round((1 - vcpu / current_vcpu) * 100, 1),
        "ram_reduction_pct": round((1 - ram  / current_ram ) * 100, 1),

        # Workload profile
        "workload_type": workload_type,

        # Instance selections
        "instances": instances,

        # Cost breakdown (includes egress + managed-services overhead)
        "pricing_model": pricing_model,
        "costs":         annotated_costs,

        # Overhead transparency
        "egress_rate":             EGRESS_AND_IOPS_RATE,
        "managed_services_premium": MANAGED_SERVICES_PREMIUM if apply_managed_services else 0.0,

        # Final recommendation
        "best_provider":     best_provider,
        "best_yearly_cost":  annotated_costs[best_provider]["selected"],
        "best_monthly_cost": round(annotated_costs[best_provider]["selected"] / 12, 2),
    }