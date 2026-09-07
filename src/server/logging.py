"""
src/server/logging.py
Cấu hình Logging an toàn cho MCP Server.
Đảm bảo tất cả log được ghi ra stderr hoặc file, không ghi ra stdout (tránh hỏng giao thức stdio).
"""

import sys
import logging

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Thiết lập logger chuẩn hướng luồng xuất về sys.stderr.
    """
    logger = logging.getLogger("microstation_mcp")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger

logger = setup_logging()
