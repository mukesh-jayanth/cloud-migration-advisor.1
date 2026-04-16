"""
zombie_detector.py
Phase 1 — Zombie Server Anomaly Detection

Scans server data for "Zombie Servers" — machines with large resource
allocations but near-zero utilisation.  These are flagged BEFORE cloud
pricing begins so the user is forced to justify their environment size,
preventing the migration of waste.

Placement: Phase 1 — Infrastructure & TCO (Inventory Integrity Check)
"""

import math
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Detection Thresholds
# ─────────────────────────────────────────────────────────────────────────────

ZOMBIE_RAM_THRESHOLD_GB = 32     # RAM allocation that should be noticed if wasted
ZOMBIE_CPU_THRESHOLD    = 4      # vCPU allocation threshold
ZOMBIE_UTIL_THRESHOLD   = 5.0    # % utilisation — anything ≤ 5% is suspicious


# ─────────────────────────────────────────────────────────────────────────────
# Severity Scoring
# ─────────────────────────────────────────────────────────────────────────────

def _zombie_severity(ram_gb: float, cpu: int, util_pct: float) -> str:
    """Return severity tier for a zombie server."""
    waste_score = 0
    if ram_gb >= 128:
        waste_score += 3
    elif ram_gb >= 64:
        waste_score += 2
    elif ram_gb >= 32:
        waste_score += 1

    if cpu >= 16:
        waste_score += 2
    elif cpu >= 8:
        waste_score += 1

    if util_pct <= 1.0:
        waste_score += 3
    elif util_pct <= 3.0:
        waste_score += 2
    elif util_pct <= 5.0:
        waste_score += 1

    if waste_score >= 6:
        return "Critical"
    elif waste_score >= 4:
        return "High"
    elif waste_score >= 2:
        return "Medium"
    return "Low"


def _zombie_recommendation(severity: str, ram_gb: float, cpu_util: float) -> str:
    if severity == "Critical":
        return (
            f"Decommission immediately. This server uses only {cpu_util:.1f}% CPU "
            f"with {ram_gb}GB RAM allocated. Right-sizing before migration is mandatory."
        )
    elif severity == "High":
        return (
            f"Right-size before migration. Reduce RAM to "
            f"≤{max(8, math.ceil(ram_gb * cpu_util / 100 * 1.25))}GB "
            "to match actual demand."
        )
    elif severity == "Medium":
        return (
            "Schedule a right-sizing review. Consider a smaller instance class in the cloud."
        )
    return "Monitor utilisation trends before deciding on cloud instance size."


# ─────────────────────────────────────────────────────────────────────────────
# Core Detection Function
# ─────────────────────────────────────────────────────────────────────────────

def detect_zombie_servers(server_list: list[dict]) -> dict:
    """
    Scan a list of server records for Zombie Servers.

    Each record should have:
        - "name"          : str   (server identifier)
        - "ram_gb"        : float (allocated RAM in GB)
        - "vcpu"          : int   (allocated vCPU count)
        - "cpu_util_pct"  : float (measured CPU utilisation %)
        - "ram_util_pct"  : float (measured RAM utilisation %) — optional

    Returns:
        {
            "zombies"              : list[dict],
            "zombie_count"         : int,
            "total_servers"        : int,
            "waste_summary"        : str,
            "potential_savings_pct" : float,
            "inventory_integrity"  : str,   # overall verdict
        }
    """
    zombies = []
    total_ram_gb  = 0.0
    wasted_ram_gb = 0.0

    for srv in server_list:
        name     = srv.get("name", "Unknown")
        ram_gb   = float(srv.get("ram_gb",       0))
        vcpu     = int(srv.get("vcpu",           0))
        cpu_util = float(srv.get("cpu_util_pct", 100))
        ram_util = float(srv.get("ram_util_pct", 100))

        total_ram_gb += ram_gb

        is_zombie = (
            (ram_gb >= ZOMBIE_RAM_THRESHOLD_GB or vcpu >= ZOMBIE_CPU_THRESHOLD)
            and cpu_util <= ZOMBIE_UTIL_THRESHOLD
        )

        if is_zombie:
            severity    = _zombie_severity(ram_gb, vcpu, cpu_util)
            wasted_ram  = ram_gb * (1 - cpu_util / 100)
            wasted_ram_gb += wasted_ram

            zombies.append({
                "name":          name,
                "ram_gb":        ram_gb,
                "vcpu":          vcpu,
                "cpu_util_pct":  cpu_util,
                "ram_util_pct":  ram_util,
                "severity":      severity,
                "wasted_ram_gb": round(wasted_ram, 1),
                "recommendation": _zombie_recommendation(severity, ram_gb, cpu_util),
            })

    zombie_count = len(zombies)

    potential_savings_pct = (
        round((wasted_ram_gb / total_ram_gb) * 100, 1) if total_ram_gb > 0 else 0.0
    )

    # ── Inventory integrity verdict ──────────────────────────────────────────
    if zombie_count == 0:
        waste_summary = "✅ No zombie servers detected. Resource allocation looks healthy."
        integrity     = "CLEAN"
    elif zombie_count == 1:
        waste_summary = (
            f"⚠️ 1 zombie server detected. Immediate decommission or right-sizing "
            f"could recover ~{potential_savings_pct}% of allocated capacity."
        )
        integrity = "WARNING"
    else:
        waste_summary = (
            f"🚨 {zombie_count} zombie servers detected ({potential_savings_pct}% wasted capacity). "
            f"Right-sizing these before migration will significantly reduce cloud bills."
        )
        integrity = "CRITICAL" if zombie_count >= 3 else "WARNING"

    return {
        "zombies":               zombies,
        "zombie_count":          zombie_count,
        "total_servers":         len(server_list),
        "waste_summary":         waste_summary,
        "potential_savings_pct": potential_savings_pct,
        "inventory_integrity":  integrity,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Zombie Server Detector Demo ===\n")

    servers = [
        {"name": "db-server-01", "ram_gb": 128, "vcpu": 32, "cpu_util_pct": 1.2},
        {"name": "web-server-01", "ram_gb": 16,  "vcpu": 4,  "cpu_util_pct": 65.0},
        {"name": "app-server-01", "ram_gb": 64,  "vcpu": 16, "cpu_util_pct": 3.5},
        {"name": "cache-01",      "ram_gb": 32,  "vcpu": 8,  "cpu_util_pct": 0.5},
    ]

    result = detect_zombie_servers(servers)
    print(f"Integrity: {result['inventory_integrity']}")
    print(f"Summary:   {result['waste_summary']}")
    for z in result["zombies"]:
        print(f"  🧟 {z['name']} [{z['severity']}]: {z['ram_gb']}GB RAM @ {z['cpu_util_pct']}% CPU")
        print(f"     → {z['recommendation']}")
