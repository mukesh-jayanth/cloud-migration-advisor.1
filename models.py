from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class MigrationSessionState(BaseModel):
    """
    Pydantic schema for strict typing and validation of the Streamlit session state.
    Provides default values and prevents missing-key errors.
    """
    org_name: str = Field(default="My Organisation", min_length=1)
    pricing_model: str = "on_demand"
    tco_result: Optional[Dict[str, Any]] = None
    cloud_analysis: Optional[Dict[str, Any]] = None
    servers: Optional[int] = None
    storage_tb: Optional[float] = None
    cpu_util: Optional[float] = None
    ram_util: Optional[float] = None
    vcpu_input: Optional[int] = None
    ram_input: Optional[float] = None
    
    # Report states
    report_risk: Optional[Dict[str, Any]] = None
    report_strategy: Optional[Dict[str, Any]] = None
    report_ml: Optional[Dict[str, Any]] = None
    report_migration_econ: Optional[Dict[str, Any]] = None
    report_audit: Optional[Dict[str, Any]] = None
