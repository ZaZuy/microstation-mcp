"""
src/main.py
Entry point chính để khởi động MicroStation V8i MCP Server.
"""

import os
import sys
import argparse

# Đảm bảo thư mục gốc dự án nằm trong sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.server import create_server
from src.transports.stdio import run_stdio
from src.transports.sse import run_sse


def main():
    parser = argparse.ArgumentParser(description="MicroStation V8i MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Giao thức truyền tải (mặc định: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host cho giao thức SSE (mặc định: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port cho giao thức SSE (mặc định: 8000)",
    )

    args = parser.parse_args()

    # Tạo instance McpServer với đầy đủ cấu hình Tools, Resources, Prompts
    server = create_server()

    # Khởi chạy theo transport đã chọn
    if args.transport == "stdio":
        run_stdio(server)
    elif args.transport == "sse":
        run_sse(server, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
