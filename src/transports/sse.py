"""
src/transports/sse.py
Cơ chế chạy MCP Server qua giao thức mạng SSE (Server-Sent Events qua HTTP).
"""

from fastmcp import FastMCP
from src.server.logging import logger


def run_sse(server: FastMCP, host: str = "127.0.0.1", port: int = 8000):
    """
    Chạy MCP Server qua giao diện SSE/HTTP.
    """
    logger.info(f"Khởi động MCP Server qua SSE tại http://{host}:{port}")
    server.run(transport="sse", host=host, port=port)
