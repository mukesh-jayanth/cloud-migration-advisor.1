import pandas as pd
import math

# -----------------------------------------------------------------------
# Enterprise Presets
# -----------------------------------------------------------------------

ENTERPRISE_PRESETS = {
    "small": {
        "servers":      8,
        "avg_util":     0.30,
        "storage_tb":   5,
        "compliance":   "low",
        "downtime":     "high",
        "growth_rate":  0.10
    },
    "medium": {
        "servers":      21,
        "avg_util":     0.38,
        "storage_tb":   18,
        "compliance":   "medium",
        "downtime":     "medium",
        "growth_rate":  0.15
    },
    "large": {
        "servers":      120,
        "avg_util":     0.45,
        "storage_tb":   120,
        "compliance":   "high",
        "downtime":     "low",
        "growth_rate":  0.20
    }
}


# -----------------------------------------------------------------------
# Financial Assumptions (Configurable)
# -----------------------------------------------------------------------

class FinancialConfig:
    """
    Holds all financial assumptions for the cost engine.
    Override defaults to model different cost scenarios.

    True On-Prem Baseline:
        Includes a Maintenance & Facilities Overhead rate (10–15%) that
        captures power, cooling, and human-intervention costs, so that
        the on-prem baseline is not artificially cheap vs. cloud.
    """

    def __init__(
        self,
        server_unit_cost:             float = 5000,
        maintenance_rate:             float = 0.15,
        power_cost_per_server:        float = 500,
        admin_salary:                 float = 80000,
        servers_per_admin:            int   = 25,
        storage_cost_per_tb:          float = 150,    # $/TB/year for storage maintenance
        storage_hardware_cost_per_tb: float = 500,    # one-time CapEx per TB
        # ── NEW: Maintenance & Facilities Overhead ──────────────────────
        # Accounts for the "Legacy Tax": power usage effectiveness (PUE),
        # cooling plant amortisation, physical security, and the hidden
        # human cost of keeping bare-metal running 24/7.
        # Industry benchmark: 10–15% of total hardware CapEx per year.
        facilities_overhead_rate:     float = 0.12,   # 12% (midpoint of 10–15%)
    ):
        self.server_unit_cost              = server_unit_cost
        self.maintenance_rate              = maintenance_rate
        self.power_cost_per_server         = power_cost_per_server
        self.admin_salary                  = admin_salary
        self.servers_per_admin             = servers_per_admin
        self.storage_cost_per_tb           = storage_cost_per_tb
        self.storage_hardware_cost_per_tb  = storage_hardware_cost_per_tb
        self.facilities_overhead_rate      = facilities_overhead_rate


# Shared default config instance
DEFAULT_CONFIG = FinancialConfig()


# -----------------------------------------------------------------------
# Migration Economics — Default Heuristics
# -----------------------------------------------------------------------
# These define what it really costs to execute each strategy.
# Labor multipliers are relative to a "baseline" SRE/migration cost.
# Allow override by passing has_skilled_team=True or has_cicd=True.

MIGRATION_ECONOMICS = {
    "Rehost": {
        "labor_multiplier":      1.0,
        "double_run_months":     1.5,    # midpoint of 1–2 months
        "description":           "Lift & Shift — minimal re-architecture"
    },
    "Replatform": {
        "labor_multiplier":      2.5,
        "double_run_months":     4.5,    # midpoint of 3–6 months
        "description":           "Re-platform — selective managed-service adoption"
    },
    "Refactor": {
        "labor_multiplier":      10.0,
        "double_run_months":     12.0,   # minimum 12 months
        "description":           "Refactor / Cloud-Native — full re-architecture"
    },
    "Hybrid": {
        "labor_multiplier":      3.0,
        "double_run_months":     6.0,
        "description":           "Hybrid Migration — retain + modernise in parallel"
    },
}

# Baseline annual labor cost per server (used as the multiplier anchor)
BASELINE_LABOR_PER_SERVER = 2000   # $/server/year for a standard migration team

