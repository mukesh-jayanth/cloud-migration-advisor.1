import pandas as pd

DATA_PATH = "data/cloud_instances.csv"


def load_dataset():
    return pd.read_csv(DATA_PATH)


# -------------------------------
# Workload Classification
# -------------------------------
def classify_workload(vcpu, ram):

    ratio = ram / vcpu

    if ratio >= 6:
        return "memory"

    elif ratio <= 2:
        return "compute"

    else:
        return "general"


# -------------------------------
# Instance Family Detection
# -------------------------------
def get_instance_family(instance):

    prefix = instance[0].lower()

    if prefix in ["m", "d", "n", "t", "b"]:
        return "general"

    if prefix in ["c", "f"]:
        return "compute"

    if prefix in ["r", "e"]:
        return "memory"

    return "general"


# -------------------------------
# Instance Selection Engine
# -------------------------------
def find_best_instances(vcpu_required, ram_required):

    df = load_dataset()

    workload = classify_workload(vcpu_required, ram_required)

    # Step 1: filter instances that satisfy requirements
    suitable = df[
        (df["vcpu"] >= vcpu_required) &
        (df["ram_gb"] >= ram_required)
    ].copy()

    if suitable.empty:
        return {}

    # Step 2: prevent extreme RAM oversizing
    suitable = suitable[
        suitable["ram_gb"] <= ram_required * 4
    ]

    # Step 3: detect instance family
    suitable["family"] = suitable["instance"].apply(get_instance_family)

    # Step 4: compute resource difference
    suitable["cpu_diff"] = suitable["vcpu"] - vcpu_required
    suitable["ram_diff"] = suitable["ram_gb"] - ram_required
    suitable["resource_score"] = suitable["cpu_diff"] + suitable["ram_diff"]

    results = {}

    for provider in ["AWS", "Azure", "GCP"]:

        provider_df = suitable[suitable["provider"] == provider]

        if provider_df.empty:
            continue

        # Step 5: prefer workload-appropriate family
        preferred = provider_df[provider_df["family"] == workload]

        if not preferred.empty:
            provider_df = preferred

        # Step 6: choose best instance
        best = provider_df.sort_values(
            ["resource_score", "price_per_hour"]
        ).iloc[0]

        results[provider] = {
            "instance": best["instance"],
            "vcpu": int(best["vcpu"]),
            "ram_gb": float(best["ram_gb"]),
            "price_per_hour": float(best["price_per_hour"])
        }

    return results