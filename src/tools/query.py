"""
src/tools/query.py
Các công cụ truy vấn, kiểm tra và phân tích đối tượng bản vẽ trong MicroStation V8i.
"""

from typing import Dict, Any, List, Optional
from src.core.ms_bridge import bridge


def register_query_tools(mcp):
    """Đăng ký các tool truy vấn vào MCP Server."""

    @mcp.tool
    def get_drawing_info() -> Dict[str, Any]:
        """
        Lấy thông tin tổng quan về bản vẽ đang mở trong MicroStation V8i.
        Bao gồm: đường dẫn file, tên file, tên Model hiện tại, loại 2D/3D, đơn vị vẽ (Master Unit).
        """
        dgn = bridge.get_active_file()
        model = bridge.get_active_model()

        info = {
            "file_name": dgn.Name,
            "full_path": dgn.FullName,
            "model_name": model.Name,
            "model_description": getattr(model, "Description", ""),
            "is_3d": bool(model.Is3D),
        }

        try:
            info["master_unit"] = model.MasterUnit.Label
            info["sub_unit"] = model.SubUnit.Label
        except Exception:
            pass

        try:
            cache = model.GraphicalElementCache
            info["elements_count"] = cache.Count
        except Exception:
            info["elements_count"] = "N/A"

        return info

    @mcp.tool
    def get_levels() -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả các Level (lớp bản vẽ) hiện có trong file DGN.
        Bao gồm: tên level, số hiệu level (number), trạng thái hiển thị.
        """
        dgn = bridge.get_active_file()
        levels_list = []

        try:
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
        except Exception as ex:
            return [{"error": f"Không thể lấy danh sách levels: {ex}"}]

        return levels_list

    @mcp.tool
    def get_active_settings() -> Dict[str, Any]:
        """
        Lấy các thiết lập vẽ đang hoạt động hiện tại (Active Level, Color, Weight, LineStyle).
        """
        app = bridge.get_app()
        settings = app.ActiveSettings

        result = {}
        try:
            result["active_level"] = settings.Level.Name if settings.Level else "Unknown"
        except Exception:
            result["active_level"] = "Unknown"

        try:
            result["active_color"] = settings.Color
        except Exception:
            result["active_color"] = "Unknown"

        try:
            result["active_weight"] = settings.LineWeight
        except Exception:
            result["active_weight"] = "Unknown"

        try:
            result["active_style"] = settings.LineStyle.Name if settings.LineStyle else "Unknown"
        except Exception:
            result["active_style"] = "Unknown"

        return result

    @mcp.tool
    def scan_elements(
        level: Optional[str] = None,
        element_type: Optional[str] = None,
        max_count: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Quét và lấy danh sách các phần tử trong bản vẽ MicroStation.
        :param level: Lọc theo tên level (nếu None sẽ lấy tất cả)
        :param element_type: Lọc theo loại ('Line', 'LineString', 'Shape', 'Text', 'TextNode', 'Cell'...)
        :param max_count: Số lượng tối đa phần tử trả về (mặc định 300)
        """
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        results = []
        count = 0

        type_map = {
            "line": 3,
            "linestring": 4,
            "shape": 6,
            "textnode": 7,
            "complexstring": 12,
            "complexshape": 14,
            "ellipse": 15,
            "arc": 16,
            "text": 17,
            "cell": 2,
        }
        target_type_id = type_map.get(element_type.lower()) if element_type else None

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
            except Exception:
                continue
            if not el:
                continue

            lvl_name = el.Level.Name if el.Level else ""
            if level and lvl_name.lower() != str(level).lower():
                continue

            el_type = int(el.Type)
            if target_type_id is not None and el_type != target_type_id:
                continue

            item = {
                "id": str(getattr(el, "ID64", getattr(el, "ID", ""))),
                "type": el_type,
                "level": lvl_name,
                "color": getattr(el, "Color", None),
                "weight": getattr(el, "LineWeight", None),
            }

            if el_type == 17:  # Text
                try:
                    item["type_name"] = "Text"
                    item["text"] = el.AsTextElement().Text
                    pt = el.AsTextElement().Origin
                    item["origin"] = [round(pt.X, 3), round(pt.Y, 3)]
                except Exception:
                    pass
            elif el_type == 7:  # TextNode
                try:
                    item["type_name"] = "TextNode"
                    lines = []
                    tne = el.AsTextNodeElement()
                    for i in range(1, tne.TextLinesCount + 1):
                        lines.append(tne.TextLine(i))
                    item["text"] = "\n".join(lines)
                    pt = tne.Origin
                    item["origin"] = [round(pt.X, 3), round(pt.Y, 3)]
                except Exception:
                    pass
            elif el_type == 3:  # Line
                try:
                    item["type_name"] = "Line"
                    le = el.AsLineElement()
                    p1 = le.StartPoint
                    p2 = le.EndPoint
                    item["points"] = [[round(p1.X, 3), round(p1.Y, 3)], [round(p2.X, 3), round(p2.Y, 3)]]
                    item["length"] = round(le.Length, 3)
                except Exception:
                    pass
            elif el_type == 4:  # LineString
                try:
                    item["type_name"] = "LineString"
                    lse = el.AsLineStringElement()
                    pts = []
                    try:
                        cnt = getattr(lse, "VerticesCount", 0)
                        for i in range(1, cnt + 1):
                            v = lse.Vertex(i)
                            pts.append([round(v.X, 3), round(v.Y, 3)])
                    except Exception:
                        pass
                    if not pts:
                        v_raw = lse.GetVertices()
                        pts = [[round(p.X, 3), round(p.Y, 3)] for p in v_raw]
                    item["points"] = pts
                    item["length"] = round(lse.Length, 3)
                except Exception:
                    pass
            elif el_type == 6:  # Shape
                try:
                    item["type_name"] = "Shape"
                    se = el.AsShapeElement()
                    v_raw = se.GetVertices()
                    item["points"] = [[round(p.X, 3), round(p.Y, 3)] for p in v_raw]
                    item["area"] = round(se.Area, 3)
                    item["length"] = round(se.Perimeter, 3)
                except Exception:
                    pass
            elif el_type == 2:  # Cell
                try:
                    item["type_name"] = "Cell"
                    item["cell_name"] = el.AsCellElement().Name
                except Exception:
                    pass
            elif el_type == 14:  # ComplexShape
                try:
                    item["type_name"] = "ComplexShape"
                    item["area"] = round(el.AsClosedElement().Area, 3)
                except Exception:
                    pass
            elif el_type == 12:  # ComplexString
                try:
                    item["type_name"] = "ComplexString"
                    item["length"] = round(el.AsOpenElement().Length, 3)
                except Exception:
                    pass
            else:
                item["type_name"] = f"Type_{el_type}"

            results.append(item)
            count += 1
            if count >= max_count:
                break

        return results

    @mcp.tool
    def get_element_details(element_id: str) -> Dict[str, Any]:
        """
        Lấy đầy đủ thông tin chi tiết của một phần tử theo ID (tọa độ Bounding Box, kích thước, thuộc tính đồ họa).

        :param element_id: ID định danh của phần tử
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy phần tử có ID {element_id}"}

        details = {
            "id": str(getattr(el, "ID64", getattr(el, "ID", element_id))),
            "type_id": int(el.Type),
            "level": el.Level.Name if el.Level else "",
            "color": getattr(el, "Color", None),
            "weight": getattr(el, "LineWeight", None),
            "style": el.LineStyle.Name if getattr(el, "LineStyle", None) else "",
            "is_locked": bool(getattr(el, "IsLocked", False)),
            "is_hidden": bool(getattr(el, "IsHidden", False)),
        }

        # Bounding Box Range
        try:
            rng = el.Range
            details["bounding_box"] = {
                "min_x": round(rng.Low.X, 4),
                "min_y": round(rng.Low.Y, 4),
                "min_z": round(rng.Low.Z, 4),
                "max_x": round(rng.High.X, 4),
                "max_y": round(rng.High.Y, 4),
                "max_z": round(rng.High.Z, 4),
                "width": round(rng.High.X - rng.Low.X, 4),
                "height": round(rng.High.Y - rng.Low.Y, 4),
            }
        except Exception:
            pass

        # Thuộc tính đặc thù theo Type
        el_type = int(el.Type)
        if el_type == 17:  # Text
            try:
                te = el.AsTextElement()
                details["type_name"] = "Text"
                details["text"] = te.Text
                details["text_height"] = te.TextStyle.Height
                details["text_width"] = te.TextStyle.Width
                details["origin"] = [round(te.Origin.X, 3), round(te.Origin.Y, 3)]
            except Exception:
                pass
        elif el_type == 3:  # Line
            try:
                le = el.AsLineElement()
                details["type_name"] = "Line"
                details["length"] = round(le.Length, 4)
                details["start_point"] = [round(le.StartPoint.X, 3), round(le.StartPoint.Y, 3)]
                details["end_point"] = [round(le.EndPoint.X, 3), round(le.EndPoint.Y, 3)]
            except Exception:
                pass
        elif el_type in (6, 14) or getattr(el, "IsClosedElement", False):  # Shape / ComplexShape
            try:
                details["type_name"] = "Shape" if el_type == 6 else ("ComplexShape" if el_type == 14 else "ClosedElement")
                closed = el.AsClosedElement()
                details["area"] = round(closed.Area, 4)
                details["perimeter"] = round(closed.Perimeter, 4)
                details["fill_mode"] = getattr(closed, "FillMode", 0)
                details["fill_color"] = getattr(closed, "FillColor", None)
                details["is_filled"] = details["fill_mode"] > 0
            except Exception:
                pass

        return details

    @mcp.tool
    def delete_element_by_id(element_id: str) -> str:
        """
        Xóa một phần tử trong bản vẽ theo ID.
        """
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
            except Exception:
                continue
            if not el:
                continue
            cur_id = str(getattr(el, "ID64", getattr(el, "ID", "")))
            if cur_id == str(element_id):
                model.RemoveElement(el)
                return f"Đã xóa phần tử ID {element_id}"
        return f"Không tìm thấy phần tử ID {element_id}"