# Skill-level discounts — reduce labor multiplier for exceptional teams
SKILLED_TEAM_DISCOUNT     = 0.30   # 30% labour reduction
CICD_DISCOUNT             = 0.20   # 20% labour reduction (automated pipelines)


def calculate_migration_economics(
    strategy_key:     str,
    servers:          int,
    onprem_annual:    float,
    cloud_annual:     float,
    has_skilled_team: bool = False,
    has_cicd:         bool = False,
) -> dict:
    """
    Compute Year-1 cost including double-run period and migration labour.

    Formula:
        Cost_Year1 = (OnPrem × M/12) + Cloud_Annual + Labor_Cost

    where M = double-run overlap months and Labor is scaled per server.

    Args:
        strategy_key     : One of "Rehost", "Replatform", "Refactor", "Hybrid"
        servers          : Number of servers being migrated
        onprem_annual    : On-prem annual cost (for double-run period)
        cloud_annual     : Cloud annual cost after migration
        has_skilled_team : If True, applies 30% labour discount
        has_cicd         : If True, applies additional 20% labour discount

    Returns:
        dict with year1_total, labor_cost, double_run_cost, break_even_notes
    """
    if strategy_key not in MIGRATION_ECONOMICS:
        strategy_key = "Rehost"   # safe fallback

    econ      = MIGRATION_ECONOMICS[strategy_key]
    months    = econ["double_run_months"]
    raw_mult  = econ["labor_multiplier"]

    # Apply team-skill discounts
    total_discount = 0.0
    if has_skilled_team:
        total_discount += SKILLED_TEAM_DISCOUNT
    if has_cicd:
        total_discount += CICD_DISCOUNT
    effective_mult = raw_mult * (1.0 - min(total_discount, 0.50))  # cap discount at 50%

    labor_cost      = BASELINE_LABOR_PER_SERVER * servers * effective_mult
    double_run_cost = onprem_annual * (months / 12.0)

    year1_total = double_run_cost + cloud_annual + labor_cost

    # Simple break-even estimate: how many months until cumulative savings
    # recoup the migration premium (labor + double-run above cloud-only Year1)
    migration_premium = labor_cost + double_run_cost
    annual_saving     = onprem_annual - cloud_annual
    if annual_saving > 0:
        break_even_months = math.ceil((migration_premium / annual_saving) * 12)
    else:
        break_even_months = None   # never breaks even

    return {
        "strategy":           strategy_key,
        "labor_multiplier":   round(effective_mult, 2),
        "double_run_months":  months,
        "labor_cost":         round(labor_cost, 2),
        "double_run_cost":    round(double_run_cost, 2),
        "year1_total":        round(year1_total, 2),
        "migration_premium":  round(migration_premium, 2),
        "break_even_months":  break_even_months,
        "has_skilled_team":   has_skilled_team,
        "has_cicd":           has_cicd,
    }


# -----------------------------------------------------------------------
# Input Validation
# -----------------------------------------------------------------------

def validate_inputs(servers: float, storage_tb: float):
    """Raises ValueError if core inputs are invalid."""
    if servers <= 0:
        raise ValueError(f"Server count must be positive, got {servers}.")
    if storage_tb < 0:
        raise ValueError(f"Storage cannot be negative, got {storage_tb} TB.")


# -----------------------------------------------------------------------
# Load Infrastructure Dataset
# -----------------------------------------------------------------------

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

    total_servers  = df["Quantity"].sum()
    total_storage  = (df["Quantity"] * df["Storage (TB) per Server"]).sum()

    return df, total_servers, total_storage


# -----------------------------------------------------------------------
# Individual Cost Calculations
# -----------------------------------------------------------------------

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


def calculate_facilities_overhead(hardware_cost: float, config: FinancialConfig = DEFAULT_CONFIG) -> float:
    """
    Annual Maintenance & Facilities Overhead — the "Legacy Tax".

    Covers:
      • Data-centre power usage effectiveness (PUE) premium
      • Physical cooling plant amortisation
      • Physical security & access controls
      • Emergency hardware-swap labour (on-call SRE time)

    Typically 10–15% of total hardware CapEx per year.
    Default rate: 12% (midpoint, configurable via FinancialConfig).
    """
    return hardware_cost * config.facilities_overhead_rate


