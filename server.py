"""
server.py
Root entrypoint tương thích ngược cho MicroStation V8i MCP Server.
Chuyển tiếp lệnh gọi tới src/main.py.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.main import main

if __name__ == "__main__":
    main()
