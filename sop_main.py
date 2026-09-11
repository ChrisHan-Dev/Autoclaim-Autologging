"""
sop_main.py — SOP Auto-Logging Entry Point
Forwards execution to auto_logging.sop_main.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_logging.sop_main import main

if __name__ == "__main__":
    main()
