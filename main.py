"""
main.py — Teleops GUI Auto-Claim Entry Point
Chuyển tiếp thực thi tới auto_claim.main.
"""

import sys
import os

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_claim.main import main

if __name__ == "__main__":
    main()
