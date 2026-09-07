"""
src/transports/stdio.py
Cơ chế chạy MCP Server qua kênh truyền chuẩn stdio (cho Antigravity, Claude Desktop, Cursor...).
"""

import sys
from fastmcp import FastMCP
from src.server.logging import logger


def run_stdio(server: FastMCP):
    """
    Chạy MCP Server qua stdio.
    Bảo đảm mã hóa UTF-8 tuyệt đối trên Windows để không bị lỗi Unicode.
    """
    if sys.platform == "win32":
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logger.info("Khởi động MCP Server qua giao thức stdio.")
    server.run(transport="stdio", show_banner=False)
