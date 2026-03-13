from engines.cloud_cost_engine import run_cloud_analysis


def run_test(name, cpu, ram, cpu_util, ram_util, servers):

    print("\n====================================")
    print(f"TEST SCENARIO: {name}")
    print("====================================")

    result = run_cloud_analysis(
        current_vcpu=cpu,
        current_ram=ram,
        cpu_utilization=cpu_util,
        ram_utilization=ram_util,
        servers=servers
    )

    print("\nRecommended Resources")
    print("---------------------")
    print("CPU :", result["recommended_vcpu"])
    print("RAM :", result["recommended_ram"], "GB")

    print("\nSelected Instances")
    print("------------------")

    for provider, data in result["instances"].items():
        print(
            f"{provider} → {data['instance']} "
            f"({data['vcpu']} vCPU, {data['ram_gb']} GB RAM)"
        )

    print("\nAnnual Cost Estimate")
    print("--------------------")

    for provider, cost in result["costs"].items():
        print(f"{provider} : ${cost:,.2f}")

    print("\nRecommended Provider")
    print("--------------------")
    print(result["best_provider"])


# ----------------------------------
# TEST CASES
# ----------------------------------

# Balanced workload
run_test(
    "Balanced Workload",
    cpu=8,
    ram=32,
    cpu_util=30,
    ram_util=40,
    servers=10
)

# Memory heavy workload
run_test(
    "Memory Heavy Workload",
    cpu=8,
    ram=64,
    cpu_util=35,
    ram_util=70,
    servers=8
)

# Compute heavy workload
run_test(
    "Compute Heavy Workload",
    cpu=16,
    ram=16,
    cpu_util=70,
    ram_util=30,
    servers=6
)