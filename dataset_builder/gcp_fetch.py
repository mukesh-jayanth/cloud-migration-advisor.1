import requests
import pandas as pd


def curated_gcp():

    data = [

        # -------------------
        # E2 (budget/general)
        # -------------------
        {"provider":"GCP","instance":"e2-micro","vcpu":2,"ram_gb":1,"price_per_hour":0.008},
        {"provider":"GCP","instance":"e2-small","vcpu":2,"ram_gb":2,"price_per_hour":0.016},
        {"provider":"GCP","instance":"e2-medium","vcpu":2,"ram_gb":4,"price_per_hour":0.033},

        {"provider":"GCP","instance":"e2-standard-2","vcpu":2,"ram_gb":8,"price_per_hour":0.067},
        {"provider":"GCP","instance":"e2-standard-4","vcpu":4,"ram_gb":16,"price_per_hour":0.134},
        {"provider":"GCP","instance":"e2-standard-8","vcpu":8,"ram_gb":32,"price_per_hour":0.268},
        {"provider":"GCP","instance":"e2-standard-16","vcpu":16,"ram_gb":64,"price_per_hour":0.536},
        {"provider":"GCP","instance":"e2-standard-32","vcpu":32,"ram_gb":128,"price_per_hour":1.072},

        # -------------------
        # N2 (mainline newer)
        # -------------------
        {"provider":"GCP","instance":"n2-standard-2","vcpu":2,"ram_gb":8,"price_per_hour":0.097},
        {"provider":"GCP","instance":"n2-standard-4","vcpu":4,"ram_gb":16,"price_per_hour":0.189},
        {"provider":"GCP","instance":"n2-standard-8","vcpu":8,"ram_gb":32,"price_per_hour":0.379},
        {"provider":"GCP","instance":"n2-standard-16","vcpu":16,"ram_gb":64,"price_per_hour":0.758},
        {"provider":"GCP","instance":"n2-standard-32","vcpu":32,"ram_gb":128,"price_per_hour":1.516},
        {"provider":"GCP","instance":"n2-standard-64","vcpu":64,"ram_gb":256,"price_per_hour":3.032},

        # -------------------
        # C2 (compute optimized)
        # -------------------
        {"provider":"GCP","instance":"c2-standard-4","vcpu":4,"ram_gb":16,"price_per_hour":0.209},
        {"provider":"GCP","instance":"c2-standard-8","vcpu":8,"ram_gb":32,"price_per_hour":0.417},
        {"provider":"GCP","instance":"c2-standard-16","vcpu":16,"ram_gb":64,"price_per_hour":0.834},
        {"provider":"GCP","instance":"c2-standard-32","vcpu":32,"ram_gb":128,"price_per_hour":1.668},
        {"provider":"GCP","instance":"c2-standard-60","vcpu":60,"ram_gb":240,"price_per_hour":3.130},

        # -------------------
        # N1 (older gen - slightly cheaper)
        # -------------------
        {"provider":"GCP","instance":"n1-standard-1","vcpu":1,"ram_gb":3.75,"price_per_hour":0.047},
        {"provider":"GCP","instance":"n1-standard-2","vcpu":2,"ram_gb":7.5,"price_per_hour":0.095},
        {"provider":"GCP","instance":"n1-standard-4","vcpu":4,"ram_gb":15,"price_per_hour":0.19},
        {"provider":"GCP","instance":"n1-standard-8","vcpu":8,"ram_gb":30,"price_per_hour":0.38},
        {"provider":"GCP","instance":"n1-standard-16","vcpu":16,"ram_gb":60,"price_per_hour":0.76},
        {"provider":"GCP","instance":"n1-standard-32","vcpu":32,"ram_gb":120,"price_per_hour":1.52},

        # -------------------
        # Extra balancing (high tiers)
        # -------------------
        {"provider":"GCP","instance":"n2-highmem-32","vcpu":32,"ram_gb":256,"price_per_hour":2.0},
        {"provider":"GCP","instance":"n2-highmem-64","vcpu":64,"ram_gb":512,"price_per_hour":4.0},

        {"provider":"GCP","instance":"n2-highcpu-32","vcpu":32,"ram_gb":32,"price_per_hour":1.3},
        {"provider":"GCP","instance":"n2-highcpu-64","vcpu":64,"ram_gb":64,"price_per_hour":2.6},

    ]

    return pd.DataFrame(data)


def parse_gcp_specs(instance):
    """
    Extract CPU/RAM from instance name
    """

    try:
        vcpu = int(instance.split("-")[-1])
        ram = vcpu * 4
        return vcpu, ram
    except:
        return None, None


def fetch_gcp_instances(limit=30):

    try:

        url = "https://cloudpricingcalculator.appspot.com/static/data/pricelist.json"

        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers, timeout=20)

        data = response.json()

        rows = []

        compute_data = data.get("gcp_price_list", {})

        for key, value in compute_data.items():

            if key.startswith("CP-COMPUTEENGINE-VMIMAGE"):

                instance = key.split("-")[-1]

                price = value.get("us")

                vcpu, ram = parse_gcp_specs(instance)

                if instance and vcpu and ram and price:

                    rows.append({
                        "provider": "GCP",
                        "instance": instance,
                        "vcpu": vcpu,
                        "ram_gb": ram,
                        "price_per_hour": float(price)
                    })

                if len(rows) >= limit:
                    break

        df = pd.DataFrame(rows)

        if df.empty:
            raise Exception("GCP API returned empty dataset")

        print("GCP API successful")

        return df

    except Exception as e:

        print("GCP API failed → using curated dataset")

        return curated_gcp()