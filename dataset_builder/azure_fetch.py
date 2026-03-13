import pandas as pd


def curated_azure():
    """
    Curated Azure VM dataset with realistic enterprise instances.
    """

    data = [

        {"provider": "Azure", "instance": "B2s", "vcpu": 2, "ram_gb": 4, "price_per_hour": 0.046},
        {"provider": "Azure", "instance": "B4ms", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.166},
        {"provider": "Azure", "instance": "B8ms", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.332},

        {"provider": "Azure", "instance": "D2s_v3", "vcpu": 2, "ram_gb": 8, "price_per_hour": 0.096},
        {"provider": "Azure", "instance": "D4s_v3", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.192},
        {"provider": "Azure", "instance": "D8s_v3", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.384},
        {"provider": "Azure", "instance": "D16s_v3", "vcpu": 16, "ram_gb": 64, "price_per_hour": 0.768},

        {"provider": "Azure", "instance": "D2s_v5", "vcpu": 2, "ram_gb": 8, "price_per_hour": 0.096},
        {"provider": "Azure", "instance": "D4s_v5", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.192},
        {"provider": "Azure", "instance": "D8s_v5", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.384},

        {"provider": "Azure", "instance": "E2s_v3", "vcpu": 2, "ram_gb": 16, "price_per_hour": 0.126},
        {"provider": "Azure", "instance": "E4s_v3", "vcpu": 4, "ram_gb": 32, "price_per_hour": 0.252},
        {"provider": "Azure", "instance": "E8s_v3", "vcpu": 8, "ram_gb": 64, "price_per_hour": 0.504},

        {"provider": "Azure", "instance": "E2s_v5", "vcpu": 2, "ram_gb": 16, "price_per_hour": 0.126},
        {"provider": "Azure", "instance": "E4s_v5", "vcpu": 4, "ram_gb": 32, "price_per_hour": 0.252},
        {"provider": "Azure", "instance": "E8s_v5", "vcpu": 8, "ram_gb": 64, "price_per_hour": 0.504},

    ]

    return pd.DataFrame(data)


def fetch_azure_instances(limit=30):
    """
    Currently uses curated dataset for stability.
    """

    print("Using curated Azure dataset")

    df = curated_azure()

    return df.head(limit)