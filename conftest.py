# conftest.py — project-root pytest configuration
#
# Explicitly inserts the project root into sys.path so that all local imports
# (config_loader, engines.*, ml.*, report_generator, models) resolve correctly
# regardless of which directory pytest is invoked from.
#
# This is the most reliable approach and works with any pytest version.

import sys
import os

# Add the directory containing this file (= project root) to sys.path
sys.path.insert(0, os.path.dirname(__file__))
