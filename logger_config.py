"""
logger_config.py
Centralized Audit Logging for CMDSS

Provides a single `get_logger(name)` function that all engines and ML modules
import. Logs are written simultaneously to:
  - logs/audit.log  (file — persistent audit trail)
  - console/stderr  (WARNING+ only, so Streamlit stays clean)

Usage in any module:
    from logger_config import get_logger
    logger = get_logger(__name__)
    logger.info("TCO calculated: %s servers | %s annual OpEx", servers, opex)
"""

import logging
import os
import sys

# ── Log directory ─────────────────────────────────────────────────────────────
LOG_DIR  = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "audit.log")
os.makedirs(LOG_DIR, exist_ok=True)

# ── Shared formatter ──────────────────────────────────────────────────────────
_FMT  = "%(asctime)s  %(levelname)-8s [%(name)s]  %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ── Root logger (configure once) ──────────────────────────────────────────────
_configured = False

def _configure_root():
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # capture everything; handlers filter

    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    # File handler — INFO and above → audit.log
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    # Console handler — WARNING and above (keeps Streamlit clean)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)

    root.addHandler(fh)
    root.addHandler(ch)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger connected to the centralized audit handler."""
    _configure_root()
    return logging.getLogger(name)
