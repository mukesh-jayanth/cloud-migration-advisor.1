import pandas as pd

# ---------------------------------------
# Enterprise Presets
# ---------------------------------------

ENTERPRISE_PRESETS = {

    "small": {
        "servers": 8,
        "avg_util": 0.30,
        "storage_tb": 5,
        "compliance": "low",
        "downtime": "high",
        "growth_rate": 0.10
    },

    "medium": {
        "servers": 21,
        "avg_util": 0.38,
        "storage_tb": 18,
        "compliance": "medium",
        "downtime": "medium",
        "growth_rate": 0.15
    },

    "large": {
        "servers": 120,
        "avg_util": 0.45,
        "storage_tb": 120,
        "compliance": "high",
        "downtime": "low",
        "growth_rate": 0.20
    }
}

# ---------------------------------------
# Financial Assumptions
# ---------------------------------------

SERVER_COST = 5000
MAINTENANCE_RATE = 0.15
POWER_COST_PER_SERVER = 500
ADMIN_SALARY = 80000
SERVERS_PER_ADMIN = 25


# ---------------------------------------
# Load Infrastructure Dataset
# ---------------------------------------

def load_infrastructure(file_path):

    df = pd.read_excel(file_path)

    total_servers = df["Quantity"].sum()

    total_storage = (
        df["Quantity"] *
        df["Storage (TB) per Server"]
    ).sum()

    return df, total_servers, total_storage


# ---------------------------------------
# Cost Calculations
# ---------------------------------------

def calculate_hardware_cost(servers):

    return servers * SERVER_COST


def calculate_maintenance_cost(hardware_cost):

    return hardware_cost * MAINTENANCE_RATE


def calculate_power_cost(servers):

    return servers * POWER_COST_PER_SERVER


def calculate_staff_cost(servers):

    admins_required = max(1, round(servers / SERVERS_PER_ADMIN))

    return admins_required * ADMIN_SALARY


# ---------------------------------------
# Manual Parameter Input
# ---------------------------------------

def calculate_manual_tco(servers, storage_tb):

    hardware_cost = calculate_hardware_cost(servers)

    maintenance = calculate_maintenance_cost(hardware_cost)

    power = calculate_power_cost(servers)

    staff = calculate_staff_cost(servers)

    annual_cost = maintenance + power + staff

    tco_3yr = hardware_cost + (annual_cost * 3)

    tco_5yr = hardware_cost + (annual_cost * 5)

    return {

        "servers": int(servers),
        "storage_tb": float(storage_tb),
        "hardware_cost": float(hardware_cost),
        "annual_operational_cost": float(annual_cost),
        "tco_3yr": float(tco_3yr),
        "tco_5yr": float(tco_5yr)

    }


# ---------------------------------------
# Main Cost Engine
# ---------------------------------------

def calculate_onprem_tco(file_path=None, preset=None):

    if file_path:

        df, servers, storage = load_infrastructure(file_path)

    elif preset:

        preset_data = ENTERPRISE_PRESETS[preset]

        servers = preset_data["servers"]
        storage = preset_data["storage_tb"]

    else:
        raise ValueError("Provide either dataset or preset.")


    # Hardware
    hardware_cost = calculate_hardware_cost(servers)

    # Operational costs
    maintenance = calculate_maintenance_cost(hardware_cost)
    power = calculate_power_cost(servers)
    staff = calculate_staff_cost(servers)

    annual_cost = maintenance + power + staff

    tco_3yr = hardware_cost + (annual_cost * 3)
    tco_5yr = hardware_cost + (annual_cost * 5)

    return {

    "servers": int(servers),
    "storage_tb": float(storage),
    "hardware_cost": float(hardware_cost),
    "annual_operational_cost": float(annual_cost),
    "tco_3yr": float(tco_3yr),
    "tco_5yr": float(tco_5yr)

}