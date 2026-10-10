"""
src/server package
Factory tạo và cấu hình instance MCP Server hoàn chỉnh.
Hỗ trợ chuyển đổi giữa chế độ 8 Consolidated Tools (mặc định - chuẩn AutoCAD MCP)
và chế độ Legacy 147 Tools.
"""

import os
from fastmcp import FastMCP
from src.server.context import SERVER_NAME, SERVER_INSTRUCTIONS
from src.server.logging import logger
from src.tools.consolidated import register_consolidated_tools
from src.tools import register_tools as register_legacy_tools
from src.resources import register_resources
from src.prompts import register_prompts


def create_server(mode: str = "auto") -> FastMCP:
    """
    Khởi tạo McpServer, gắn cấu hình và đăng ký toàn bộ Tools, Resources, Prompts.
    :param mode: 'consolidated' (8 tools - mặc định), 'legacy' (147 tools), hoặc 'both'
    """
    logger.info(f"Đang khởi tạo MCP Server: {SERVER_NAME}...")

    server = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )

    env_mode = os.environ.get("MICROSTATION_MCP_MODE", "consolidated").lower().strip()
    active_mode = mode if mode != "auto" else env_mode

    # 1. Đăng ký Tools theo mode
    if active_mode == "legacy":
        register_legacy_tools(server)
        logger.info("Đã đăng ký nhóm Legacy Tools (147 công cụ vi mô).")
    elif active_mode == "both":
        register_consolidated_tools(server)
        register_legacy_tools(server)
        logger.info("Đã đăng ký cả Consolidated Tools (8 công cụ) và Legacy Tools.")
    else:
        # Mặc định: 8 Consolidated Tools chuẩn kiến trúc AutoCAD MCP v3.1
        register_consolidated_tools(server)
        logger.info("Đã đăng ký 8 Consolidated Tools: drawing, entity, layer, cell, annotation, view, cadastral, system.")

    # 2. Đăng ký Resources
    register_resources(server)
    logger.info("Đã đăng ký các Resources (drawing/info, drawing/levels, drawing/settings).")

    # 3. Đăng ký Prompts
    register_prompts(server)
    logger.info("Đã đăng ký các Prompts (cad_drawing_workflow, element_inspection).")

    return server


__all__ = ["create_server"]
