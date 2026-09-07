"""
src/tools package
Hợp nhất và đăng ký toàn bộ 55+ công cụ MicroStation V8i vào MCP Server.
"""

from src.tools.drawing import register_drawing_tools
from src.tools.dimension import register_dimension_tools
from src.tools.modify import register_modify_tools
from src.tools.text import register_text_tools
from src.tools.view import register_view_tools
from src.tools.file_model import register_file_model_tools
from src.tools.batch import register_batch_tools
from src.tools.settings import register_settings_tools
from src.tools.query import register_query_tools
from src.tools.keyin import register_keyin_tools


def register_tools(mcp):
    """Đăng ký toàn bộ 10 nhóm công cụ (55+ tools) vào MCP Server."""
    register_drawing_tools(mcp)
    register_dimension_tools(mcp)
    register_modify_tools(mcp)
    register_text_tools(mcp)
    register_view_tools(mcp)
    register_file_model_tools(mcp)
    register_batch_tools(mcp)
    register_settings_tools(mcp)
    register_query_tools(mcp)
    register_keyin_tools(mcp)


__all__ = ["register_tools"]
