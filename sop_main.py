"""
sop_main.py — SOP Auto-Logging Entry Point
Chuyển tiếp thực thi tới auto_logging.sop_main.
"""

import sys
import os

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_logging.sop_main import main

if __name__ == "__main__":
    main()
