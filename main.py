"""
main.py — Teleops GUI Auto-Claim Entry Point
Forwards execution to auto_claim.main.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_claim.main import main

if __name__ == "__main__":
    main()
