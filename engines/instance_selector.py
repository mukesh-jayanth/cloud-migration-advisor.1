import logging
import pandas as pd
from logger_config import get_logger

logger = get_logger(__name__)

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "cloud_instances.csv")

# -------------------------------
# Workload Classification Thresholds
# Named constants — do not bury magic numbers in logic
# -------------------------------
MEMORY_RATIO_THRESHOLD = 6
COMPUTE_RATIO_THRESHOLD = 2

# -------------------------------
# Dataset Cache
# Loaded once at module level — avoids repeated disk reads
# -------------------------------
_df = None


def load_dataset() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(DATA_PATH)
    return _df


def reload_dataset() -> pd.DataFrame:
    """Force a fresh reload — useful during testing or if CSV changes."""
    global _df
    _df = pd.read_csv(DATA_PATH)
    return _df


# -------------------------------
# Workload Classification
# -------------------------------
def classify_workload(vcpu: int, ram: float) -> str:
    """
    Classify workload type based on RAM-to-CPU ratio.

    Returns:
        'memory'  — RAM-heavy workloads (databases, caches)
        'compute' — CPU-heavy workloads (batch jobs, ML inference)
        'general' — balanced workloads (web servers, APIs)
    """
    ratio = ram / vcpu

    if ratio >= MEMORY_RATIO_THRESHOLD:
        return "memory"
    elif ratio <= COMPUTE_RATIO_THRESHOLD:
        return "compute"
    else:
        return "general"


# -------------------------------
# Instance Family Detection
# Provider-aware — handles AWS, Azure, GCP naming conventions
# -------------------------------
def get_instance_family(provider: str, instance: str) -> str:
    """
    Detect the instance family (general / compute / memory)
    based on provider-specific naming conventions.

    AWS   : m/t = general, c = compute, r = memory
    Azure : D/B = general, F = compute, E = memory
    GCP   : standard = general, highcpu = compute, highmem = memory
    """
    name = instance.lower()

    if provider == "AWS":
        if name.startswith(("m", "t")):
            return "general"
        if name.startswith("c"):
            return "compute"
        if name.startswith("r"):
            return "memory"

    elif provider == "Azure":
        if name.startswith(("d", "b")):
            return "general"
        if name.startswith("f"):
            return "compute"
        if name.startswith("e"):
            return "memory"

    elif provider == "GCP":
        if "standard" in name:
            return "general"
        if "highcpu" in name:
            return "compute"
        if "highmem" in name:
            return "memory"

    return "general"


# -------------------------------
# Input Validation
# -------------------------------
def validate_inputs(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float,
    servers: int
) -> None:
    """
    Validate all user inputs before processing.
    Raises ValueError with a clear message on bad input.
    """
    errors = []

    if current_vcpu <= 0:
        errors.append(f"current_vcpu must be > 0, got {current_vcpu}")
    if current_ram <= 0:
        errors.append(f"current_ram must be > 0, got {current_ram}")
    if not (1 <= cpu_utilization <= 100):
        errors.append(f"cpu_utilization must be 1–100, got {cpu_utilization}")
    if not (1 <= ram_utilization <= 100):
        errors.append(f"ram_utilization must be 1–100, got {ram_utilization}")
    if servers <= 0:
        errors.append(f"servers must be > 0, got {servers}")

    if errors:
        raise ValueError("Input validation failed:\n  " + "\n  ".join(errors))


# -------------------------------
# Instance Selection Engine
# -------------------------------
def find_best_instances(vcpu_required: int, ram_required: float) -> dict:
    """
    Select the best matching cloud instance per provider.

    Steps:
      1. Filter instances meeting minimum CPU + RAM requirements
      2. Prevent extreme RAM oversizing (cap at 4×)
      3. Detect instance family per provider
      4. Compute normalized resource score (CPU diff + RAM diff)
      5. Prefer workload-appropriate family
      6. Pick lowest resource score, then lowest price

    Returns:
        dict of provider → instance details, or raises ValueError if
        no suitable instances are found for any provider.
    """
    df = load_dataset()
    workload = classify_workload(vcpu_required, ram_required)

    # Step 1: Filter by minimum requirements
    suitable = df[
        (df["vcpu"] >= vcpu_required) &
        (df["ram_gb"] >= ram_required)
    ].copy()

    if suitable.empty:
        raise ValueError(
            f"No cloud instances found for {vcpu_required} vCPU / "
            f"{ram_required} GB RAM. Consider revising requirements."
        )

    # Step 2: Prevent extreme oversizing (cap at 4× RAM)
    suitable = suitable[suitable["ram_gb"] <= ram_required * 4]

    if suitable.empty:
        raise ValueError(
            f"All instances matching {vcpu_required} vCPU / {ram_required} GB RAM "
            f"exceed the 4× RAM oversizing limit. Check your dataset."
        )

    # Step 3: Detect instance family (provider-aware)
    suitable["family"] = suitable.apply(
        lambda row: get_instance_family(row["provider"], row["instance"]),
        axis=1
    )

    # Step 4: Normalized resource score
    # Normalizing prevents RAM (large numbers) from dominating CPU (small numbers)
    suitable["cpu_diff"] = suitable["vcpu"] - vcpu_required
    suitable["ram_diff"] = suitable["ram_gb"] - ram_required
    suitable["resource_score"] = (
        suitable["cpu_diff"] / vcpu_required +
        suitable["ram_diff"] / ram_required
    )

    results = {}
    skipped_providers = []

    for provider in suitable["provider"].unique():
        provider_df = suitable[suitable["provider"] == provider]

        if provider_df.empty:
            skipped_providers.append(provider)
            continue

        # Step 5: Prefer workload-appropriate family
        preferred = provider_df[provider_df["family"] == workload]
        if not preferred.empty:
            provider_df = preferred

        # Step 6: Best instance = lowest resource score, then efficiency, then lowest price
        # Efficiency uses requirement-relative normalization so vCPU and RAM
        # contribute equally regardless of their raw scale difference.
        # e.g. needed 4 vCPU / 16 GB -> instance with 8 vCPU / 32 GB scores 2.0 + 2.0
        provider_df = provider_df.copy()
        provider_df["efficiency"] = (
            provider_df["price_per_hour"] /
            (provider_df["vcpu"] / vcpu_required +
             provider_df["ram_gb"] / ram_required)
        )

        best = provider_df.sort_values(
            ["resource_score", "efficiency", "price_per_hour"]
        ).iloc[0]

        results[provider] = {
            "instance": best["instance"],
            "vcpu": int(best["vcpu"]),
            "ram_gb": float(best["ram_gb"]),
            "price_per_hour": float(best["price_per_hour"]),
            "family": best["family"],
            "workload_match": best["family"] == workload   # restored
        }

    # Warn if some providers had no data
    if skipped_providers:
        logger.warning(
            "No instances found for providers: %s. Comparison will be incomplete.",
            skipped_providers
        )

    if not results:
        raise ValueError(
            f"No suitable instances found across any provider for "
            f"{vcpu_required} vCPU / {ram_required} GB RAM."
        )

    return results, workload