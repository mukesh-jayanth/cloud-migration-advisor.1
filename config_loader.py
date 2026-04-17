import yaml
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def load_config() -> dict:
    """Loads the central configuration file."""
    if not os.path.exists(CONFIG_PATH):
        logger.warning(f"Config file not found at {CONFIG_PATH}. Using empty dictionary.")
        return {}
        
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error parsing config.yaml: {e}")
        return {}

# Load it once on module import to act as a singleton
app_config = load_config()

def get_config_val(path: str, default=None):
    """
    Helper to fetch nested config values like 'cloud_cost.right_sizing_buffer'.
    Returns the given default if any part of the path is missing.
    """
    keys = path.split('.')
    val = app_config
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val
