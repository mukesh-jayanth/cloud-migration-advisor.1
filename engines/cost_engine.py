import pandas as pd
import math

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
# Financial Assumptions (Configurable)
# ---------------------------------------
# These defaults can be overridden by passing a custom
# FinancialConfig object into any calculation function.

class FinancialConfig:
    """
    Holds all financial assumptions for the cost engine.
    Override defaults to model different cost scenarios.
    """

    def __init__(
        self,
        server_unit_cost: float = 5000,
        maintenance_rate: float = 0.15,
        power_cost_per_server: float = 500,
        admin_salary: float = 80000,
        servers_per_admin: int = 25,
        storage_cost_per_tb: float = 150,        # NEW: $/TB/year for storage maintenance
        storage_hardware_cost_per_tb: float = 500 # NEW: one-time CapEx per TB
    ):
        self.server_unit_cost = server_unit_cost
        self.maintenance_rate = maintenance_rate
        self.power_cost_per_server = power_cost_per_server
        self.admin_salary = admin_salary
        self.servers_per_admin = servers_per_admin
        self.storage_cost_per_tb = storage_cost_per_tb
        self.storage_hardware_cost_per_tb = storage_hardware_cost_per_tb


# Shared default config instance
DEFAULT_CONFIG = FinancialConfig()


# ---------------------------------------
# Input Validation
# ---------------------------------------

def validate_inputs(servers: float, storage_tb: float):
    """Raises ValueError if core inputs are invalid."""
    if servers <= 0:
        raise ValueError(f"Server count must be positive, got {servers}.")
    if storage_tb < 0:
        raise ValueError(f"Storage cannot be negative, got {storage_tb} TB.")


# ---------------------------------------
# Load Infrastructure Dataset
# ---------------------------------------

def load_infrastructure(file_path: str):
    """
    Reads an Excel infrastructure file and derives
    total server count and total storage.
    """
    df = pd.read_excel(file_path)

    required_cols = {"Quantity", "Storage (TB) per Server"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    total_servers = df["Quantity"].sum()
    total_storage = (df["Quantity"] * df["Storage (TB) per Server"]).sum()

    return df, total_servers, total_storage


# ---------------------------------------
# Individual Cost Calculations
# ---------------------------------------

def calculate_hardware_cost(servers: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """One-time CapEx for server hardware."""
    return servers * config.server_unit_cost


def calculate_storage_hardware_cost(storage_tb: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """One-time CapEx for storage hardware (SAN/NAS)."""
    return storage_tb * config.storage_hardware_cost_per_tb


def calculate_maintenance_cost(hardware_cost: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """Annual server maintenance (% of hardware CapEx)."""
    return hardware_cost * config.maintenance_rate


def calculate_power_cost(servers: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """Annual power & cooling cost."""
    return servers * config.power_cost_per_server


def calculate_staff_cost(servers: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """Annual IT staff cost based on admin-to-server ratio."""
    admins_required = max(1, math.ceil(servers / config.servers_per_admin))
    return admins_required * config.admin_salary


def calculate_storage_opex(storage_tb: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """Annual storage operational cost (licensing, maintenance)."""
    return storage_tb * config.storage_cost_per_tb


# ---------------------------------------
# Core Cost Aggregator
# ---------------------------------------

def calculate_annual_cost(
    servers: float,
    storage_tb: float,
    config: FinancialConfig = DEFAULT_CONFIG
) -> tuple[float, float, float]:
    """
    Computes total CapEx and annual OpEx.

    Returns:
        total_capex   — one-time hardware + storage capital expenditure
        annual_opex   — recurring yearly operational cost
        hardware_cost — server CapEx component (exposed for reporting)
    """
    # CapEx (one-time)
    hardware_cost = calculate_hardware_cost(servers, config)
    storage_capex = calculate_storage_hardware_cost(storage_tb, config)
    total_capex = hardware_cost + storage_capex

    # OpEx (annual recurring)
    maintenance = calculate_maintenance_cost(hardware_cost, config)
    power = calculate_power_cost(servers, config)
    staff = calculate_staff_cost(servers, config)
    storage_opex = calculate_storage_opex(storage_tb, config)

    annual_opex = maintenance + power + staff + storage_opex

    return total_capex, annual_opex, hardware_cost


# ---------------------------------------
# Shared TCO Result Builder
# ---------------------------------------

def build_tco_result(
    servers: float,
    storage_tb: float,
    config: FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Central function that assembles the full TCO result dict.
    Used by all input modes (file, preset, manual) to avoid duplication.
    """
    validate_inputs(servers, storage_tb)

    total_capex, annual_opex, hardware_cost = calculate_annual_cost(servers, storage_tb, config)

    return {
        # Infrastructure
        "servers": int(servers),
        "storage_tb": float(storage_tb),

        # CapEx breakdown
        "hardware_cost": float(hardware_cost),
        "storage_capex": float(calculate_storage_hardware_cost(storage_tb, config)),
        "total_capex": float(total_capex),

        # OpEx breakdown (annual)
        "annual_maintenance": float(calculate_maintenance_cost(hardware_cost, config)),
        "annual_power": float(calculate_power_cost(servers, config)),
        "annual_staff": float(calculate_staff_cost(servers, config)),
        "annual_storage_opex": float(calculate_storage_opex(storage_tb, config)),
        "annual_operational_cost": float(annual_opex),

        # TCO projections
        "tco_3yr": float(total_capex + annual_opex * 3),
        "tco_5yr": float(total_capex + annual_opex * 5),
    }


# ---------------------------------------
# Public API — Three Input Modes
# ---------------------------------------

def calculate_onprem_tco(
    file_path: str = None,
    preset: str = None,
    config: FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Computes on-premise TCO from an Excel file or a named preset.

    Args:
        file_path : path to Excel infrastructure dataset
        preset    : one of "small", "medium", "large"
        config    : optional FinancialConfig to override assumptions
    """
    if file_path:
        _, servers, storage = load_infrastructure(file_path)
    elif preset:
        if preset not in ENTERPRISE_PRESETS:
            raise ValueError(f"Unknown preset '{preset}'. Choose from: {list(ENTERPRISE_PRESETS)}")
        preset_data = ENTERPRISE_PRESETS[preset]
        servers = preset_data["servers"]
        storage = preset_data["storage_tb"]
    else:
        raise ValueError("Provide either a file_path or a preset name.")

    return build_tco_result(servers, storage, config)


def calculate_manual_tco(
    servers: float,
    storage_tb: float,
    config: FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Computes on-premise TCO from manually supplied values.

    Args:
        servers    : total number of on-premise servers
        storage_tb : total storage in terabytes
        config     : optional FinancialConfig to override assumptions
    """
    return build_tco_result(servers, storage_tb, config)