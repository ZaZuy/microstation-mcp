"""
src/server package
Factory tạo và cấu hình instance MCP Server hoàn chỉnh.
"""

from fastmcp import FastMCP
from src.server.context import SERVER_NAME, SERVER_INSTRUCTIONS
from src.server.logging import logger
from src.tools import register_tools
from src.resources import register_resources
from src.prompts import register_prompts


def create_server() -> FastMCP:
    """
    Khởi tạo McpServer, gắn cấu hình và đăng ký toàn bộ Tools, Resources, Prompts.
    """
    logger.info(f"Đang khởi tạo MCP Server: {SERVER_NAME}...")

    server = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )

    # 1. Đăng ký Tools
    register_tools(server)
    logger.info("Đã đăng ký toàn bộ nhóm Tools (drawing, text, settings, query, keyin).")

    # 2. Đăng ký Resources
    register_resources(server)
    logger.info("Đã đăng ký các Resources (drawing/info, drawing/levels, drawing/settings).")

    # 3. Đăng ký Prompts
    register_prompts(server)
    logger.info("Đã đăng ký các Prompts (cad_drawing_workflow, element_inspection).")

    return server


__all__ = ["create_server"]
