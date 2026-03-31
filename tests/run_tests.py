"""
run_tests.py
Phase 6 — Standalone Test Runner

Executes all Phase 6 tests without requiring pytest.
Run with:  python tests/run_tests.py   (from project root)
           python run_tests.py          (from tests/ folder)

Exit code: 0 = all passed, 1 = one or more failures
"""

import sys
import os
import math
import time
import csv as csv_mod
import io

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

# ══════════════════════════════════════════════════════════════════════════════
#  MINI TEST FRAMEWORK
# ══════════════════════════════════════════════════════════════════════════════

class _Results:
    def __init__(self):
        self.passed  = []
        self.failed  = []
        self.current = ""

    def ok(self, name, ms):
        self.passed.append(name)
        print(f"  \u2705  {name:<64} ({ms:.0f}ms)")

    def fail(self, name, msg, ms):
        self.failed.append((name, msg))
        print(f"  \u274c  {name:<64} ({ms:.0f}ms)")
        print(f"       \u2192 {msg}")

    def suite(self, title):
        self.current = title
        print(f"\n{'─'*70}")
        print(f"  {title}")
        print(f"{'─'*70}")

    def report(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'═'*70}")
        print(f"  PHASE 6 — TEST RESULTS")
        print(f"{'═'*70}")
        print(f"  Total  : {total}")
        print(f"  Passed : {len(self.passed)} \u2705")
        print(f"  Failed : {len(self.failed)} {'❌' if self.failed else '✅'}")
        if self.failed:
            print(f"\n  FAILURES:")
            for name, msg in self.failed:
                print(f"    ✗ {name}")
                print(f"      {msg}")
        print(f"{'═'*70}\n")
        return 1 if self.failed else 0


R = _Results()


def run(name: str, fn):
    t0 = time.perf_counter()
    try:
        fn()
        R.ok(name, (time.perf_counter() - t0) * 1000)
    except AssertionError as e:
        R.fail(name, str(e) or "Assertion failed",
               (time.perf_counter() - t0) * 1000)
    except Exception as e:
        R.fail(name, f"{type(e).__name__}: {e}",
               (time.perf_counter() - t0) * 1000)


def approx(a, b, rel=1e-6):
    tol = abs(b) * rel if b != 0 else 1e-9
    if abs(a - b) > tol:
        raise AssertionError(f"{a} ≉ {b} (tolerance {rel*100:.4f}%)")


