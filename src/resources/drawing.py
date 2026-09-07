"""
src/resources/drawing.py
MCP Resources cung cấp dữ liệu ngữ cảnh tức thời về bản vẽ MicroStation DGN.
"""

import json
from src.core.ms_bridge import bridge


def register_drawing_resources(mcp):
    """Đăng ký các Resource liên quan tới thông tin bản vẽ."""

    @mcp.resource("ms://drawing/info")
    def drawing_info_resource() -> str:
        """
        Trả về thông tin chi tiết dưới dạng JSON về file DGN và Active Model đang mở.
        """
        try:
            dgn = bridge.get_active_file()
            model = bridge.get_active_model()
            data = {
                "file_name": dgn.Name,
                "full_path": dgn.FullName,
                "model_name": model.Name,
                "model_description": getattr(model, "Description", ""),
                "is_3d": bool(model.Is3D),
            }
            try:
                data["master_unit"] = model.MasterUnit.Label
                data["sub_unit"] = model.SubUnit.Label
            except Exception:
                pass

            try:
                cache = model.GraphicalElementCache
                data["elements_count"] = cache.Count
            except Exception:
                data["elements_count"] = "N/A"

            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as ex:
            return json.dumps({"status": "disconnected", "error": str(ex)}, ensure_ascii=False, indent=2)

    @mcp.resource("ms://drawing/settings")
    def drawing_settings_resource() -> str:
        """
        Trả về thiết lập vẽ hiện hành (Active Level, Active Color, Weight, Style).
        """
        try:
            app = bridge.get_app()
            settings = app.ActiveSettings
            data = {
                "active_level": settings.Level.Name if settings.Level else "Unknown",
                "active_color": getattr(settings, "Color", "Unknown"),
                "active_weight": getattr(settings, "LineWeight", "Unknown"),
                "active_style": settings.LineStyle.Name if settings.LineStyle else "Unknown",
            }
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as ex:
            return json.dumps({"status": "error", "error": str(ex)}, ensure_ascii=False, indent=2)
