import requests
import pandas as pd


def curated_azure():

    data = [

        # -------------------
        # B-series (burstable)
        # -------------------
        {"provider": "Azure", "instance": "B2s", "vcpu": 2, "ram_gb": 4, "price_per_hour": 0.046},
        {"provider": "Azure", "instance": "B4ms", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.166},
        {"provider": "Azure", "instance": "B8ms", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.332},
        {"provider": "Azure", "instance": "B16ms", "vcpu": 16, "ram_gb": 64, "price_per_hour": 0.664},

        # -------------------
        # D v3 (baseline)
        # -------------------
        {"provider": "Azure", "instance": "D2s_v3", "vcpu": 2, "ram_gb": 8, "price_per_hour": 0.096},
        {"provider": "Azure", "instance": "D4s_v3", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.192},
        {"provider": "Azure", "instance": "D8s_v3", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.384},
        {"provider": "Azure", "instance": "D16s_v3", "vcpu": 16, "ram_gb": 64, "price_per_hour": 0.768},
        {"provider": "Azure", "instance": "D32s_v3", "vcpu": 32, "ram_gb": 128, "price_per_hour": 1.536},
        {"provider": "Azure", "instance": "D64s_v3", "vcpu": 64, "ram_gb": 256, "price_per_hour": 3.072},

        # -------------------
        # D v5 (+5%)
        # -------------------
        {"provider": "Azure", "instance": "D2s_v5", "vcpu": 2, "ram_gb": 8, "price_per_hour": 0.101},
        {"provider": "Azure", "instance": "D4s_v5", "vcpu": 4, "ram_gb": 16, "price_per_hour": 0.202},
        {"provider": "Azure", "instance": "D8s_v5", "vcpu": 8, "ram_gb": 32, "price_per_hour": 0.403},
        {"provider": "Azure", "instance": "D16s_v5", "vcpu": 16, "ram_gb": 64, "price_per_hour": 0.806},
        {"provider": "Azure", "instance": "D32s_v5", "vcpu": 32, "ram_gb": 128, "price_per_hour": 1.613},
        {"provider": "Azure", "instance": "D64s_v5", "vcpu": 64, "ram_gb": 256, "price_per_hour": 3.226},

        # -------------------
        # E v3 (baseline)
        # -------------------
        {"provider": "Azure", "instance": "E2s_v3", "vcpu": 2, "ram_gb": 16, "price_per_hour": 0.126},
        {"provider": "Azure", "instance": "E4s_v3", "vcpu": 4, "ram_gb": 32, "price_per_hour": 0.252},
        {"provider": "Azure", "instance": "E8s_v3", "vcpu": 8, "ram_gb": 64, "price_per_hour": 0.504},
        {"provider": "Azure", "instance": "E16s_v3", "vcpu": 16, "ram_gb": 128, "price_per_hour": 1.008},
        {"provider": "Azure", "instance": "E32s_v3", "vcpu": 32, "ram_gb": 256, "price_per_hour": 2.016},
        {"provider": "Azure", "instance": "E64s_v3", "vcpu": 64, "ram_gb": 512, "price_per_hour": 4.032},

        # -------------------
        # E v5 (+5%)
        # -------------------
        {"provider": "Azure", "instance": "E2s_v5", "vcpu": 2, "ram_gb": 16, "price_per_hour": 0.132},
        {"provider": "Azure", "instance": "E4s_v5", "vcpu": 4, "ram_gb": 32, "price_per_hour": 0.265},
        {"provider": "Azure", "instance": "E8s_v5", "vcpu": 8, "ram_gb": 64, "price_per_hour": 0.529},
        {"provider": "Azure", "instance": "E16s_v5", "vcpu": 16, "ram_gb": 128, "price_per_hour": 1.058},
        {"provider": "Azure", "instance": "E32s_v5", "vcpu": 32, "ram_gb": 256, "price_per_hour": 2.117},
        {"provider": "Azure", "instance": "E64s_v5", "vcpu": 64, "ram_gb": 512, "price_per_hour": 4.234},

        # -------------------
        # Extra tiers (48 vCPU)
        # -------------------
        {"provider": "Azure", "instance": "D48s_v3", "vcpu": 48, "ram_gb": 192, "price_per_hour": 2.304},
        {"provider": "Azure", "instance": "D48s_v5", "vcpu": 48, "ram_gb": 192, "price_per_hour": 2.419},

        {"provider": "Azure", "instance": "E48s_v3", "vcpu": 48, "ram_gb": 384, "price_per_hour": 3.024},
        {"provider": "Azure", "instance": "E48s_v5", "vcpu": 48, "ram_gb": 384, "price_per_hour": 3.175},

    ]

    return pd.DataFrame(data)


def fetch_azure_instances(limit=30):
    """
    Currently uses curated dataset for stability.
    """

    print("Using curated Azure dataset")

    df = curated_azure()

    return df.head(limit)