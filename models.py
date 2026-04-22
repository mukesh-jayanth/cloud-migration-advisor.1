"""
models.py — Pydantic session-state schema for CMDSS

Defines MigrationSessionState as the single source of truth for all
Streamlit session-state keys, their types, and their validation rules.

Usage
-----
Initialisation (once per session):
    initial_state = MigrationSessionState().model_dump()
    for key, val in initial_state.items():
        if key not in st.session_state:
            st.session_state[key] = val

Validated writes (every subsequent write):
    from models import set_state
    set_state("servers", 50)          # validated + written atomically
    set_state("pricing_model", "spot") # raises ValidationError → shown as st.error
"""

from __future__ import annotations

import streamlit as st
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class MigrationSessionState(BaseModel):
    """
    Strict Pydantic schema for all Streamlit session-state keys.
    Every field has a validated type and a safe default.
    """

    # ── Organisation ─────────────────────────────────────────────────────────
    org_name: str = Field(default="My Organisation", min_length=1, max_length=200)

    # ── Global settings ──────────────────────────────────────────────────────
    pricing_model: Literal["on_demand", "reserved_1yr", "reserved_3yr"] = "on_demand"

    # ── Infrastructure inputs ────────────────────────────────────────────────
    servers:    Optional[int]   = Field(default=None, ge=1)
    storage_tb: Optional[float] = Field(default=None, ge=0.0)
    vcpu_input: Optional[int]   = Field(default=None, ge=1)
    ram_input:  Optional[float] = Field(default=None, ge=1.0)

    # ── Utilisation (%) ──────────────────────────────────────────────────────
    cpu_util: Optional[float] = Field(default=None, ge=1.0, le=100.0)
    ram_util: Optional[float] = Field(default=None, ge=1.0, le=100.0)

    # ── Computed results ─────────────────────────────────────────────────────
    tco_result:     Optional[Dict[str, Any]] = None
    cloud_analysis: Optional[Dict[str, Any]] = None

    # ── Per-phase report payloads ─────────────────────────────────────────────
    report_risk:            Optional[Dict[str, Any]] = None
    report_strategy:        Optional[Dict[str, Any]] = None
    report_ml:              Optional[Dict[str, Any]] = None
    report_migration_econ:  Optional[Dict[str, Any]] = None
    report_audit:           Optional[Dict[str, Any]] = None

    # ── NLP risk analysis ─────────────────────────────────────────────────────
    nlp_risk_result: Optional[Dict[str, Any]] = None

    # ── Excel raw rows (for per-server-type zombie detection) ─────────────────
    infra_rows: Optional[list] = None

    # ── Field validators ──────────────────────────────────────────────────────

    @field_validator("org_name")
    @classmethod
    def _strip_org_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Organisation name must not be blank.")
        return v

    @field_validator("pricing_model")
    @classmethod
    def _valid_pricing_model(cls, v: str) -> str:
        allowed = {"on_demand", "reserved_1yr", "reserved_3yr"}
        if v not in allowed:
            raise ValueError(f"pricing_model must be one of {allowed}, got {v!r}")
        return v

    model_config = {"extra": "allow"}   # allow unknown keys like "state_initialized"


# ---------------------------------------------------------------------------
# Validated write helper
# ---------------------------------------------------------------------------

def set_state(key: str, value: Any) -> None:
    """
    Write a value to st.session_state through Pydantic validation.

    Steps
    -----
    1. Build a trial state dict from current session state + the new key/value.
    2. Run it through MigrationSessionState() — raises ValidationError on bad input.
    3. On success, write the (possibly coerced) value to st.session_state.
    4. On failure, surface a user-friendly st.error() and do NOT write the value.

    Parameters
    ----------
    key   : session-state key (must match a field in MigrationSessionState,
            or be allowed via model_config extra="allow")
    value : new value to set

    Example
    -------
    >>> set_state("servers", 50)
    >>> set_state("pricing_model", "reserved_1yr")
    >>> set_state("report_risk", {"risk": {...}, "adj_cloud_cost": 12345.0})
    """
    from pydantic import ValidationError

    trial: Dict[str, Any] = dict(st.session_state)  # shallow copy of current state
    trial[key] = value

    # Only validate schema fields; extra keys pass through unmodified.
    schema_fields = MigrationSessionState.model_fields.keys()
    schema_subset = {k: trial[k] for k in schema_fields if k in trial}

    try:
        validated = MigrationSessionState(**schema_subset)
        # Write the coerced value from the validated model (if it's a schema field)
        if key in schema_fields:
            st.session_state[key] = getattr(validated, key)
        else:
            st.session_state[key] = value          # extra keys written as-is
    except ValidationError as exc:
        # Collect all human-readable messages and surface them to the user
        messages = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        st.error(f"⚠️ **Input validation error** — {messages}")
