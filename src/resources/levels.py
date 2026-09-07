"""
src/resources/levels.py
MCP Resource cung cấp danh mục các layer/level trong bản vẽ MicroStation.
"""

import json
from src.core.ms_bridge import bridge


def register_levels_resources(mcp):
    """Đăng ký Resource danh sách levels."""

    @mcp.resource("ms://drawing/levels")
    def drawing_levels_resource() -> str:
        """
        Trả về danh sách tất cả các Level hiện có trong file DGN dưới dạng JSON.
        """
        try:
            dgn = bridge.get_active_file()
            levels_list = []
            levels = dgn.Levels
            for i in range(1, levels.Count + 1):
                try:
                    lvl = levels.Item(i)
                    levels_list.append({
                        "name": lvl.Name,
                        "number": getattr(lvl, "Number", i),
                        "is_displayed": getattr(lvl, "IsDisplayed", True),
                    })
                except Exception:
                    continue
            return json.dumps(levels_list, ensure_ascii=False, indent=2)
        except Exception as ex:
            return json.dumps({"status": "error", "error": str(ex)}, ensure_ascii=False, indent=2)
