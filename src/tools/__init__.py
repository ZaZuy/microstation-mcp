"""
src/tools package
Hợp nhất và đăng ký toàn bộ 16 nhóm công cụ nguyên thủy MicroStation V8i vào MCP Server (109 CAD primitives).
Toàn bộ là các API CAD cơ bản tương ứng trực tiếp các Tool Box của MicroStation V8i,
AI đóng vai trò là bộ não điều khiển trực tiếp.
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
from src.tools.raster import register_raster_tools
from src.tools.group import register_group_tools
from src.tools.pattern import register_pattern_tools
from src.tools.fence import register_fence_tools
from src.tools.tags import register_tag_tools
from src.tools.solids_3d import register_solids_tools


def register_tools(mcp):
    """Đăng ký toàn bộ 16 nhóm công cụ CAD nguyên thủy vào MCP Server."""
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
    register_raster_tools(mcp)
    register_group_tools(mcp)
    register_pattern_tools(mcp)
    register_fence_tools(mcp)
    register_tag_tools(mcp)
    register_solids_tools(mcp)


__all__ = ["register_tools"]
