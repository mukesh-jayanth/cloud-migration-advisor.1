"""
test_phase6.py
Phase 6 — Testing & Validation Suite

Covers:
  1. Cost Engine       — normal, boundary, extreme, manual verification
  2. Risk Engine       — probability math, boundary conditions, type guards
  3. Cloud Cost Engine — right-sizing formula, pricing multipliers, yearly cost
  4. Rule Engine       — all rule branches, all DR tiers, roadmap completeness
  5. Decision Engine   — confidence thresholds, strategy tiers, summary logic
  6. ML Prediction     — valid prediction, out-of-range rejection, type rejection
  7. Rule vs ML        — consistency comparison on shared scenario matrix
  8. Integration       — end-to-end pipeline with cross-engine result checks
  9. Report Generator  — both output formats contain expected sections
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Engine imports ─────────────────────────────────────────────────────────────
from engines.cost_engine import (
    calculate_manual_tco,
    calculate_onprem_tco,
    calculate_hardware_cost,
    calculate_storage_hardware_cost,
    calculate_maintenance_cost,
    calculate_power_cost,
    calculate_staff_cost,
    calculate_storage_opex,
    FinancialConfig,
    DEFAULT_CONFIG,
    ENTERPRISE_PRESETS,
)
from engines.risk_engine import calculate_risk_adjustment, risk_adjusted_tco
from engines.cloud_cost_engine import (
    calculate_yearly_cost,
    recommend_resources,
    run_cloud_analysis,
    PRICING_MODELS,
    HOURS_PER_YEAR,
    RIGHTSIZING_BUFFER,
)
from engines.rule_engine import (
    recommend_strategy as rule_recommend,
    recommend_dr,
    get_migration_roadmap,
    VALID_LEVELS,
    MIGRATION_ROADMAPS,
)
from engines.decision_engine import recommend_strategy as financial_recommend
from ml.zombie_detector import detect_zombie_servers
from ml.risk_nlp import analyze_migration_concerns
from ml.predict_strategy import calculate_failure_probability, generate_friction_report
from report_generator import generate_html_report, generate_csv_export


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _base_features(**overrides):
    """Return a valid ML feature dict, with optional overrides."""
    base = {
        "server_count":       50,
        "avg_cpu_util":       60,
        "storage_tb":         20.0,
        "downtime_tolerance": 4.0,
        "compliance_level":   2,
        "growth_rate":        15,
        "budget_sensitivity": 2,
    }
    base.update(overrides)
    return base


def _base_cloud_costs(yearly=50000):
    """Minimal cloud_costs dict matching decision_engine expectations."""
    return {
        "AWS":   {"on_demand": yearly, "reserved_1yr": yearly * 0.65,
                  "reserved_3yr": yearly * 0.45, "selected": yearly},
        "Azure": {"on_demand": yearly * 1.1, "reserved_1yr": yearly * 0.70,
                  "reserved_3yr": yearly * 0.50, "selected": yearly * 1.1},
        "GCP":   {"on_demand": yearly * 0.95, "reserved_1yr": yearly * 0.62,
                  "reserved_3yr": yearly * 0.43, "selected": yearly * 0.95},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  1. COST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestCostEngine:

    # ── Manual verification — every number checked by hand ──

    def test_hardware_cost_manual(self):
        """10 servers × $5,000 = $50,000"""
        result = calculate_hardware_cost(10, DEFAULT_CONFIG)
        assert result == 50_000.0

    def test_storage_capex_manual(self):
        """5 TB × $500/TB = $2,500"""
        result = calculate_storage_hardware_cost(5, DEFAULT_CONFIG)
        assert result == 2_500.0

    def test_maintenance_manual(self):
        """$50,000 hardware × 15% = $7,500"""
        result = calculate_maintenance_cost(50_000, DEFAULT_CONFIG)
        assert result == 7_500.0

    def test_power_manual(self):
        """10 servers × $500/server = $5,000"""
        result = calculate_power_cost(10, DEFAULT_CONFIG)
        assert result == 5_000.0

    def test_staff_cost_one_admin_boundary(self):
        """
        Fewer than 25 servers → ceil(n/25) = 1 admin → $80,000.
        Tests the max(1, ...) floor guard.
        """
        for n in [1, 10, 24, 25]:
            result = calculate_staff_cost(n, DEFAULT_CONFIG)
            assert result == 80_000.0, f"Failed for {n} servers"

    def test_staff_cost_two_admins(self):
        """26 servers → ceil(26/25) = 2 admins → $160,000"""
        result = calculate_staff_cost(26, DEFAULT_CONFIG)
        assert result == 160_000.0

    def test_storage_opex_manual(self):
        """10 TB × $150/TB = $1,500"""
        result = calculate_storage_opex(10, DEFAULT_CONFIG)
        assert result == 1_500.0

    def test_tco_3yr_formula(self):
        """3-year TCO = CapEx + (OpEx × 3). Verify against manual calculation."""
        r = calculate_manual_tco(servers=10, storage_tb=5)
        # CapEx: (10×5000) + (5×500) = 52,500
        # OpEx:  7500 + 5000 + 80000 + 750 = 93,250
        expected_capex = 52_500
        expected_opex  = 93_250
        assert r["total_capex"]             == expected_capex
        assert r["annual_operational_cost"] == expected_opex
        assert r["tco_3yr"]  == expected_capex + expected_opex * 3
        assert r["tco_5yr"]  == expected_capex + expected_opex * 5

    def test_tco_5yr_greater_than_3yr(self):
        """5-year TCO must always exceed 3-year TCO."""
        r = calculate_manual_tco(servers=20, storage_tb=10)
        assert r["tco_5yr"] > r["tco_3yr"]

    def test_all_result_keys_present(self):
        """Result dict must expose every documented key."""
        required = {
            "servers", "storage_tb", "hardware_cost", "storage_capex",
            "total_capex", "annual_maintenance", "annual_power",
            "annual_staff", "annual_storage_opex",
            "annual_operational_cost", "tco_3yr", "tco_5yr",
        }
        r = calculate_manual_tco(servers=10, storage_tb=5)
        assert required.issubset(r.keys())

    def test_all_values_non_negative(self):
        """No cost field should ever be negative."""
        r = calculate_manual_tco(servers=50, storage_tb=20)
        for key, val in r.items():
            if isinstance(val, float):
                assert val >= 0, f"{key} is negative: {val}"

    # ── Scaling ──

    def test_doubling_servers_doubles_hardware_cost(self):
        r1 = calculate_manual_tco(servers=10, storage_tb=5)
        r2 = calculate_manual_tco(servers=20, storage_tb=5)
        assert r2["hardware_cost"] == r1["hardware_cost"] * 2

    def test_doubling_servers_increases_tco(self):
        r1 = calculate_manual_tco(servers=10, storage_tb=5)
        r2 = calculate_manual_tco(servers=20, storage_tb=5)
        assert r2["tco_5yr"] > r1["tco_5yr"]

    def test_zero_storage_allowed(self):
        """Zero storage is valid (storage_tb >= 0)."""
        r = calculate_manual_tco(servers=10, storage_tb=0)
        assert r["storage_capex"]      == 0
        assert r["annual_storage_opex"] == 0

    # ── Extreme values ──

    def test_single_server(self):
        """1 server should not crash and should produce sensible output."""
        r = calculate_manual_tco(servers=1, storage_tb=1)
        assert r["servers"] == 1
        assert r["tco_5yr"] > 0

    def test_large_enterprise(self):
        """500 servers, 500 TB — should complete without error."""
        r = calculate_manual_tco(servers=500, storage_tb=500)
        assert r["servers"] == 500
        assert r["tco_5yr"] > 0

    def test_very_large_storage(self):
        """Extreme storage value should scale linearly."""
        r1 = calculate_manual_tco(servers=10, storage_tb=100)
        r2 = calculate_manual_tco(servers=10, storage_tb=200)
        diff = r2["storage_capex"] - r1["storage_capex"]
        assert diff == pytest.approx(100 * DEFAULT_CONFIG.storage_hardware_cost_per_tb)

    # ── Validation guards ──

    def test_zero_servers_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_manual_tco(servers=0, storage_tb=5)

    def test_negative_servers_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_manual_tco(servers=-5, storage_tb=5)

    def test_negative_storage_raises(self):
        with pytest.raises(ValueError, match="negative"):
            calculate_manual_tco(servers=10, storage_tb=-1)

    # ── Presets ──

    def test_all_presets_return_valid_results(self):
        for preset_name in ENTERPRISE_PRESETS:
            r = calculate_onprem_tco(preset=preset_name)
            assert r["servers"] == ENTERPRISE_PRESETS[preset_name]["servers"]
            assert r["tco_5yr"] > 0

    def test_preset_ordering_small_lt_medium_lt_large(self):
        """Larger presets must always cost more."""
        rs = calculate_onprem_tco(preset="small")
        rm = calculate_onprem_tco(preset="medium")
        rl = calculate_onprem_tco(preset="large")
        assert rs["tco_5yr"] < rm["tco_5yr"] < rl["tco_5yr"]

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            calculate_onprem_tco(preset="enterprise")

    def test_no_input_raises(self):
        with pytest.raises(ValueError):
            calculate_onprem_tco()

    # ── Custom FinancialConfig ──

    def test_custom_config_higher_salary_increases_tco(self):
        cheap_cfg    = FinancialConfig(admin_salary=50_000)
        expensive_cfg = FinancialConfig(admin_salary=150_000)
        r_cheap    = calculate_manual_tco(servers=50, storage_tb=20, config=cheap_cfg)
        r_expensive = calculate_manual_tco(servers=50, storage_tb=20, config=expensive_cfg)
        assert r_expensive["tco_5yr"] > r_cheap["tco_5yr"]

    def test_zero_maintenance_rate_gives_zero_maintenance(self):
        cfg = FinancialConfig(maintenance_rate=0.0)
        r   = calculate_manual_tco(servers=10, storage_tb=5, config=cfg)
        assert r["annual_maintenance"] == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  2. RISK ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskEngine:

    # ── Manual verification ──

    def test_expected_value_formula_manual(self):
        """
        downtime:   0.10 × 50,000 = 5,000
        compliance: 0.05 × 100,000 = 5,000
        skill:      0.20 × 15,000 = 3,000
        total = 13,000
        (matches docstring example exactly)
        """
        r = calculate_risk_adjustment(
            downtime_risk=0.10,   downtime_cost=50_000,
            compliance_risk=0.05, compliance_penalty=100_000,
            skill_risk=0.20,      training_cost=15_000,
        )
        assert r["downtime_cost"]   == pytest.approx(5_000.0)
        assert r["compliance_cost"] == pytest.approx(5_000.0)
        assert r["skill_cost"]      == pytest.approx(3_000.0)
        assert r["total_risk_cost"] == pytest.approx(13_000.0)

    def test_total_equals_sum_of_components(self):
        """total_risk_cost must always equal the sum of its three components."""
        r = calculate_risk_adjustment(0.3, 20000, 0.1, 80000, 0.5, 10000)
        expected = r["downtime_cost"] + r["compliance_cost"] + r["skill_cost"]
        assert r["total_risk_cost"] == pytest.approx(expected)

    def test_zero_probability_gives_zero_cost(self):
        """Zero risk probability → zero expected cost for that component."""
        r = calculate_risk_adjustment(0.0, 100000, 0.1, 50000, 0.2, 10000)
        assert r["downtime_cost"] == 0.0

    def test_probability_one_gives_full_cost(self):
        """Probability of 1.0 → expected cost equals the full cost."""
        r = calculate_risk_adjustment(1.0, 99999, 0.0, 0, 0.0, 0)
        assert r["downtime_cost"] == pytest.approx(99999.0)

    def test_all_zeros_gives_zero_total(self):
        r = calculate_risk_adjustment(0.0, 0, 0.0, 0, 0.0, 0)
        assert r["total_risk_cost"] == 0.0

    def test_all_max_gives_sum_of_costs(self):
        r = calculate_risk_adjustment(1.0, 50000, 1.0, 100000, 1.0, 20000)
        assert r["total_risk_cost"] == pytest.approx(170_000.0)

    # ── risk_adjusted_tco ──

    def test_adjusted_tco_equals_base_plus_risk(self):
        risk = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
        base  = 200_000
        adj   = risk_adjusted_tco(base, risk)
        assert adj == pytest.approx(base + risk["total_risk_cost"])

    def test_zero_risk_adjusted_tco_equals_base(self):
        risk = calculate_risk_adjustment(0.0, 0, 0.0, 0, 0.0, 0)
        adj  = risk_adjusted_tco(100_000, risk)
        assert adj == pytest.approx(100_000.0)

    def test_adjusted_tco_always_gte_base(self):
        """Risk can only add cost, never subtract it."""
        risk = calculate_risk_adjustment(0.3, 30000, 0.1, 60000, 0.4, 15000)
        base = 300_000
        assert risk_adjusted_tco(base, risk) >= base

    # ── Boundary values ──

    def test_risk_probability_boundary_zero(self):
        r = calculate_risk_adjustment(0.0, 10000, 0.0, 10000, 0.0, 10000)
        assert r["total_risk_cost"] == 0.0

    def test_risk_probability_boundary_one(self):
        r = calculate_risk_adjustment(1.0, 10000, 1.0, 10000, 1.0, 10000)
        assert r["total_risk_cost"] == pytest.approx(30_000.0)

    def test_cost_boundary_zero(self):
        r = calculate_risk_adjustment(0.5, 0, 0.5, 0, 0.5, 0)
        assert r["total_risk_cost"] == 0.0

    # ── Validation guards ──

    def test_probability_above_1_raises(self):
        with pytest.raises(ValueError, match="probability"):
            calculate_risk_adjustment(1.1, 50000, 0.0, 0, 0.0, 0)

    def test_probability_below_0_raises(self):
        with pytest.raises(ValueError, match="probability"):
            calculate_risk_adjustment(-0.1, 50000, 0.0, 0, 0.0, 0)

    def test_negative_cost_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_risk_adjustment(0.1, -1000, 0.0, 0, 0.0, 0)

    def test_string_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_risk_adjustment("high", 50000, 0.05, 100000, 0.2, 20000)

    def test_none_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_risk_adjustment(None, 50000, 0.05, 100000, 0.2, 20000)

    def test_adjusted_tco_negative_base_raises(self):
        risk = calculate_risk_adjustment(0.1, 10000, 0.0, 0, 0.0, 0)
        with pytest.raises(ValueError, match="non-negative"):
            risk_adjusted_tco(-1000, risk)

    def test_adjusted_tco_wrong_dict_key_raises(self):
        with pytest.raises(ValueError, match="total_risk_cost"):
            risk_adjusted_tco(100_000, {"wrong_key": 5000})


# ══════════════════════════════════════════════════════════════════════════════
#  3. CLOUD COST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestCloudCostEngine:

    # ── Yearly cost formula — manual verification ──

    def test_yearly_cost_formula_manual(self):
        """
        price=$0.192/hr, 10 servers, on_demand:
        0.192 × 8760 × 10 × 1.00 = 16,819.20
        """
        result = calculate_yearly_cost(0.192, 10, "on_demand")
        assert result == pytest.approx(0.192 * 8760 * 10 * 1.00)

    def test_reserved_1yr_discount(self):
        """Reserved 1yr = 65% of on-demand."""
        base     = calculate_yearly_cost(0.192, 10, "on_demand")
        reserved = calculate_yearly_cost(0.192, 10, "reserved_1yr")
        assert reserved == pytest.approx(base * 0.65)

    def test_reserved_3yr_discount(self):
        """Reserved 3yr = 45% of on-demand."""
        base     = calculate_yearly_cost(0.192, 10, "on_demand")
        reserved = calculate_yearly_cost(0.192, 10, "reserved_3yr")
        assert reserved == pytest.approx(base * 0.45)

    def test_pricing_model_ordering(self):
        """on_demand > reserved_1yr > reserved_3yr always."""
        od  = calculate_yearly_cost(0.384, 5, "on_demand")
        r1  = calculate_yearly_cost(0.384, 5, "reserved_1yr")
        r3  = calculate_yearly_cost(0.384, 5, "reserved_3yr")
        assert od > r1 > r3

    def test_invalid_pricing_model_raises(self):
        with pytest.raises(ValueError, match="pricing_model"):
            calculate_yearly_cost(0.192, 5, "spot")

    def test_doubling_servers_doubles_cost(self):
        c1 = calculate_yearly_cost(0.384, 5,  "on_demand")
        c2 = calculate_yearly_cost(0.384, 10, "on_demand")
        assert c2 == pytest.approx(c1 * 2)

    def test_zero_servers_gives_zero_cost(self):
        result = calculate_yearly_cost(0.384, 0, "on_demand")
        assert result == pytest.approx(0.0)

    # ── Right-sizing formula — manual verification ──

    def test_right_sizing_formula_manual(self):
        """
        8 vCPU, 32 GB, 50% CPU util, 50% RAM util, safety_buffer=1.3
        required_cpu = 8 × 0.5 × 1.3 = 5.2 → ceil = 6
        required_ram = 32 × 0.5 × 1.3 = 20.8 → nearest std = 16 or 32
        """
        vcpu, ram = recommend_resources(8, 32, 50, 50)
        assert vcpu == math.ceil(8 * 0.5 * RIGHTSIZING_BUFFER)

    def test_right_sizing_low_utilisation_reduces_resources(self):
        """Low utilisation should recommend fewer resources than current."""
        vcpu, ram = recommend_resources(16, 64, 20, 20)
        assert vcpu < 16
        assert ram < 64

    def test_right_sizing_high_utilisation_keeps_resources(self):
        """High utilisation + safety buffer keeps resource count similar."""
        vcpu, ram = recommend_resources(8, 32, 90, 90)
        # 8 × 0.9 × 1.3 = 9.36 → ceil = 10, but capped by cloud sizes
        assert vcpu >= 8

    def test_right_sizing_ram_snaps_to_standard_sizes(self):
        """RAM output must always be one of the standard cloud sizes."""
        standard = {1, 2, 4, 8, 16, 32, 64, 128}
        for util in [20, 40, 60, 80]:
            _, ram = recommend_resources(8, 32, util, util)
            assert ram in standard, f"RAM {ram} not in standard sizes for util={util}"

    # ── Full pipeline ──

    def test_run_cloud_analysis_returns_all_providers(self):
        result = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
        assert set(result["instances"].keys()) == {"AWS", "Azure", "GCP"}
        assert set(result["costs"].keys())     == {"AWS", "Azure", "GCP"}

    def test_run_cloud_analysis_best_provider_has_lowest_cost(self):
        result = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
        bp     = result["best_provider"]
        bp_cost = result["costs"][bp]["selected"]
        for prov, cdata in result["costs"].items():
            assert cdata["selected"] >= bp_cost, \
                f"{prov} (${cdata['selected']}) cheaper than best {bp} (${bp_cost})"

    def test_run_cloud_analysis_all_pricing_models_in_output(self):
        result = run_cloud_analysis(4, 16, 50, 50, 5, "reserved_1yr")
        for prov, cdata in result["costs"].items():
            for model in PRICING_MODELS:
                assert model in cdata, f"Missing {model} for {prov}"
            assert "selected" in cdata

    def test_run_cloud_analysis_reserved_cheaper_than_on_demand(self):
        r_od  = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
        r_res = run_cloud_analysis(8, 32, 60, 70, 10, "reserved_3yr")
        bp_od  = r_od["best_provider"]
        bp_res = r_res["best_provider"]
        # Best reserved cost must be less than best on-demand cost
        assert r_res["costs"][bp_res]["selected"] < r_od["costs"][bp_od]["selected"]

    def test_run_cloud_analysis_reduction_pct_non_negative(self):
        result = run_cloud_analysis(8, 32, 30, 40, 5, "on_demand")
        assert result["cpu_reduction_pct"] >= 0
        assert result["ram_reduction_pct"] >= 0

    def test_invalid_utilisation_raises(self):
        with pytest.raises(ValueError):
            run_cloud_analysis(8, 32, 0, 70, 10)   # cpu_util=0 invalid

    def test_zero_servers_raises(self):
        with pytest.raises(ValueError):
            run_cloud_analysis(8, 32, 60, 70, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  4. RULE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestRuleEngine:

    # ── Strategy — every rule branch ──

    def test_hybrid_when_high_compliance_and_low_downtime(self):
        """Rule 1: high compliance + low downtime → Hybrid Migration"""
        assert rule_recommend("high", "low", "medium") == "Hybrid Migration"

    def test_hybrid_overrides_growth_when_compliance_high_downtime_low(self):
        """Rule 1 takes priority over Rule 2 (growth)."""
        assert rule_recommend("high", "low", "high") == "Hybrid Migration"

    def test_cloud_native_when_high_growth(self):
        """Rule 2: high growth (non-rule-1 combo) → Cloud-Native Migration"""
        assert rule_recommend("low",    "medium", "high") == "Cloud-Native Migration"
        assert rule_recommend("medium", "high",   "high") == "Cloud-Native Migration"
        assert rule_recommend("medium", "low",    "high") == "Cloud-Native Migration"

    def test_lift_and_shift_as_default(self):
        """Rule 3 fallback covers all remaining combinations."""
        assert rule_recommend("low",    "low",    "low")    == "Lift-and-Shift"
        assert rule_recommend("low",    "medium", "low")    == "Lift-and-Shift"
        assert rule_recommend("medium", "medium", "medium") == "Lift-and-Shift"
        assert rule_recommend("low",    "high",   "medium") == "Lift-and-Shift"
        assert rule_recommend("high",   "medium", "medium") == "Lift-and-Shift"

    def test_all_valid_level_combinations_do_not_crash(self):
        """Every possible (3×3×3 = 27) combination must return a valid strategy."""
        valid_strategies = {"Lift-and-Shift", "Hybrid Migration", "Cloud-Native Migration"}
        for c in VALID_LEVELS:
            for d in VALID_LEVELS:
                for g in VALID_LEVELS:
                    result = rule_recommend(c, d, g)
                    assert result in valid_strategies, f"Invalid strategy for ({c},{d},{g}): {result}"

    # ── Strategy — type & value guards ──

    def test_integer_compliance_raises_type_error(self):
        with pytest.raises(TypeError):
            rule_recommend(1, "low", "low")

    def test_invalid_level_string_raises_value_error(self):
        with pytest.raises(ValueError, match="must be one of"):
            rule_recommend("extreme", "low", "low")

    def test_uppercase_level_normalised(self):
        """_validate_level lowercases input — 'HIGH' should work."""
        assert rule_recommend("HIGH", "LOW", "MEDIUM") == "Hybrid Migration"

    def test_whitespace_level_normalised(self):
        """Leading/trailing whitespace should be stripped."""
        assert rule_recommend("  high  ", "  low  ", "  medium  ") == "Hybrid Migration"

    # ── DR tiers — all three branches ──

    def test_dr_low_downtime_gives_hot_dr(self):
        assert recommend_dr("low") == "Hot DR"

    def test_dr_medium_downtime_gives_warm_dr(self):
        assert recommend_dr("medium") == "Warm DR"

    def test_dr_high_downtime_gives_cold_dr(self):
        assert recommend_dr("high") == "Cold DR"

    def test_dr_invalid_raises(self):
        with pytest.raises(ValueError):
            recommend_dr("extreme")

    def test_dr_integer_raises(self):
        with pytest.raises(TypeError):
            recommend_dr(0)

    # ── Roadmap ──

    def test_each_strategy_has_exactly_five_roadmap_phases(self):
        for strategy, roadmap in MIGRATION_ROADMAPS.items():
            assert len(roadmap) == 5, f"{strategy} has {len(roadmap)} phases, expected 5"

    def test_roadmap_phases_are_non_empty_strings(self):
        for strategy, roadmap in MIGRATION_ROADMAPS.items():
            for phase in roadmap:
                assert isinstance(phase, str) and len(phase) > 0

    def test_get_migration_roadmap_returns_list(self):
        for strategy in MIGRATION_ROADMAPS:
            result = get_migration_roadmap(strategy)
            assert isinstance(result, list)
            assert len(result) == 5

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_migration_roadmap("Stay Put")

    def test_roadmap_integer_raises(self):
        with pytest.raises(TypeError):
            get_migration_roadmap(42)


# ══════════════════════════════════════════════════════════════════════════════
#  5. DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionEngine:

    def _run(self, onprem_cost, cloud_yearly, model="on_demand"):
        costs = _base_cloud_costs(cloud_yearly)
        return financial_recommend(onprem_cost, costs, model)

    # ── Confidence thresholds — manual verification ──

    def test_high_confidence_when_cloud_saves_more_than_20pct(self):
        """Cloud at $60k vs on-prem $80k → 25% saving → High confidence."""
        result = self._run(80_000, 60_000)
        aws = result["AWS"]
        assert aws["savings_pct"] == pytest.approx(25.0)
        assert aws["confidence"]  == "High"

    def test_medium_confidence_at_10pct_saving(self):
        """10% saving → Medium confidence."""
        result = self._run(100_000, 90_000)
        aws = result["AWS"]
        assert aws["savings_pct"] == pytest.approx(10.0)
        assert aws["confidence"]  == "Medium"

    def test_low_confidence_at_3pct_saving(self):
        """3% saving → Low confidence."""
        result = self._run(100_000, 97_000)
        aws = result["AWS"]
        assert aws["confidence"] == "Low"

    def test_stay_on_prem_when_cloud_is_more_expensive(self):
        """Cloud more expensive → Stay On-Prem."""
        result = self._run(50_000, 70_000)
        aws = result["AWS"]
        assert aws["recommendation"] == "Stay On-Prem"
        assert aws["confidence"]     == "Stay On-Prem"
        assert aws["savings"]        < 0

    # ── Strategy tiers ──

    def test_full_migration_above_20pct_saving(self):
        result = self._run(100_000, 70_000)   # 30% saving
        assert result["AWS"]["strategy"] == "Full Migration"

    def test_hybrid_migration_between_5_and_20pct(self):
        result = self._run(100_000, 88_000)   # 12% saving
        assert result["AWS"]["strategy"] == "Hybrid Migration"

    def test_selective_migration_between_0_and_5pct(self):
        result = self._run(100_000, 97_000)   # 3% saving
        assert result["AWS"]["strategy"] == "Selective Migration"

    def test_stay_on_prem_strategy_when_no_saving(self):
        result = self._run(100_000, 110_000)
        assert result["AWS"]["strategy"] == "Stay On-Prem"

    # ── Summary ──

    def test_summary_key_present(self):
        result = self._run(80_000, 60_000)
        assert "_summary" in result

    def test_summary_migrate_when_savings_exist(self):
        result  = self._run(100_000, 70_000)
        summary = result["_summary"]
        assert summary["overall_recommendation"] == "Migrate to Cloud"
        assert summary["best_cloud_option"] is not None

    def test_summary_stay_when_all_providers_expensive(self):
        """If all providers exceed on-prem, summary recommends staying."""
        costs = {
            "AWS":   {"on_demand": 120_000, "reserved_1yr": 78_000,
                      "reserved_3yr": 54_000, "selected": 120_000},
            "Azure": {"on_demand": 130_000, "reserved_1yr": 84_500,
                      "reserved_3yr": 58_500, "selected": 130_000},
            "GCP":   {"on_demand": 125_000, "reserved_1yr": 81_250,
                      "reserved_3yr": 56_250, "selected": 125_000},
        }
        result  = financial_recommend(100_000, costs)
        summary = result["_summary"]
        assert summary["overall_recommendation"] == "Stay On-Prem"

    # ── Validation guards ──

    def test_zero_onprem_cost_raises(self):
        with pytest.raises(ValueError):
            financial_recommend(0, _base_cloud_costs(50_000))

    def test_negative_onprem_cost_raises(self):
        with pytest.raises(ValueError):
            financial_recommend(-1, _base_cloud_costs(50_000))

    def test_invalid_pricing_model_raises(self):
        with pytest.raises(ValueError, match="pricing_model"):
            financial_recommend(80_000, _base_cloud_costs(60_000), pricing_model="spot")

    # ── All-pricing keys in output ──

    def test_all_pricing_keys_in_per_provider_result(self):
        result = self._run(80_000, 60_000)
        for prov in ("AWS", "Azure", "GCP"):
            assert "all_pricing" in result[prov]
            for model in PRICING_MODELS:
                assert model in result[prov]["all_pricing"]


# ══════════════════════════════════════════════════════════════════════════════
#  6. ZOMBIE SERVER DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestZombieDetector:

    def test_detects_zombie_high_ram_low_util(self):
        result = detect_zombie_servers([
            {"name": "db-01", "ram_gb": 128, "vcpu": 32, "cpu_util_pct": 1.2},
        ])
        assert result["zombie_count"] == 1
        assert result["zombies"][0]["severity"] in ("Critical", "High")

    def test_no_zombie_when_utilisation_healthy(self):
        result = detect_zombie_servers([
            {"name": "web-01", "ram_gb": 16, "vcpu": 4, "cpu_util_pct": 65.0},
        ])
        assert result["zombie_count"] == 0
        assert result["inventory_integrity"] == "CLEAN"

    def test_multiple_zombies_returns_warning_or_critical(self):
        result = detect_zombie_servers([
            {"name": "z1", "ram_gb": 64, "vcpu": 16, "cpu_util_pct": 2.0},
            {"name": "z2", "ram_gb": 32, "vcpu": 8,  "cpu_util_pct": 3.0},
            {"name": "ok", "ram_gb": 8,  "vcpu": 2,  "cpu_util_pct": 80.0},
        ])
        assert result["zombie_count"] == 2
        assert result["inventory_integrity"] in ("WARNING", "CRITICAL")

    def test_empty_server_list(self):
        result = detect_zombie_servers([])
        assert result["zombie_count"] == 0
        assert result["total_servers"] == 0

    def test_potential_savings_pct_non_negative(self):
        result = detect_zombie_servers([
            {"name": "s1", "ram_gb": 64, "vcpu": 8, "cpu_util_pct": 1.0},
        ])
        assert result["potential_savings_pct"] >= 0

    def test_zombie_has_recommendation(self):
        result = detect_zombie_servers([
            {"name": "db-01", "ram_gb": 128, "vcpu": 32, "cpu_util_pct": 0.5},
        ])
        assert result["zombie_count"] == 1
        assert len(result["zombies"][0]["recommendation"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
#  7. NLP RISK CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

class TestNLPRiskClassifier:

    def test_detects_data_security_concerns(self):
        result = analyze_migration_concerns("worried about data breaches and GDPR")
        labels = [c["label"] for c in result["detected_categories"]]
        assert "Data Security & Compliance" in labels

    def test_detects_skill_gap_concerns(self):
        result = analyze_migration_concerns("our team has no Kubernetes experience")
        labels = [c["label"] for c in result["detected_categories"]]
        assert "Skill Gap & Team Readiness" in labels

    def test_detects_multiple_categories(self):
        text = "budget is tight, worried about data loss, team needs training, delays are likely"
        result = analyze_migration_concerns(text, cloud_annual=100000)
        assert len(result["detected_categories"]) >= 3
        assert result["risk_score"] >= 3

    def test_empty_text_returns_no_risk(self):
        result = analyze_migration_concerns("")
        assert result["risk_level"] == "None"
        assert result["detected_categories"] == []

    def test_no_keywords_returns_empty(self):
        result = analyze_migration_concerns("The weather is nice today")
        assert result["detected_categories"] == []

    def test_probability_adjustments_structure(self):
        result = analyze_migration_concerns("worried about skill gap and downtime")
        adj = result["probability_adjustments"]
        assert isinstance(adj, dict)
        for field, val in adj.items():
            assert 0 < val <= 0.90

    def test_financial_penalty_scales_with_cloud_cost(self):
        r1 = analyze_migration_concerns("data breach risk", cloud_annual=100000)
        r2 = analyze_migration_concerns("data breach risk", cloud_annual=500000)
        assert r2["total_penalty"] > r1["total_penalty"]

    def test_zero_cloud_cost_gives_zero_penalty(self):
        result = analyze_migration_concerns("budget concerns", cloud_annual=0)
        assert result["total_penalty"] == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  7b. FAILURE PROBABILITY PREDICTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestFailureProbability:

    def test_low_risk_strategy_with_good_conditions(self):
        fp = calculate_failure_probability(
            strategy="Lift-and-Shift", budget_level="high",
            servers=10, annual_saving=50000,
        )
        assert fp["risk_tier"] == "Low"
        assert fp["final_probability"] < 0.15

    def test_high_risk_cloud_native_low_budget(self):
        fp = calculate_failure_probability(
            strategy="Cloud-Native Migration", budget_level="low",
            servers=100, migration_premium=500000, annual_saving=20000,
            zombie_count=3, nlp_risk_score=8,
        )
        assert fp["risk_tier"] in ("High", "Critical")
        assert fp["final_probability"] >= 0.35

    def test_skilled_team_reduces_probability(self):
        base = calculate_failure_probability(
            strategy="Hybrid Migration", budget_level="medium", servers=30,
        )
        with_team = calculate_failure_probability(
            strategy="Hybrid Migration", budget_level="medium", servers=30,
            has_skilled_team=True,
        )
        assert with_team["final_probability"] < base["final_probability"]

    def test_negative_roi_increases_risk(self):
        fp = calculate_failure_probability(
            strategy="Lift-and-Shift", budget_level="medium",
            servers=20, migration_premium=100000, annual_saving=-5000,
        )
        assert any("Negative ROI" in a["factor"] for a in fp["adjustments"])

    def test_probability_clamped_between_bounds(self):
        fp = calculate_failure_probability(
            strategy="Cloud-Native Migration", budget_level="low",
            servers=500, migration_premium=2000000, annual_saving=-50000,
            zombie_count=10, nlp_risk_score=20,
        )
        assert 0.02 <= fp["final_probability"] <= 0.95

    def test_verdict_is_non_empty_string(self):
        fp = calculate_failure_probability(
            strategy="Lift-and-Shift", budget_level="medium", servers=10,
        )
        assert isinstance(fp["verdict"], str) and len(fp["verdict"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
#  8. INTEGRATION — END-TO-END PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """
    End-to-end tests that chain multiple engines together and cross-check
    results — e.g. verifying that cloud savings are consistent across
    the cost engine and decision engine outputs.
    """

    @pytest.fixture(scope="class")
    def full_result(self):
        tco   = calculate_manual_tco(servers=20, storage_tb=10)
        cloud = run_cloud_analysis(8, 32, 60, 70, 20, "on_demand")
        risk  = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
        adj   = risk_adjusted_tco(cloud["costs"][cloud["best_provider"]]["selected"], risk)
        dec   = financial_recommend(
            tco["annual_operational_cost"], cloud["costs"], "on_demand"
        )
        return {"tco": tco, "cloud": cloud, "risk": risk,
                "adj_cost": adj, "decision": dec}

    def test_best_provider_savings_match_decision_engine(self, full_result):
        """
        Decision engine savings = on-prem - cloud.
        Cross-check with raw values from cost and cloud engines.
        """
        tco     = full_result["tco"]
        cloud   = full_result["cloud"]
        dec     = full_result["decision"]
        bp      = cloud["best_provider"]
        cloud_y = cloud["costs"][bp]["selected"]
        onp_y   = tco["annual_operational_cost"]

        expected_saving = onp_y - cloud_y
        assert dec[bp]["savings"] == pytest.approx(expected_saving, rel=1e-6)

    def test_risk_adjusted_cost_exceeds_base_cloud_cost(self, full_result):
        cloud   = full_result["cloud"]
        bp      = cloud["best_provider"]
        base    = cloud["costs"][bp]["selected"]
        adj     = full_result["adj_cost"]
        assert adj >= base

    def test_decision_summary_best_provider_matches_cloud_engine(self, full_result):
        """The decision engine's best provider must match the cloud engine's."""
        cloud   = full_result["cloud"]
        dec     = full_result["decision"]
        summary = dec["_summary"]
        if summary["overall_recommendation"] == "Migrate to Cloud":
            assert summary["best_cloud_option"] == cloud["best_provider"]

    def test_tco_5yr_consistent_with_annual_opex(self, full_result):
        """5yr TCO = CapEx + (OpEx × 5) — verified against raw fields."""
        tco = full_result["tco"]
        expected = tco["total_capex"] + tco["annual_operational_cost"] * 5
        assert tco["tco_5yr"] == pytest.approx(expected)

    def test_pipeline_with_small_preset(self):
        """Small preset → full pipeline should complete without error."""
        tco   = calculate_onprem_tco(preset="small")
        cloud = run_cloud_analysis(4, 16, 30, 40, tco["servers"], "on_demand")
        risk  = calculate_risk_adjustment(0.05, 20000, 0.02, 50000, 0.1, 10000)
        adj   = risk_adjusted_tco(cloud["costs"][cloud["best_provider"]]["selected"], risk)
        strat_result = rule_recommend("low", "high", "low")
        strat = strat_result["strategy"] if isinstance(strat_result, dict) else strat_result
        fp    = calculate_failure_probability(
            strategy=strat, budget_level="low", servers=tco["servers"]
        )
        assert tco["tco_5yr"] > 0
        assert adj > 0
        assert strat == "Lift-and-Shift"
        assert fp["final_probability"] >= 0.02

    def test_pipeline_with_large_preset(self):
        """Large preset → full pipeline should complete without error."""
        tco   = calculate_onprem_tco(preset="large")
        cloud = run_cloud_analysis(16, 64, 45, 50, min(tco["servers"], 200), "reserved_1yr")
        risk  = calculate_risk_adjustment(0.15, 200000, 0.10, 500000, 0.25, 80000)
        adj   = risk_adjusted_tco(cloud["costs"][cloud["best_provider"]]["selected"], risk)
        strat_result = rule_recommend("high", "low", "medium")
        strat = strat_result["strategy"] if isinstance(strat_result, dict) else strat_result
        assert tco["tco_5yr"] > 0
        assert adj > 0
        assert strat == "Hybrid Migration"


# ══════════════════════════════════════════════════════════════════════════════
#  9. REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class TestReportGenerator:

    @pytest.fixture(scope="class")
    def full_report_data(self):
        tco   = calculate_manual_tco(servers=20, storage_tb=10)
        cloud = run_cloud_analysis(8, 32, 60, 70, 20, "on_demand")
        risk_raw = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
        adj      = risk_adjusted_tco(cloud["costs"][cloud["best_provider"]]["selected"], risk_raw)
        strat_result = rule_recommend("medium", "medium", "high")
        strat    = strat_result["strategy"] if isinstance(strat_result, dict) else strat_result
        dr       = recommend_dr("medium")
        rm       = get_migration_roadmap(strat)
        fp = calculate_failure_probability(
            strategy=strat, budget_level="medium", servers=20
        )

        return {
            "org_name":      "Test Corp",
            "pricing_model": "on_demand",
            "tco":    tco,
            "cloud":  cloud,
            "risk": {
                "risk": risk_raw, "adj_cloud_cost": adj,
                "inputs": {
                    "downtime_risk": 0.1, "downtime_cost": 50000,
                    "compliance_risk": 0.05, "compliance_penalty": 100000,
                    "skill_risk": 0.2, "training_cost": 20000,
                }
            },
            "strategy": {
                "strategy": strat, "dr_plan": dr, "roadmap": rm,
                "inputs": {"compliance": "medium", "downtime": "medium", "growth": "high"}
            },
            "ml": {
                "friction_risk": "Medium",
                "friction_narrative": "Test narrative",
                "warnings": [],
                "failure_probability": fp["final_probability"],
                "failure_tier": fp["risk_tier"],
                "failure_verdict": fp["verdict"],
                "zombie_count": 0,
                "waste_pct": 0,
            },
        }

    # ── HTML report ──

    def test_html_report_is_string(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert isinstance(html, str)

    def test_html_report_minimum_length(self, full_report_data):
        """A full report must be at least 10,000 chars."""
        html = generate_html_report(full_report_data)
        assert len(html) >= 10_000

    def test_html_report_contains_org_name(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert "Test Corp" in html

    def test_html_report_contains_all_phase_headings(self, full_report_data):
        html = generate_html_report(full_report_data)
        for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]:
            assert phase in html, f"Missing heading: {phase}"

    def test_html_report_contains_executive_summary(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert "Executive Summary" in html

    def test_html_report_contains_migration_roadmap(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert "Migration Roadmap" in html

    def test_html_report_contains_ml_section(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert "Phase 5" in html

    def test_html_report_is_valid_html(self, full_report_data):
        html = generate_html_report(full_report_data)
        assert html.strip().startswith("<!DOCTYPE html")
        assert "</html>" in html

    def test_html_report_with_partial_data(self):
        """Report with only Phase 1 data should still render without error."""
        tco  = calculate_manual_tco(servers=10, storage_tb=5)
        data = {
            "org_name": "Partial Corp", "pricing_model": "on_demand",
            "tco": tco, "cloud": None, "risk": None,
            "strategy": None, "ml": None,
        }
        html = generate_html_report(data)
        assert "Partial Corp" in html
        assert "Phase 1" in html

    # ── CSV export ──

    def test_csv_export_is_string(self, full_report_data):
        csv = generate_csv_export(full_report_data)
        assert isinstance(csv, str)

    def test_csv_export_minimum_length(self, full_report_data):
        csv = generate_csv_export(full_report_data)
        assert len(csv) >= 500

    def test_csv_export_contains_all_phase_headers(self, full_report_data):
        csv = generate_csv_export(full_report_data)
        for phase in ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]:
            assert phase in csv, f"Missing CSV section: {phase}"

    def test_csv_export_contains_org_name(self, full_report_data):
        csv = generate_csv_export(full_report_data)
        assert "Test Corp" in csv

    def test_csv_export_is_parseable(self, full_report_data):
        """CSV must be parseable by Python's csv module."""
        import csv as csv_module, io
        raw = generate_csv_export(full_report_data)
        reader = csv_module.reader(io.StringIO(raw))
        rows   = list(reader)
        assert len(rows) > 10

    def test_csv_export_contains_key_metrics(self, full_report_data):
        csv = generate_csv_export(full_report_data)
        for metric in ["5-Year TCO", "Best Provider", "Total Risk Cost",
                       "Recommended Strategy"]:
            assert metric in csv, f"Missing CSV metric: {metric}"