def raises(exc, fn, match=""):
    try:
        fn()
        raise AssertionError(f"Expected {exc.__name__} but nothing raised")
    except exc as e:
        if match and match.lower() not in str(e).lower():
            raise AssertionError(
                f"{exc.__name__} raised but '{match}' not in: {e}")
    except AssertionError:
        raise
    except Exception as e:
        raise AssertionError(
            f"Expected {exc.__name__} but got {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE IMPORTS
# ══════════════════════════════════════════════════════════════════════════════

from engines.cost_engine import (
    calculate_manual_tco, calculate_onprem_tco,
    calculate_hardware_cost, calculate_storage_hardware_cost,
    calculate_maintenance_cost, calculate_power_cost,
    calculate_staff_cost, calculate_storage_opex,
    FinancialConfig, DEFAULT_CONFIG, ENTERPRISE_PRESETS,
)
from engines.risk_engine import calculate_risk_adjustment, risk_adjusted_tco
from engines.cloud_cost_engine import (
    calculate_yearly_cost, recommend_resources, run_cloud_analysis,
    PRICING_MODELS, HOURS_PER_YEAR, SAFETY_BUFFER,
)
from engines.rule_engine import (
    recommend_strategy as rule_recommend,
    recommend_dr, get_migration_roadmap,
    VALID_LEVELS, MIGRATION_ROADMAPS,
)
from engines.decision_engine import recommend_strategy as financial_recommend
from ml.predict_strategy import predict_strategy
from report_generator import generate_html_report, generate_csv_export


# ── Shared helpers ────────────────────────────────────────────────────────────

def _base_features(**overrides):
    base = {
        "server_count": 50, "avg_cpu_util": 60, "storage_tb": 20.0,
        "downtime_tolerance": 4.0, "compliance_level": 2,
        "growth_rate": 15, "budget_sensitivity": 2,
    }
    base.update(overrides)
    return base


def _base_cloud_costs(yearly=50_000):
    return {
        "AWS":   {"on_demand": yearly,       "reserved_1yr": yearly*0.65,
                  "reserved_3yr": yearly*0.45, "selected": yearly},
        "Azure": {"on_demand": yearly*1.1,   "reserved_1yr": yearly*0.70,
                  "reserved_3yr": yearly*0.50, "selected": yearly*1.1},
        "GCP":   {"on_demand": yearly*0.95,  "reserved_1yr": yearly*0.62,
                  "reserved_3yr": yearly*0.43, "selected": yearly*0.95},
    }


def _full_report_data():
    tco      = calculate_manual_tco(servers=20, storage_tb=10)
    cloud    = run_cloud_analysis(8, 32, 60, 70, 20, "on_demand")
    risk_raw = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
    adj      = risk_adjusted_tco(
        cloud["costs"][cloud["best_provider"]]["selected"], risk_raw)
    strat    = rule_recommend("medium", "medium", "high")
    dr       = recommend_dr("medium")
    rm       = get_migration_roadmap(strat)
    ml       = predict_strategy(_base_features())
    return {
        "org_name": "Test Corp", "pricing_model": "on_demand",
        "tco": tco, "cloud": cloud,
        "risk": {
            "risk": risk_raw, "adj_cloud_cost": adj,
            "inputs": {
                "downtime_risk": 0.1,  "downtime_cost": 50000,
                "compliance_risk": 0.05, "compliance_penalty": 100000,
                "skill_risk": 0.2,     "training_cost": 20000,
            }
        },
        "strategy": {
            "strategy": strat, "dr_plan": dr, "roadmap": rm,
            "inputs": {"compliance": "medium", "downtime": "medium", "growth": "high"}
        },
        "ml": {**ml, "inputs": _base_features()},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  1. COST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("1. COST ENGINE — Manual Verification & Extreme Values")

def t_hw_cost():
    approx(calculate_hardware_cost(10), 50_000)
run("Hardware cost: 10 servers × $5,000 = $50,000", t_hw_cost)

def t_stor_capex():
    approx(calculate_storage_hardware_cost(5), 2_500)
run("Storage CapEx: 5 TB × $500 = $2,500", t_stor_capex)

def t_maintenance():
    approx(calculate_maintenance_cost(50_000), 7_500)
run("Maintenance: $50,000 × 15% = $7,500", t_maintenance)

def t_power():
    approx(calculate_power_cost(10), 5_000)
run("Power: 10 servers × $500 = $5,000", t_power)

def t_staff_one_admin():
    for n in [1, 10, 24, 25]:
        approx(calculate_staff_cost(n), 80_000)
run("Staff: 1–25 servers → 1 admin → $80,000 (floor guard)", t_staff_one_admin)

def t_staff_two_admins():
    approx(calculate_staff_cost(26), 160_000)
run("Staff: 26 servers → 2 admins → $160,000", t_staff_two_admins)

def t_storage_opex():
    approx(calculate_storage_opex(10), 1_500)
run("Storage OpEx: 10 TB × $150 = $1,500", t_storage_opex)

def t_tco_formula():
    r = calculate_manual_tco(servers=10, storage_tb=5)
    # CapEx = (10×5000)+(5×500) = 52,500
    # OpEx  = 7500+5000+80000+750 = 93,250
    approx(r["total_capex"],             52_500)
    approx(r["annual_operational_cost"], 93_250)
    approx(r["tco_3yr"], 52_500 + 93_250 * 3)
    approx(r["tco_5yr"], 52_500 + 93_250 * 5)
run("Full TCO formula: CapEx + OpEx×N verified manually", t_tco_formula)

def t_5yr_gt_3yr():
    r = calculate_manual_tco(servers=20, storage_tb=10)
    assert r["tco_5yr"] > r["tco_3yr"], "5yr TCO must exceed 3yr TCO"
run("5-year TCO always greater than 3-year TCO", t_5yr_gt_3yr)

def t_all_keys():
    required = {
        "servers", "storage_tb", "hardware_cost", "storage_capex",
        "total_capex", "annual_maintenance", "annual_power", "annual_staff",
        "annual_storage_opex", "annual_operational_cost", "tco_3yr", "tco_5yr",
    }
    r = calculate_manual_tco(servers=10, storage_tb=5)
    missing = required - set(r.keys())
    assert not missing, f"Missing keys: {missing}"
run("All 12 documented result keys present", t_all_keys)

def t_non_negative():
    r = calculate_manual_tco(servers=50, storage_tb=20)
    for k, v in r.items():
        if isinstance(v, float):
            assert v >= 0, f"{k} is negative: {v}"
run("All cost values are non-negative", t_non_negative)

def t_doubling_servers():
    r1 = calculate_manual_tco(servers=10, storage_tb=5)
    r2 = calculate_manual_tco(servers=20, storage_tb=5)
    approx(r2["hardware_cost"], r1["hardware_cost"] * 2)
run("Doubling servers doubles hardware cost (linear scaling)", t_doubling_servers)

def t_zero_storage():
    r = calculate_manual_tco(servers=10, storage_tb=0)
    approx(r["storage_capex"], 0)
    approx(r["annual_storage_opex"], 0)
run("Zero storage → zero storage CapEx and OpEx", t_zero_storage)

def t_single_server():
    r = calculate_manual_tco(servers=1, storage_tb=1)
    assert r["servers"] == 1
    assert r["tco_5yr"] > 0
run("Extreme: 1 server produces valid positive TCO", t_single_server)

def t_large_enterprise():
    r = calculate_manual_tco(servers=500, storage_tb=500)
    assert r["servers"] == 500
    assert r["tco_5yr"] > 0
run("Extreme: 500 servers, 500 TB completes without error", t_large_enterprise)

def t_zero_servers_raises():
    raises(ValueError, lambda: calculate_manual_tco(0, 5), "positive")
run("Zero servers raises ValueError('positive')", t_zero_servers_raises)

def t_neg_servers_raises():
    raises(ValueError, lambda: calculate_manual_tco(-5, 5), "positive")
run("Negative servers raises ValueError", t_neg_servers_raises)

def t_neg_storage_raises():
    raises(ValueError, lambda: calculate_manual_tco(10, -1), "negative")
run("Negative storage raises ValueError('negative')", t_neg_storage_raises)

def t_all_presets():
    for p in ENTERPRISE_PRESETS:
        r = calculate_onprem_tco(preset=p)
        assert r["servers"] == ENTERPRISE_PRESETS[p]["servers"]
        assert r["tco_5yr"] > 0
run("All three presets produce valid results", t_all_presets)

def t_preset_order():
    rs = calculate_onprem_tco(preset="small")
    rm = calculate_onprem_tco(preset="medium")
    rl = calculate_onprem_tco(preset="large")
    assert rs["tco_5yr"] < rm["tco_5yr"] < rl["tco_5yr"], \
        "Expected small < medium < large TCO"
run("Preset ordering: small < medium < large 5yr TCO", t_preset_order)

def t_unknown_preset():
    raises(ValueError, lambda: calculate_onprem_tco(preset="enterprise"),
           "Unknown preset")
run("Unknown preset name raises ValueError", t_unknown_preset)

def t_no_input_raises():
    raises(ValueError, lambda: calculate_onprem_tco())
run("No input (no file, no preset) raises ValueError", t_no_input_raises)

def t_custom_salary():
    cheap    = calculate_manual_tco(50, 20, FinancialConfig(admin_salary=50_000))
    expensive = calculate_manual_tco(50, 20, FinancialConfig(admin_salary=150_000))
    assert expensive["tco_5yr"] > cheap["tco_5yr"]
run("Custom config: higher admin salary increases TCO", t_custom_salary)

def t_zero_maintenance():
    cfg = FinancialConfig(maintenance_rate=0.0)
    r   = calculate_manual_tco(10, 5, cfg)
    approx(r["annual_maintenance"], 0.0)
run("Custom config: zero maintenance rate gives zero maintenance cost", t_zero_maintenance)


# ══════════════════════════════════════════════════════════════════════════════
#  2. RISK ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("2. RISK ENGINE — Probability Math & Validation Guards")

def t_risk_formula():
    r = calculate_risk_adjustment(0.10, 50_000, 0.05, 100_000, 0.20, 15_000)
    approx(r["downtime_cost"],   5_000)
    approx(r["compliance_cost"], 5_000)
    approx(r["skill_cost"],      3_000)
    approx(r["total_risk_cost"], 13_000)
run("Expected value formula: docstring example verified manually", t_risk_formula)

def t_total_equals_sum():
    r = calculate_risk_adjustment(0.3, 20000, 0.1, 80000, 0.5, 10000)
    approx(r["total_risk_cost"],
           r["downtime_cost"] + r["compliance_cost"] + r["skill_cost"])
run("Total risk cost = sum of three components", t_total_equals_sum)

def t_zero_prob_zero_cost():
    r = calculate_risk_adjustment(0.0, 100000, 0.1, 50000, 0.2, 10000)
    approx(r["downtime_cost"], 0.0)
run("Zero probability → zero expected cost for that component", t_zero_prob_zero_cost)

def t_prob_one_full_cost():
    r = calculate_risk_adjustment(1.0, 99999, 0.0, 0, 0.0, 0)
    approx(r["downtime_cost"], 99999.0)
run("Probability 1.0 → expected cost = full stated cost", t_prob_one_full_cost)

def t_all_zeros():
    r = calculate_risk_adjustment(0.0, 0, 0.0, 0, 0.0, 0)
    approx(r["total_risk_cost"], 0.0)
run("All zeros → total risk cost = 0", t_all_zeros)

def t_all_max():
    r = calculate_risk_adjustment(1.0, 50000, 1.0, 100000, 1.0, 20000)
    approx(r["total_risk_cost"], 170_000.0)
run("All max (prob=1.0) → total = sum of all costs ($170,000)", t_all_max)

def t_adj_tco():
    risk = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
    adj  = risk_adjusted_tco(200_000, risk)
    approx(adj, 200_000 + risk["total_risk_cost"])
run("Risk-adjusted TCO = base cloud cost + total risk cost", t_adj_tco)

def t_zero_risk_adj():
    risk = calculate_risk_adjustment(0.0, 0, 0.0, 0, 0.0, 0)
    approx(risk_adjusted_tco(100_000, risk), 100_000.0)
run("Zero risk → adjusted TCO = base cost (no change)", t_zero_risk_adj)

def t_adj_gte_base():
    risk = calculate_risk_adjustment(0.3, 30000, 0.1, 60000, 0.4, 15000)
    assert risk_adjusted_tco(300_000, risk) >= 300_000, \
        "Risk adjustment can only increase costs"
run("Adjusted TCO always >= base cloud cost (risk only adds)", t_adj_gte_base)

def t_prob_above_1():
    raises(ValueError, lambda:
           calculate_risk_adjustment(1.1, 50000, 0.0, 0, 0.0, 0), "probability")
run("Probability > 1.0 raises ValueError", t_prob_above_1)

def t_prob_below_0():
    raises(ValueError, lambda:
           calculate_risk_adjustment(-0.1, 50000, 0.0, 0, 0.0, 0), "probability")
run("Probability < 0.0 raises ValueError", t_prob_below_0)

def t_neg_cost():
    raises(ValueError, lambda:
           calculate_risk_adjustment(0.1, -1000, 0.0, 0, 0.0, 0), "non-negative")
run("Negative cost raises ValueError('non-negative')", t_neg_cost)

def t_string_prob():
    raises(TypeError, lambda:
           calculate_risk_adjustment("high", 50000, 0.05, 100000, 0.2, 20000))
run("String probability raises TypeError", t_string_prob)

def t_none_prob():
    raises(TypeError, lambda:
           calculate_risk_adjustment(None, 50000, 0.05, 100000, 0.2, 20000))
run("None probability raises TypeError", t_none_prob)

def t_neg_base():
    risk = calculate_risk_adjustment(0.1, 10000, 0.0, 0, 0.0, 0)
    raises(ValueError, lambda: risk_adjusted_tco(-1000, risk), "non-negative")
run("Negative base cost in risk_adjusted_tco raises ValueError", t_neg_base)

def t_wrong_dict_key():
    raises(ValueError, lambda:
           risk_adjusted_tco(100_000, {"wrong_key": 5000}), "total_risk_cost")
run("Wrong dict key in risk_adjusted_tco raises ValueError", t_wrong_dict_key)


# ══════════════════════════════════════════════════════════════════════════════
#  3. CLOUD COST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("3. CLOUD COST ENGINE — Pricing Multipliers & Right-Sizing")

def t_yearly_formula():
    result = calculate_yearly_cost(0.192, 10, "on_demand")
    approx(result, 0.192 * 8760 * 10)
run("Yearly cost: 0.192 × 8760 × 10 × 1.0 verified manually", t_yearly_formula)

def t_reserved_1yr():
    od = calculate_yearly_cost(0.192, 10, "on_demand")
    r1 = calculate_yearly_cost(0.192, 10, "reserved_1yr")
    approx(r1, od * 0.65)
run("Reserved 1yr = 65% of on-demand (35% discount)", t_reserved_1yr)

def t_reserved_3yr():
    od = calculate_yearly_cost(0.192, 10, "on_demand")
    r3 = calculate_yearly_cost(0.192, 10, "reserved_3yr")
    approx(r3, od * 0.45)
run("Reserved 3yr = 45% of on-demand (55% discount)", t_reserved_3yr)

def t_pricing_order():
    od = calculate_yearly_cost(0.384, 5, "on_demand")
    r1 = calculate_yearly_cost(0.384, 5, "reserved_1yr")
    r3 = calculate_yearly_cost(0.384, 5, "reserved_3yr")
    assert od > r1 > r3, f"Pricing order violated: {od} > {r1} > {r3}"
run("Pricing order: on_demand > reserved_1yr > reserved_3yr", t_pricing_order)

def t_invalid_model():
    raises(ValueError, lambda: calculate_yearly_cost(0.192, 5, "spot"),
           "pricing_model")
run("Invalid pricing model 'spot' raises ValueError", t_invalid_model)

def t_double_servers_cost():
    c1 = calculate_yearly_cost(0.384, 5, "on_demand")
    c2 = calculate_yearly_cost(0.384, 10, "on_demand")
    approx(c2, c1 * 2)
run("Doubling servers doubles yearly cloud cost (linear)", t_double_servers_cost)

def t_rightsizing_formula():
    vcpu, _ = recommend_resources(8, 32, 50, 50)
    expected = math.ceil(8 * 0.50 * SAFETY_BUFFER)
    assert vcpu == expected, f"Got {vcpu}, expected {expected}"
run("Right-sizing: ceil(current × utilisation × 1.3) verified manually",
    t_rightsizing_formula)

def t_low_util_reduces():
    vcpu, ram = recommend_resources(16, 64, 20, 20)
    assert vcpu < 16, f"Expected vCPU < 16, got {vcpu}"
    assert ram  < 64, f"Expected RAM < 64, got {ram}"
run("Low utilisation (20%) reduces recommended resources", t_low_util_reduces)

def t_ram_standard_sizes():
    standard = {1, 2, 4, 8, 16, 32, 64, 128}
    for util in [20, 40, 60, 80]:
        _, ram = recommend_resources(8, 32, util, util)
        assert ram in standard, f"RAM {ram} not standard for util={util}%"
run("Recommended RAM always snaps to a standard cloud size", t_ram_standard_sizes)

def t_all_providers_present():
    r = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
    assert set(r["instances"].keys()) == {"AWS", "Azure", "GCP"}
    assert set(r["costs"].keys())     == {"AWS", "Azure", "GCP"}
run("Full analysis returns instances and costs for all 3 providers",
    t_all_providers_present)

def t_best_provider_lowest_cost():
    r  = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
    bp = r["best_provider"]
    bp_cost = r["costs"][bp]["selected"]
    for prov, cdata in r["costs"].items():
        assert cdata["selected"] >= bp_cost, \
            f"{prov} (${cdata['selected']:.0f}) cheaper than best {bp} (${bp_cost:.0f})"
run("Best provider has the lowest selected cost", t_best_provider_lowest_cost)

def t_all_pricing_keys():
    r = run_cloud_analysis(4, 16, 50, 50, 5, "reserved_1yr")
    for prov, cdata in r["costs"].items():
        for model in PRICING_MODELS:
            assert model in cdata, f"Missing {model} for {prov}"
        assert "selected" in cdata
run("All pricing model keys present in cost output per provider", t_all_pricing_keys)

def t_reserved_cheaper_than_od():
    r_od  = run_cloud_analysis(8, 32, 60, 70, 10, "on_demand")
    r_res = run_cloud_analysis(8, 32, 60, 70, 10, "reserved_3yr")
    best_od  = r_od["costs"][r_od["best_provider"]]["selected"]
    best_res = r_res["costs"][r_res["best_provider"]]["selected"]
    assert best_res < best_od, \
        f"Reserved ({best_res:.0f}) should be less than on-demand ({best_od:.0f})"
run("Best reserved-3yr cost always less than best on-demand cost", t_reserved_cheaper_than_od)

def t_reduction_pct_non_negative():
    r = run_cloud_analysis(8, 32, 30, 40, 5, "on_demand")
    assert r["cpu_reduction_pct"] >= 0
    assert r["ram_reduction_pct"] >= 0
run("CPU and RAM reduction percentages are non-negative", t_reduction_pct_non_negative)

def t_zero_cpu_util_raises():
    raises(ValueError, lambda: run_cloud_analysis(8, 32, 0, 70, 10))
run("CPU utilisation = 0 raises ValueError (out of valid range)", t_zero_cpu_util_raises)

def t_zero_servers_cloud_raises():
    raises(ValueError, lambda: run_cloud_analysis(8, 32, 60, 70, 0))
run("Zero servers raises ValueError", t_zero_servers_cloud_raises)


# ══════════════════════════════════════════════════════════════════════════════
#  4. RULE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("4. RULE ENGINE — All Branches, DR Tiers, Roadmap Integrity")

def t_rule1_hybrid():
    assert rule_recommend("high", "low", "medium") == "Hybrid Migration"
run("Rule 1: high compliance + low downtime → Hybrid Migration", t_rule1_hybrid)

def t_rule1_overrides_growth():
    assert rule_recommend("high", "low", "high") == "Hybrid Migration", \
        "Rule 1 must take priority over Rule 2 (growth)"
run("Rule 1 priority: overrides high growth when compliance=high, downtime=low",
    t_rule1_overrides_growth)

def t_rule2_cloud_native():
    for c, d in [("low","medium"), ("medium","high"), ("medium","low")]:
        r = rule_recommend(c, d, "high")
        assert r == "Cloud-Native Migration", \
            f"Expected Cloud-Native for ({c},{d},high), got {r}"
run("Rule 2: high growth (non-rule-1 combos) → Cloud-Native Migration", t_rule2_cloud_native)

def t_rule3_fallback():
    fallback_cases = [
        ("low","low","low"), ("low","medium","low"),
        ("medium","medium","medium"), ("low","high","medium"),
        ("high","medium","medium"),
    ]
    for c, d, g in fallback_cases:
        r = rule_recommend(c, d, g)
        assert r == "Lift-and-Shift", f"Expected Lift-and-Shift for ({c},{d},{g}), got {r}"
run("Rule 3 fallback: all remaining combos → Lift-and-Shift", t_rule3_fallback)

def t_all_27_combos():
    valid = {"Lift-and-Shift", "Hybrid Migration", "Cloud-Native Migration"}
    for c in VALID_LEVELS:
        for d in VALID_LEVELS:
            for g in VALID_LEVELS:
                result = rule_recommend(c, d, g)
                assert result in valid, f"Invalid strategy for ({c},{d},{g}): {result}"
run("All 27 level combinations return a valid strategy", t_all_27_combos)

def t_int_raises_type():
    raises(TypeError, lambda: rule_recommend(1, "low", "low"))
run("Integer compliance raises TypeError", t_int_raises_type)

def t_invalid_level_raises():
    raises(ValueError, lambda: rule_recommend("extreme", "low", "low"),
           "must be one of")
run("Invalid level string raises ValueError('must be one of')", t_invalid_level_raises)

def t_uppercase_normalised():
    assert rule_recommend("HIGH", "LOW", "MEDIUM") == "Hybrid Migration"
run("Uppercase input is normalised correctly (HIGH=high)", t_uppercase_normalised)

def t_whitespace_normalised():
    assert rule_recommend("  high  ", "  low  ", "  medium  ") == "Hybrid Migration"
run("Whitespace in input is stripped and normalised", t_whitespace_normalised)

def t_dr_hot():
    assert recommend_dr("low") == "Hot DR"
run("DR: low downtime tolerance → Hot DR (always-on standby)", t_dr_hot)

def t_dr_warm():
    assert recommend_dr("medium") == "Warm DR"
run("DR: medium downtime tolerance → Warm DR (pre-provisioned)", t_dr_warm)

def t_dr_cold():
    assert recommend_dr("high") == "Cold DR"
run("DR: high downtime tolerance → Cold DR (backup-based)", t_dr_cold)

def t_dr_invalid():
    raises(ValueError, lambda: recommend_dr("extreme"))
run("DR: invalid level raises ValueError", t_dr_invalid)

def t_dr_int():
    raises(TypeError, lambda: recommend_dr(0))
run("DR: integer input raises TypeError", t_dr_int)

def t_roadmap_five_phases():
    for strategy, roadmap in MIGRATION_ROADMAPS.items():
        assert len(roadmap) == 5, f"{strategy} has {len(roadmap)} phases, expected 5"
        for phase in roadmap:
            assert isinstance(phase, str) and len(phase) > 0
run("Each strategy has exactly 5 non-empty roadmap phases", t_roadmap_five_phases)

def t_get_roadmap():
    for strategy in MIGRATION_ROADMAPS:
        rm = get_migration_roadmap(strategy)
        assert isinstance(rm, list) and len(rm) == 5
run("get_migration_roadmap returns list of 5 for all strategies", t_get_roadmap)

def t_unknown_strategy():
    raises(ValueError, lambda: get_migration_roadmap("Stay Put"),
           "Unknown strategy")
run("Unknown strategy raises ValueError", t_unknown_strategy)

def t_int_strategy():
    raises(TypeError, lambda: get_migration_roadmap(42))
run("Integer strategy raises TypeError", t_int_strategy)


# ══════════════════════════════════════════════════════════════════════════════
#  5. DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("5. DECISION ENGINE — Confidence Thresholds & Strategy Tiers")

def _decide(onprem, cloud_yr, model="on_demand"):
    return financial_recommend(onprem, _base_cloud_costs(cloud_yr), model)

def t_high_confidence():
    r = _decide(80_000, 60_000)   # 25% saving
    approx(r["AWS"]["savings_pct"], 25.0)
    assert r["AWS"]["confidence"] == "High", \
        f"Expected High, got {r['AWS']['confidence']}"
run("25% saving → High confidence (threshold is 20%)", t_high_confidence)

def t_medium_confidence():
    r = _decide(100_000, 90_000)  # 10% saving
    assert r["AWS"]["confidence"] == "Medium"
run("10% saving → Medium confidence (5–20% band)", t_medium_confidence)

def t_low_confidence():
    r = _decide(100_000, 97_000)  # 3% saving
    assert r["AWS"]["confidence"] == "Low"
run("3% saving → Low confidence (0–5% band)", t_low_confidence)

def t_stay_on_prem():
    r = _decide(50_000, 70_000)
    assert r["AWS"]["recommendation"] == "Stay On-Prem"
    assert r["AWS"]["savings"] < 0
run("Cloud more expensive → Stay On-Prem, negative savings", t_stay_on_prem)

def t_full_migration():
    r = _decide(100_000, 70_000)  # 30% saving
    assert r["AWS"]["strategy"] == "Full Migration"
run("30% saving → Full Migration strategy", t_full_migration)

def t_hybrid_migration():
    r = _decide(100_000, 88_000)  # 12% saving
    assert r["AWS"]["strategy"] == "Hybrid Migration"
run("12% saving → Hybrid Migration strategy", t_hybrid_migration)

def t_selective_migration():
    r = _decide(100_000, 97_000)  # 3% saving
    assert r["AWS"]["strategy"] == "Selective Migration"
run("3% saving → Selective Migration strategy", t_selective_migration)

def t_no_saving_strategy():
    r = _decide(100_000, 110_000)
    assert r["AWS"]["strategy"] == "Stay On-Prem"
run("No saving → Stay On-Prem strategy", t_no_saving_strategy)

def t_summary_present():
    r = _decide(80_000, 60_000)
    assert "_summary" in r
run("_summary key present in every result", t_summary_present)

def t_summary_migrate():
    s = _decide(100_000, 70_000)["_summary"]
    assert s["overall_recommendation"] == "Migrate to Cloud"
    assert s["best_cloud_option"] is not None
run("Summary recommends Migrate to Cloud when savings exist", t_summary_migrate)

def t_summary_stay():
    costs = {
        p: {"on_demand": 120_000, "reserved_1yr": 78_000,
            "reserved_3yr": 54_000, "selected": 120_000}
        for p in ("AWS", "Azure", "GCP")
    }
    s = financial_recommend(100_000, costs)["_summary"]
    assert s["overall_recommendation"] == "Stay On-Prem"
run("Summary Stay On-Prem when ALL providers exceed on-prem cost", t_summary_stay)

def t_zero_onprem():
    raises(ValueError, lambda: financial_recommend(0, _base_cloud_costs(50_000)))
run("Zero on-prem cost raises ValueError", t_zero_onprem)

def t_invalid_pricing_decision():
    raises(ValueError, lambda:
           financial_recommend(80_000, _base_cloud_costs(60_000),
                               pricing_model="spot"), "pricing_model")
run("Invalid pricing model raises ValueError", t_invalid_pricing_decision)

def t_all_pricing_in_result():
    r = _decide(80_000, 60_000)
    for prov in ("AWS", "Azure", "GCP"):
        for model in PRICING_MODELS:
            assert model in r[prov]["all_pricing"], \
                f"Missing {model} in {prov}.all_pricing"
run("All pricing model keys present in per-provider result", t_all_pricing_in_result)


# ══════════════════════════════════════════════════════════════════════════════
#  6. ML PREDICTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

R.suite("6. ML PREDICTION ENGINE — Validity, Boundaries, Type Guards")

VALID_ML = {"Hybrid", "Cloud-Native", "Lift-and-Shift"}

def t_valid_strategy():
    r = predict_strategy(_base_features())
    assert r["strategy"] in VALID_ML, f"Unknown strategy: {r['strategy']}"
run("Prediction returns one of the three valid strategies", t_valid_strategy)

def t_confidence_format():
    r    = predict_strategy(_base_features())
    conf = r["confidence"]
    assert conf.endswith("%"), f"Confidence missing %: {conf}"
    pct  = float(conf.replace("%", ""))
    assert 0.0 < pct <= 100.0, f"Confidence out of range: {pct}"
run("Confidence is a % string between 0 and 100", t_confidence_format)

def t_top_factors_count():
    r = predict_strategy(_base_features())
    assert len(r["top_factors"]) == 3, \
        f"Expected 3 top factors, got {len(r['top_factors'])}"
run("top_factors always returns exactly 3 items", t_top_factors_count)

def t_top_factors_strings():
    r = predict_strategy(_base_features())
    for f in r["top_factors"]:
        assert isinstance(f, str) and len(f) > 0
run("top_factors entries are non-empty human-readable strings", t_top_factors_strings)

def t_decision_path_nonempty():
    r = predict_strategy(_base_features())
    assert isinstance(r["decision_path"], list)
    assert len(r["decision_path"]) > 0
    for step in r["decision_path"]:
        assert isinstance(step, str)
run("decision_path is a non-empty list of strings", t_decision_path_nonempty)

def t_result_keys():
    r = predict_strategy(_base_features())
    missing = {"strategy", "confidence", "top_factors", "decision_path"} - set(r.keys())
    assert not missing, f"Missing keys: {missing}"
run("Result dict contains all 4 required keys", t_result_keys)

def t_min_boundary():
    r = predict_strategy(_base_features(
        server_count=5, avg_cpu_util=10, storage_tb=1.0,
        downtime_tolerance=0.5, compliance_level=1,
        growth_rate=0, budget_sensitivity=1
    ))
    assert r["strategy"] in VALID_ML
run("Min boundary values accepted without error", t_min_boundary)

def t_max_boundary():
    r = predict_strategy(_base_features(
        server_count=500, avg_cpu_util=90, storage_tb=100.0,
        downtime_tolerance=24.0, compliance_level=3,
        growth_rate=40, budget_sensitivity=3
    ))
    assert r["strategy"] in VALID_ML
run("Max boundary values accepted without error", t_max_boundary)

def t_hybrid_profile():
    # Hybrid condition: compliance_level=3 (high) + downtime_tolerance<2
    # budget_sensitivity must be >= 2; the tree splits on Budget <= 1.5 before
    # reaching the compliance node — budget=1 routes to Lift-and-Shift instead.
    r = predict_strategy(_base_features(
        compliance_level=3, downtime_tolerance=1.0,
        growth_rate=10, budget_sensitivity=2
    ))
    assert r["strategy"] == "Hybrid", f"Expected Hybrid, got {r['strategy']}"
run("High compliance + low downtime + medium budget predicts Hybrid", t_hybrid_profile)

def t_cloud_native_profile():
    # Matches: growth_rate>25, budget_sensitivity>=2 → Cloud-Native
    r = predict_strategy(_base_features(
        growth_rate=35, budget_sensitivity=3,
        compliance_level=1, downtime_tolerance=10.0
    ))
    assert r["strategy"] == "Cloud-Native", f"Expected Cloud-Native, got {r['strategy']}"
run("High growth + flexible budget profile predicts Cloud-Native", t_cloud_native_profile)

def t_lift_and_shift_profile():
    # Matches: server_count>200, avg_cpu_util<40 → Lift-and-Shift
    r = predict_strategy(_base_features(
        server_count=300, avg_cpu_util=20, budget_sensitivity=1,
        downtime_tolerance=15.0, compliance_level=1, growth_rate=5
    ))
    assert r["strategy"] == "Lift-and-Shift", \
        f"Expected Lift-and-Shift, got {r['strategy']}"
run("Large low-utilisation estate predicts Lift-and-Shift", t_lift_and_shift_profile)

def t_server_below_min():
    raises(ValueError, lambda:
           predict_strategy(_base_features(server_count=4)), "out of range")
run("server_count = 4 (below min 5) raises ValueError", t_server_below_min)

def t_server_above_max():
    raises(ValueError, lambda:
           predict_strategy(_base_features(server_count=501)), "out of range")
run("server_count = 501 (above max 500) raises ValueError", t_server_above_max)

def t_cpu_below_min():
    raises(ValueError, lambda:
           predict_strategy(_base_features(avg_cpu_util=9)), "out of range")
run("avg_cpu_util = 9 (below min 10) raises ValueError", t_cpu_below_min)

def t_cpu_above_max():
    raises(ValueError, lambda:
           predict_strategy(_base_features(avg_cpu_util=91)), "out of range")
run("avg_cpu_util = 91 (above max 90) raises ValueError", t_cpu_above_max)

def t_compliance_zero():
    raises(ValueError, lambda:
           predict_strategy(_base_features(compliance_level=0)), "out of range")
run("compliance_level = 0 raises ValueError", t_compliance_zero)

def t_compliance_four():
    raises(ValueError, lambda:
           predict_strategy(_base_features(compliance_level=4)), "out of range")
run("compliance_level = 4 raises ValueError", t_compliance_four)

def t_growth_neg():
    raises(ValueError, lambda:
           predict_strategy(_base_features(growth_rate=-1)), "out of range")
run("growth_rate = -1 raises ValueError", t_growth_neg)

def t_growth_too_high():
    raises(ValueError, lambda:
           predict_strategy(_base_features(growth_rate=41)), "out of range")
run("growth_rate = 41 (above max 40) raises ValueError", t_growth_too_high)

def t_string_feature():
    raises(ValueError, lambda:
           predict_strategy(_base_features(server_count="fifty")))
run("String feature value raises ValueError", t_string_feature)

def t_none_feature():
    raises(ValueError, lambda:
           predict_strategy(_base_features(growth_rate=None)))
run("None feature value raises ValueError", t_none_feature)

def t_missing_feature():
    f = _base_features()
    del f["compliance_level"]
    raises(ValueError, lambda: predict_strategy(f), "Missing features")
run("Missing feature raises ValueError('Missing features')", t_missing_feature)


# ══════════════════════════════════════════════════════════════════════════════
#  7. RULE vs ML — Consistency on Anchor Scenarios
# ══════════════════════════════════════════════════════════════════════════════

R.suite("7. RULE vs ML — Consistency on Shared Scenario Matrix")

_COMPLIANCE_MAP = {"low": 1, "medium": 2, "high": 3}
_DOWNTIME_MAP   = {"low": 1.0, "medium": 6.0, "high": 14.0}
_GROWTH_MAP     = {"low": 5, "medium": 15, "high": 30}
_BUDGET_MAP     = {"low": 1, "medium": 2, "high": 3}
_STRATEGY_MAP   = {
    "Hybrid Migration":       "Hybrid",
    "Cloud-Native Migration": "Cloud-Native",
    "Lift-and-Shift":         "Lift-and-Shift",
}

SCENARIOS = [
    # (compliance, downtime, growth, budget, rule_expected, ml_expected, label)
    ("high", "low",  "medium", "medium",
     "Hybrid Migration",       "Hybrid",         "Anchor A: high compliance + low downtime"),
    ("low",  "high", "high",   "high",
     "Cloud-Native Migration", "Cloud-Native",   "Anchor B: high growth + flexible budget"),
    ("low",  "high", "low",    "low",
     "Lift-and-Shift",         "Lift-and-Shift", "Anchor C: low-growth default fallback"),
]

for _comp, _down, _grow, _budg, _rule_exp, _ml_exp, _label in SCENARIOS:
    def _make_tests(comp, down, grow, budg, rule_exp, ml_exp, label):

        def _rule_test():
            result = rule_recommend(comp, down, grow)
            assert result == rule_exp, \
                f"{label}: Rule → {result!r}, expected {rule_exp!r}"

        def _ml_test():
            f = _base_features(
                compliance_level   = _COMPLIANCE_MAP[comp],
                downtime_tolerance = _DOWNTIME_MAP[down],
                growth_rate        = _GROWTH_MAP[grow],
                budget_sensitivity = _BUDGET_MAP[budg],
            )
            result = predict_strategy(f)["strategy"]
            assert result == ml_exp, \
                f"{label}: ML → {result!r}, expected {ml_exp!r}"

        def _agree_test():
            rule_result = rule_recommend(comp, down, grow)
            f = _base_features(
                compliance_level   = _COMPLIANCE_MAP[comp],
                downtime_tolerance = _DOWNTIME_MAP[down],
                growth_rate        = _GROWTH_MAP[grow],
                budget_sensitivity = _BUDGET_MAP[budg],
            )
            ml_result = predict_strategy(f)["strategy"]
            rule_mapped = _STRATEGY_MAP[rule_result]
            assert rule_mapped == ml_result, (
                f"DISAGREEMENT — {label}: "
                f"Rule={rule_result} → {rule_mapped}, ML={ml_result}"
            )

        return _rule_test, _ml_test, _agree_test

    _rt, _mt, _at = _make_tests(
        _comp, _down, _grow, _budg, _rule_exp, _ml_exp, _label)
    run(f"Rule engine  — {_label}", _rt)
    run(f"ML engine    — {_label}", _mt)
    run(f"Agreement    — {_label}", _at)

def t_all_27_valid():
    valid = {"Lift-and-Shift", "Hybrid Migration", "Cloud-Native Migration"}
    for c in VALID_LEVELS:
        for d in VALID_LEVELS:
            for g in VALID_LEVELS:
                assert rule_recommend(c, d, g) in valid, \
                    f"Invalid result for ({c},{d},{g})"
run("All 27 level combinations produce a defined strategy", t_all_27_valid)


# ══════════════════════════════════════════════════════════════════════════════
#  8. INTEGRATION — End-to-End Pipeline
# ══════════════════════════════════════════════════════════════════════════════

R.suite("8. INTEGRATION — End-to-End Pipeline Cross-Checks")

_tco   = calculate_manual_tco(servers=20, storage_tb=10)
_cloud = run_cloud_analysis(8, 32, 60, 70, 20, "on_demand")
_risk  = calculate_risk_adjustment(0.1, 50000, 0.05, 100000, 0.2, 20000)
_adj   = risk_adjusted_tco(_cloud["costs"][_cloud["best_provider"]]["selected"], _risk)
_dec   = financial_recommend(_tco["annual_operational_cost"], _cloud["costs"])

def t_savings_consistency():
    bp = _cloud["best_provider"]
    expected = _tco["annual_operational_cost"] - _cloud["costs"][bp]["selected"]
    approx(_dec[bp]["savings"], expected)
run("Decision engine savings matches cost/cloud engine values (cross-check)",
    t_savings_consistency)

def t_adj_gte_base():
    base = _cloud["costs"][_cloud["best_provider"]]["selected"]
    assert _adj >= base, f"Adjusted ({_adj:.0f}) < base ({base:.0f})"
run("Risk-adjusted cost always >= base cloud cost", t_adj_gte_base)

def t_tco_5yr_formula():
    approx(_tco["tco_5yr"],
           _tco["total_capex"] + _tco["annual_operational_cost"] * 5)
run("5yr TCO = CapEx + OpEx×5 (cross-engine formula check)", t_tco_5yr_formula)

def t_summary_best_matches_cloud():
    s = _dec["_summary"]
    if s["overall_recommendation"] == "Migrate to Cloud":
        assert s["best_cloud_option"] == _cloud["best_provider"], \
            f"Summary best {s['best_cloud_option']} ≠ cloud engine best {_cloud['best_provider']}"
run("Decision summary best provider matches cloud engine best provider",
    t_summary_best_matches_cloud)

def t_small_preset_pipeline():
    t = calculate_onprem_tco(preset="small")
    c = run_cloud_analysis(4, 16, 30, 40, t["servers"], "on_demand")
    r = calculate_risk_adjustment(0.05, 20000, 0.02, 50000, 0.1, 10000)
    a = risk_adjusted_tco(c["costs"][c["best_provider"]]["selected"], r)
    s = rule_recommend("low", "high", "low")
    m = predict_strategy(_base_features(
        server_count=t["servers"], storage_tb=min(t["storage_tb"], 100)))
    assert t["tco_5yr"] > 0
    assert a > 0
    assert s == "Lift-and-Shift"
    assert m["strategy"] in VALID_ML
run("Full pipeline: small preset, all engines, end-to-end", t_small_preset_pipeline)

def t_large_preset_pipeline():
    t = calculate_onprem_tco(preset="large")
    c = run_cloud_analysis(16, 64, 45, 50, min(t["servers"], 200), "reserved_1yr")
    r = calculate_risk_adjustment(0.15, 200000, 0.10, 500000, 0.25, 80000)
    a = risk_adjusted_tco(c["costs"][c["best_provider"]]["selected"], r)
    s = rule_recommend("high", "low", "medium")
    assert t["tco_5yr"] > 0
    assert a > 0
    assert s == "Hybrid Migration"
run("Full pipeline: large preset, all engines, end-to-end", t_large_preset_pipeline)

def t_reserved_always_cheaper():
    c_od  = run_cloud_analysis(8, 32, 60, 70, 50, "on_demand")
    c_res = run_cloud_analysis(8, 32, 60, 70, 50, "reserved_3yr")
    best_od  = c_od["costs"][c_od["best_provider"]]["selected"]
    best_res = c_res["costs"][c_res["best_provider"]]["selected"]
    assert best_res < best_od
run("Reserved pricing consistently cheaper than on-demand across full analysis",
    t_reserved_always_cheaper)


# ══════════════════════════════════════════════════════════════════════════════
#  9. REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

R.suite("9. REPORT GENERATOR — HTML & CSV Output Validation")

_rd = _full_report_data()

def t_html_is_string():
    h = generate_html_report(_rd)
    assert isinstance(h, str) and len(h) > 0
run("HTML report is a non-empty string", t_html_is_string)

def t_html_min_length():
    h = generate_html_report(_rd)
    assert len(h) >= 10_000, f"Only {len(h):,} chars — expected ≥ 10,000"
run("HTML report >= 10,000 characters (full content check)", t_html_min_length)

def t_html_org_name():
    assert "Test Corp" in generate_html_report(_rd)
run("HTML report contains organisation name", t_html_org_name)

def t_html_phase_headings():
    h = generate_html_report(_rd)
    for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]:
        assert phase in h, f"Missing heading: {phase}"
run("HTML report contains all 5 phase headings", t_html_phase_headings)

def t_html_exec_summary():
    assert "Executive Summary" in generate_html_report(_rd)
run("HTML report contains Executive Summary section", t_html_exec_summary)

def t_html_roadmap():
    assert "Migration Roadmap" in generate_html_report(_rd)
run("HTML report contains Migration Roadmap section", t_html_roadmap)

def t_html_ml_strategy():
    assert _rd["ml"]["strategy"] in generate_html_report(_rd)
run("HTML report contains the ML predicted strategy name", t_html_ml_strategy)

def t_html_valid_structure():
    h = generate_html_report(_rd)
    assert h.strip().startswith("<!DOCTYPE html")
    assert "</html>" in h
run("HTML report has valid structure (DOCTYPE + closing tag)", t_html_valid_structure)

def t_html_partial_data():
    tco  = calculate_manual_tco(servers=10, storage_tb=5)
    data = {
        "org_name": "Partial Corp", "pricing_model": "on_demand",
        "tco": tco, "cloud": None, "risk": None,
        "strategy": None, "ml": None,
    }
    h = generate_html_report(data)
    assert "Partial Corp" in h
    assert "Phase 1" in h
run("Partial data (Phase 1 only) renders HTML without error", t_html_partial_data)

def t_csv_is_string():
    c = generate_csv_export(_rd)
    assert isinstance(c, str) and len(c) > 0
run("CSV export is a non-empty string", t_csv_is_string)

def t_csv_min_length():
    c = generate_csv_export(_rd)
    assert len(c) >= 500, f"Only {len(c)} chars — expected ≥ 500"
run("CSV export >= 500 characters", t_csv_min_length)

def t_csv_phase_headers():
    c = generate_csv_export(_rd)
    for phase in ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]:
        assert phase in c, f"Missing section: {phase}"
run("CSV export contains all 5 phase section headers", t_csv_phase_headers)

def t_csv_org_name():
    assert "Test Corp" in generate_csv_export(_rd)
run("CSV export contains organisation name", t_csv_org_name)

def t_csv_parseable():
    raw  = generate_csv_export(_rd)
    rows = list(csv_mod.reader(io.StringIO(raw)))
    assert len(rows) > 10, f"Only {len(rows)} rows parsed"
run("CSV export is parseable by Python's csv module", t_csv_parseable)

def t_csv_key_metrics():
    c = generate_csv_export(_rd)
    for metric in ["5-Year TCO", "Best Provider", "Total Risk Cost",
                   "Recommended Strategy", "ML Strategy"]:
        assert metric in c, f"Missing metric label: {metric}"
run("CSV export contains all key metric labels", t_csv_key_metrics)


# ══════════════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════════════

sys.exit(R.report())
