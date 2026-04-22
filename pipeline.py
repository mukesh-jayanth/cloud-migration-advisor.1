import time
import sys
import io
from engines.cloud_cost_engine import run_cloud_analysis
from engines.decision_engine import recommend_strategy

# Ensure UTF-8 output on Windows consoles (avoids UnicodeEncodeError with ✓/★ chars)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# NOTE: pipeline.py is a standalone CLI demo / smoke-test.
# The primary code path is app.py (Streamlit). Run directly:
#   python pipeline.py
# to validate the cloud analysis + decision engine integration.


# -------------------------------
# Full Pipeline Runner
# -------------------------------
def run_full_pipeline(
    current_vcpu: int,
    current_ram: float,
    cpu_utilization: float,
    ram_utilization: float,
    servers: int,
    onprem_cost: float,
    pricing_model: str = "on_demand"
) -> dict:
    """
    End-to-end pipeline:
      1. Validate inputs
      2. Right-size infrastructure
      3. Select best cloud instances per provider
      4. Calculate costs
      5. Choose best provider
      6. Compare vs on-prem and recommend strategy

    Args:
        current_vcpu    : Current number of vCPUs per server
        current_ram     : Current RAM in GB per server
        cpu_utilization : Measured CPU usage % (1-100)
        ram_utilization : Measured RAM usage % (1-100)
        servers         : Number of servers to migrate
        onprem_cost     : Total annual on-prem cost in USD
        pricing_model   : 'on_demand' | 'reserved_1yr' | 'reserved_3yr'

    Returns:
        Complete analysis dict on success, or
        { "error": "<message>", "summary": {} } on failure.
        Always check result["error"] before reading other keys.
    """

    try:
        start_time = time.time()

        # Stage 1-5: Cloud analysis
        cloud_result = run_cloud_analysis(
            current_vcpu=current_vcpu,
            current_ram=current_ram,
            cpu_utilization=cpu_utilization,
            ram_utilization=ram_utilization,
            servers=servers,
            pricing_model=pricing_model
        )

        # Stage 6: Decision layer
        decision = recommend_strategy(
            onprem_cost=onprem_cost,
            cloud_costs=cloud_result["costs"],
            pricing_model=pricing_model
        )

        # Derive monthly cost from selected pricing model — always consistent
        best_provider = cloud_result["best_provider"]
        best_yearly_cost = cloud_result["costs"][best_provider]["selected"]
        best_monthly_cost = round(best_yearly_cost / 12, 2)

        end_time = time.time()

        return {
            **cloud_result,
            "onprem_cost": onprem_cost,
            "decision": decision,
            "summary": decision.get("_summary", {}),
            "execution_time_sec": round(end_time - start_time, 3),
            "best_monthly_cost": best_monthly_cost,
            "error": None
        }

    except ValueError as e:
        # Input validation or instance-matching failures
        return {
            "error": str(e),
            "summary": {}
        }

    except Exception as e:
        # Unexpected failures — missing CSV, pandas errors, etc.
        return {
            "error": f"Unexpected error: {str(e)}",
            "summary": {}
        }


