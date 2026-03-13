import math
HOURS_PER_YEAR = 8760
SAFETY_BUFFER = 1.3

from engines.instance_selector import find_best_instances

def calculate_yearly_cost(price_per_hour, servers):

    return price_per_hour * HOURS_PER_YEAR * servers


def calculate_provider_costs(instances, servers):

    costs = {}

    for provider, data in instances.items():

        yearly_cost = calculate_yearly_cost(
            data["price_per_hour"],
            servers
        )

        costs[provider] = yearly_cost

    return costs

# Provider Comparison Engine
def choose_best_provider(costs):

    best_provider = min(costs, key=costs.get)

    return best_provider

# Infrastructure Right-Sizing Engine
def recommend_resources(
    current_vcpu,
    current_ram,
    cpu_utilization,
    ram_utilization
):

    cpu_util = cpu_utilization / 100
    ram_util = ram_utilization / 100

    required_cpu = current_vcpu * cpu_util * SAFETY_BUFFER
    required_ram = current_ram * ram_util * SAFETY_BUFFER

    recommended_cpu = math.ceil(required_cpu)
    recommended_ram = math.ceil(required_ram)

    # round to nearest standard cloud size
    standard_sizes = [1,2,4,8,16,32,64,128]

    recommended_ram = min(
        standard_sizes,
        key=lambda x: abs(x - recommended_ram)
    )

    return recommended_cpu, recommended_ram

# Full Decision Pipeline
def run_cloud_analysis(
    current_vcpu,
    current_ram,
    cpu_utilization,
    ram_utilization,
    servers
):

    # Step 1: Right-size infrastructure
    vcpu, ram = recommend_resources(
        current_vcpu,
        current_ram,
        cpu_utilization,
        ram_utilization
    )

    # Step 2: Find instances
    instances = find_best_instances(vcpu, ram)

    # Step 3: Calculate costs
    costs = calculate_provider_costs(instances, servers)

    # Step 4: Choose best provider
    best_provider = choose_best_provider(costs)

    return {
        "recommended_vcpu": vcpu,
        "recommended_ram": ram,
        "instances": instances,
        "costs": costs,
        "best_provider": best_provider
    }