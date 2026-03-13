import requests
import pandas as pd


def curated_aws():

    data = [

        {"provider":"AWS","instance":"t3.micro","vcpu":2,"ram_gb":1,"price_per_hour":0.0104},
        {"provider":"AWS","instance":"t3.small","vcpu":2,"ram_gb":2,"price_per_hour":0.0208},
        {"provider":"AWS","instance":"t3.medium","vcpu":2,"ram_gb":4,"price_per_hour":0.0416},
        {"provider":"AWS","instance":"t3.large","vcpu":2,"ram_gb":8,"price_per_hour":0.0832},
        {"provider":"AWS","instance":"t3.xlarge","vcpu":4,"ram_gb":16,"price_per_hour":0.1664},
        {"provider":"AWS","instance":"t3.2xlarge","vcpu":8,"ram_gb":32,"price_per_hour":0.3328},

        {"provider":"AWS","instance":"m5.large","vcpu":2,"ram_gb":8,"price_per_hour":0.096},
        {"provider":"AWS","instance":"m5.xlarge","vcpu":4,"ram_gb":16,"price_per_hour":0.192},
        {"provider":"AWS","instance":"m5.2xlarge","vcpu":8,"ram_gb":32,"price_per_hour":0.384},
        {"provider":"AWS","instance":"m5.4xlarge","vcpu":16,"ram_gb":64,"price_per_hour":0.768},

        {"provider":"AWS","instance":"c5.large","vcpu":2,"ram_gb":4,"price_per_hour":0.085},
        {"provider":"AWS","instance":"c5.xlarge","vcpu":4,"ram_gb":8,"price_per_hour":0.17},
        {"provider":"AWS","instance":"c5.2xlarge","vcpu":8,"ram_gb":16,"price_per_hour":0.34},
        {"provider":"AWS","instance":"c5.4xlarge","vcpu":16,"ram_gb":32,"price_per_hour":0.68},

        {"provider":"AWS","instance":"r5.large","vcpu":2,"ram_gb":16,"price_per_hour":0.126},
        {"provider":"AWS","instance":"r5.xlarge","vcpu":4,"ram_gb":32,"price_per_hour":0.252},
        {"provider":"AWS","instance":"r5.2xlarge","vcpu":8,"ram_gb":64,"price_per_hour":0.504},
        {"provider":"AWS","instance":"r5.4xlarge","vcpu":16,"ram_gb":128,"price_per_hour":1.008},

        {"provider":"AWS","instance":"m6i.large","vcpu":2,"ram_gb":8,"price_per_hour":0.096},
        {"provider":"AWS","instance":"m6i.xlarge","vcpu":4,"ram_gb":16,"price_per_hour":0.192},

        {"provider":"AWS","instance":"c6i.large","vcpu":2,"ram_gb":4,"price_per_hour":0.085},
        {"provider":"AWS","instance":"c6i.xlarge","vcpu":4,"ram_gb":8,"price_per_hour":0.17},

        {"provider":"AWS","instance":"r6i.large","vcpu":2,"ram_gb":16,"price_per_hour":0.126},
        {"provider":"AWS","instance":"r6i.xlarge","vcpu":4,"ram_gb":32,"price_per_hour":0.252},

    ]

    return pd.DataFrame(data)


def estimate_price(vcpu):
    """
    Estimate price if using API specs
    """
    return 0.05 * vcpu


def fetch_aws_instances(limit=30):

    try:

        url = "https://ec2.us-east-1.amazonaws.com/?Action=DescribeInstanceTypes&Version=2016-11-15"

        response = requests.get(url, timeout=20)

        from io import StringIO
        tables = pd.read_xml(StringIO(response.text), parser="etree")

        rows = []

        for _, row in tables.iterrows():

            instance = row.get("instanceType")
            vcpu = row.get("defaultVCpus")
            ram = row.get("sizeInMiB")

            if instance and vcpu and ram:

                rows.append({
                    "provider": "AWS",
                    "instance": instance,
                    "vcpu": int(vcpu),
                    "ram_gb": float(ram) / 1024,
                    "price_per_hour": estimate_price(int(vcpu))
                })

            if len(rows) >= limit:
                break

        df = pd.DataFrame(rows)

        if df.empty:
            raise Exception("AWS API returned empty dataset")

        print("AWS API successful")

        return df

    except Exception as e:

        print("AWS API failed → using curated dataset")

        return curated_aws()