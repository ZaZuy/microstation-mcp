"""
src/tools package
Hợp nhất và đăng ký toàn bộ nhóm công cụ MicroStation V8i vào MCP Server.

Có 2 lớp tool:
  1. COM Tools (16 nhóm, ~62+ tools): Giao tiếp qua COM out-of-process
     - Không cần MDL, chỉ cần MicroStation đang chạy
  2. Native Tools (2 nhóm, ~23 tools): Giao tiếp qua Named Pipe MDL
     - Cần MDL app MsNativePipe.ma đang load: MDL LOAD MsNativePipe
     - Nhanh hơn COM ~10-50x
     - Tên tool có prefix 'native_' hoặc 'batch_' / 'begin_' / 'end_' / 'get_model_snapshot'
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
from src.tools.workflow import register_workflow_tools

# Native Pipe tools — yêu cầu MDL MsNativePipe.ma
from src.tools.native_batch import register_native_batch_tools
from src.tools.drawing_native import register_drawing_native_tools
from src.core._pipe_singleton import get_pipe_client


def register_tools(mcp):
    """
    Đăng ký toàn bộ nhóm công cụ CAD vào MCP Server.

    - 16 nhóm COM tools (backward compatible, không cần MDL)
    - 2 nhóm Native tools (yêu cầu MDL MsNativePipe.ma — nhanh hơn nhiều)
    """
    # --- COM Tools (16 nhóm, không cần MDL) ---
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
    register_workflow_tools(mcp)

    # --- Native Pipe Tools (yêu cầu MDL, nhanh hơn COM) ---
    # Lấy singleton PipeClient — được tạo lazy (không kết nối ngay)
    pipe_client = get_pipe_client()
    register_native_batch_tools(mcp, pipe_client)
    register_drawing_native_tools(mcp, pipe_client)


__all__ = ["register_tools"]