# -------------------------------
# Pretty CLI Report
# -------------------------------
def print_report(result: dict) -> None:
    """
    Pretty-print a full analysis result to the console.
    Useful for CLI usage, debugging, and viva demos.
    """

    # Guard: surface errors clearly instead of crashing on missing keys
    if result.get("error"):
        print(f"\n  [ERROR] Pipeline failed: {result['error']}\n")
        return

    sep = "-" * 60

    print(f"\n{'=' * 60}")
    print(f"  MULTI-CLOUD DECISION REPORT")
    print(f"{'=' * 60}")

    # -------------------------------
    # RIGHT-SIZING
    # -------------------------------
    print(f"\n  RIGHT-SIZING")
    print(sep)
    print(f"  Original  : {result['original_vcpu']} vCPU / {result['original_ram']} GB RAM")
    print(f"  Optimized : {result['recommended_vcpu']} vCPU / {result['recommended_ram']} GB RAM")
    print(f"  CPU saved : {result['cpu_reduction_pct']}%")
    print(f"  RAM saved : {result['ram_reduction_pct']}%")
    print(f"  Workload  : {result['workload_type'].capitalize()}")

    # -------------------------------
    # INSTANCE SELECTION + ALL PRICING
    # -------------------------------
    print(f"\n  INSTANCE SELECTION")
    print(sep)

    for provider, data in result["instances"].items():
        match = "[OK] optimal" if data["workload_match"] else "[~] adjusted"
        costs = result["costs"][provider]

        # Instance summary line
        print(
            f"  {provider:<8}: {data['instance']:<20} "
            f"{data['vcpu']} vCPU / {data['ram_gb']} GB   "
            f"${data['price_per_hour']:.4f}/hr   {match}"
        )

        # All-pricing breakdown
        print(
            f"  {'':8}  "
            f"on-demand: ${costs['on_demand']:>10,.2f}   "
            f"1yr reserved: ${costs['reserved_1yr']:>10,.2f}   "
            f"3yr reserved: ${costs['reserved_3yr']:>10,.2f}"
        )

    # -------------------------------
    # ANNUAL COST COMPARISON TABLE
    # -------------------------------
    pricing_label = result["pricing_model"].replace("_", " ").upper()
    print(f"\n  ANNUAL COST COMPARISON  [{pricing_label}]")
    print(sep)
    print(
        f"  {'':1} {'Provider':<9} {'Cloud Cost':>12} "
        f"{'Savings':>12}   {'Confidence':<10} Recommendation"
    )
    print(
        f"  {'-':1} {'-'*9} {'-'*12} "
        f"{'-'*12}   {'-'*10} {'-'*20}"
    )

    for provider, data in result["decision"].items():
        if provider in ("_summary", "_migration_economics"):
            continue

        marker = "*" if provider == result["best_provider"] else " "

        savings_str = (
            f"+${data['savings']:,.0f}"
            if data["savings"] >= 0
            else f"-${abs(data['savings']):,.0f}"
        )

        rec = data.get('recommendation', data.get('strategy', 'Migrate'))

        print(
            f" {marker} {provider:<9} ${data['cloud_cost']:>11,.2f} "
            f"{savings_str:>12}   {data['confidence']:<10} {rec}"
        )

    print(f"\n  {'':1} {'On-Prem':<9} ${result['onprem_cost']:>11,.2f}")

    # -------------------------------
    # FINAL RECOMMENDATION
    # -------------------------------
    summary = result.get("summary", {})

    print(f"\n  RECOMMENDATION")
    print(sep)
    print(f"  Decision     : {summary.get('overall_recommendation', 'N/A')}")

    if summary.get("best_cloud_option"):
        print(f"  Best option  : {summary['best_cloud_option']}")
        print(f"  Confidence   : {summary.get('confidence', 'N/A')}")
        print(f"  Annual save  : ${summary['best_savings']:,.2f} ({summary['best_savings_pct']:.1f}%)")
        print(f"  Monthly cost : ${result.get('best_monthly_cost', 0):,.2f}")

    print(f"  {summary.get('reason', '')}")

    # -------------------------------
    # PERFORMANCE
    # -------------------------------
    print(f"\n  Execution time : {result.get('execution_time_sec', 0)} sec")
    print(f"\n{'=' * 60}\n")


# -------------------------------
# Demo run
# -------------------------------
if __name__ == "__main__":

    # pricing_model = "reserved_1yr" — 1-year commitment, ~35% cheaper than on-demand.
    # Change to "on_demand" or "reserved_3yr" to compare commitment levels.
    result = run_full_pipeline(
        current_vcpu=8,
        current_ram=32,
        cpu_utilization=30,
        ram_utilization=40,
        servers=5,
        onprem_cost=80000,
        pricing_model="reserved_1yr"
    )

    print_report(result)