# -----------------------------------------------------------------------
# Core Cost Aggregator
# -----------------------------------------------------------------------

def calculate_annual_cost(
    servers:    float,
    storage_tb: float,
    config:     FinancialConfig = DEFAULT_CONFIG
) -> tuple[float, float, float, float]:
    """
    Computes total CapEx and annual OpEx (including facilities overhead).

    Returns:
        total_capex        — one-time hardware + storage capital expenditure
        annual_opex        — recurring yearly operational cost (incl. facilities)
        hardware_cost      — server CapEx component (exposed for reporting)
        facilities_cost    — annual facilities overhead (exposed for reporting)
    """
    # CapEx (one-time)
    hardware_cost  = calculate_hardware_cost(servers, config)
    storage_capex  = calculate_storage_hardware_cost(storage_tb, config)
    total_capex    = hardware_cost + storage_capex

    # OpEx (annual recurring)
    maintenance    = calculate_maintenance_cost(hardware_cost, config)
    power          = calculate_power_cost(servers, config)
    staff          = calculate_staff_cost(servers, config)
    storage_opex   = calculate_storage_opex(storage_tb, config)
    facilities     = calculate_facilities_overhead(hardware_cost, config)

    annual_opex    = maintenance + power + staff + storage_opex + facilities

    return total_capex, annual_opex, hardware_cost, facilities


# -----------------------------------------------------------------------
# Shared TCO Result Builder
# -----------------------------------------------------------------------

def build_tco_result(
    servers:    float,
    storage_tb: float,
    config:     FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Central function that assembles the full TCO result dict.
    Used by all input modes (file, preset, manual) to avoid duplication.
    """
    validate_inputs(servers, storage_tb)

    total_capex, annual_opex, hardware_cost, facilities_cost = calculate_annual_cost(
        servers, storage_tb, config
    )

    return {
        # Infrastructure
        "servers":     int(servers),
        "storage_tb":  float(storage_tb),

        # CapEx breakdown
        "hardware_cost":  float(hardware_cost),
        "storage_capex":  float(calculate_storage_hardware_cost(storage_tb, config)),
        "total_capex":    float(total_capex),

        # OpEx breakdown (annual)
        "annual_maintenance":     float(calculate_maintenance_cost(hardware_cost, config)),
        "annual_power":           float(calculate_power_cost(servers, config)),
        "annual_staff":           float(calculate_staff_cost(servers, config)),
        "annual_storage_opex":    float(calculate_storage_opex(storage_tb, config)),
        "annual_facilities":      float(facilities_cost),   # NEW — Legacy Tax
        "annual_operational_cost": float(annual_opex),

        # TCO projections
        "tco_3yr": float(total_capex + annual_opex * 3),
        "tco_5yr": float(total_capex + annual_opex * 5),

        # Transparency
        "facilities_overhead_rate": config.facilities_overhead_rate,
    }


# -----------------------------------------------------------------------
# Public API — Three Input Modes
# -----------------------------------------------------------------------

def calculate_onprem_tco(
    file_path: str = None,
    preset:    str = None,
    config:    FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Computes on-premise TCO from an Excel file or a named preset.
    """
    if file_path:
        _, servers, storage = load_infrastructure(file_path)
    elif preset:
        if preset not in ENTERPRISE_PRESETS:
            raise ValueError(f"Unknown preset '{preset}'. Choose from: {list(ENTERPRISE_PRESETS)}")
        preset_data = ENTERPRISE_PRESETS[preset]
        servers     = preset_data["servers"]
        storage     = preset_data["storage_tb"]
    else:
        raise ValueError("Provide either a file_path or a preset name.")

    return build_tco_result(servers, storage, config)


def calculate_manual_tco(
    servers:    float,
    storage_tb: float,
    config:     FinancialConfig = DEFAULT_CONFIG
) -> dict:
    """
    Computes on-premise TCO from manually supplied values.
    """
    return build_tco_result(servers, storage_tb, config)