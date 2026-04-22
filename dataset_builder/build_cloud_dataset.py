import pandas as pd
import os
from pathlib import Path

from .azure_fetch import fetch_azure_instances
from .aws_fetch import fetch_aws_instances
from .gcp_fetch import fetch_gcp_instances


# Safe project root path
BASE_DIR = Path(__file__).resolve().parent.parent

# Dataset location
DATA_PATH = BASE_DIR / "data" / "cloud_instances.csv"

# Required dataset schema
required_columns = {"provider", "instance", "vcpu", "ram_gb", "price_per_hour"}


def validate_schema(df, name):

    if df.empty:
        print(f"{name} dataset is empty, skipping validation.")
        return

    if set(df.columns) != required_columns:
        raise ValueError(f"{name} schema mismatch: {df.columns}")


def build_dataset(force_refresh=False):

    # Check cached dataset
    if DATA_PATH.exists() and not force_refresh:
        print("Loading cached dataset...")

        dataset = pd.read_csv(DATA_PATH)

        print("Dataset loaded:", len(dataset))

        print("\nProvider distribution:")
        print(dataset["provider"].value_counts())

        return dataset

    print("Building dataset from cloud APIs...")

    # Fetch datasets with debug prints
    print("Fetching Azure instances...")
    azure_df = fetch_azure_instances()

    print("Fetching AWS instances...")
    aws_df = fetch_aws_instances()

    print("Fetching GCP instances...")
    gcp_df = fetch_gcp_instances()

    # Validate schema
    validate_schema(aws_df, "AWS")
    validate_schema(azure_df, "Azure")
    validate_schema(gcp_df, "GCP")

    # Combine datasets
    dataset = pd.concat([azure_df, aws_df, gcp_df])

    # Clean dataset
    dataset = dataset.reset_index(drop=True)

    dataset = dataset.drop_duplicates(subset=["provider", "instance"])

    dataset["vcpu"] = pd.to_numeric(dataset["vcpu"], errors="coerce")
    dataset["ram_gb"] = pd.to_numeric(dataset["ram_gb"], errors="coerce")
    dataset["price_per_hour"] = pd.to_numeric(dataset["price_per_hour"], errors="coerce")

    # Ensure data directory exists
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save dataset
    dataset.to_csv(DATA_PATH, index=False)

    print("Dataset created:", len(dataset))

    print("\nProvider distribution:")
    print(dataset["provider"].value_counts())

    print("\nDataset preview:")
    print(dataset.head())

    return dataset


# Allow file to run directly
if __name__ == "__main__":
    build_dataset()