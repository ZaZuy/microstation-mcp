"""
src/tools/batch.py
Các công cụ xử lý dữ liệu đồ họa hàng loạt (Batch Processing) cho MicroStation V8i.
Đặc biệt tối ưu cho công tác khảo sát địa hình, số liệu mốc ranh quy hoạch và đo bóc bản đồ.
"""

from typing import List, Dict, Any, Optional
from src.core.ms_bridge import bridge


def register_batch_tools(mcp):
    """Đăng ký các tool xử lý hàng loạt vào MCP Server."""

    @mcp.tool
    def batch_draw_points(
        points: List[List[float]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: int = 5,
    ) -> str:
        """
        Vẽ hàng loạt điểm mốc (Point Markers) từ danh sách tọa độ [[x, y], [x, y, z], ...].

        :param points: Danh sách các tọa độ điểm
        :param level: Tên Level
        :param color: Chỉ số màu
        :param weight: Độ lớn điểm
        """
        if not points:
            return "Lỗi: Danh sách điểm trống!"

        app = bridge.get_app()
        count = 0
        for pt in points:
            x = float(pt[0])
            y = float(pt[1])
            z = float(pt[2]) if len(pt) > 2 else 0.0
            pt_obj = bridge.create_point(x, y, z)

            try:
                elem = bridge.unwrap(app.CreatePointMarkerElement1(None, pt_obj, 0))
            except Exception:
                elem = bridge.unwrap(app.CreateLineElement2(None, pt_obj, pt_obj))

            bridge.apply_symbology(elem, level=level, color=color, weight=weight)
            bridge.add_element(elem)
            count += 1

        return f"Đã vẽ thành công hàng loạt {count} điểm mốc."

    @mcp.tool
    def batch_draw_lines(
        lines: List[List[List[float]]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ hàng loạt đoạn thẳng từ danh sách cặp điểm: [[ [x1, y1], [x2, y2] ], [ [x3, y3], [x4, y4] ], ...].

        :param lines: Danh sách các cặp điểm đoạn thẳng
        :param level: Tên Level
        :param color: Màu nét
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if not lines:
            return "Lỗi: Danh sách đoạn thẳng trống!"

        app = bridge.get_app()
        count = 0
        for pair in lines:
            if len(pair) < 2:
                continue
            p1_raw, p2_raw = pair[0], pair[1]
            p1 = bridge.create_point(p1_raw[0], p1_raw[1], p1_raw[2] if len(p1_raw) > 2 else 0.0)
            p2 = bridge.create_point(p2_raw[0], p2_raw[1], p2_raw[2] if len(p2_raw) > 2 else 0.0)

            elem = bridge.unwrap(app.CreateLineElement2(None, p1, p2))
            bridge.apply_symbology(elem, level=level, color=color, weight=weight, style=style)
            bridge.add_element(elem)
            count += 1

        return f"Đã vẽ thành công hàng loạt {count} đoạn thẳng."

    @mcp.tool
    def batch_place_texts(
        items: List[Dict[str, Any]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        default_height: float = 2.5,
    ) -> str:
        """
        Đặt hàng loạt nhãn chữ (Text Elements) từ danh sách:
        [{'text': 'Số thửa 101', 'x': 100.5, 'y': 200.3, 'height': 2.0}, ...].

        :param items: Danh sách thông tin văn bản cần đặt
        :param level: Tên Level chung (hoặc có thể ghi đè trong từng item)
        :param color: Màu chữ chung
        :param default_height: Chiều cao chữ mặc định
        """
        if not items:
            return "Lỗi: Danh sách văn bản trống!"

        app = bridge.get_app()
        matrix = bridge.create_rotation_matrix(0.0)
        count = 0

        for item in items:
            txt = str(item.get("text", "")).strip()
            if not txt:
                continue
            x = float(item.get("x", 0.0))
            y = float(item.get("y", 0.0))
            h = float(item.get("height", default_height))
            rot = float(item.get("rotation_deg", 0.0))
            lvl = item.get("level", level)
            clr = item.get("color", color)

            origin = bridge.create_point(x, y, 0.0)
            rot_matrix = bridge.create_rotation_matrix(rot) if abs(rot) > 1e-6 else matrix

            elem = bridge.unwrap(app.CreateTextElement1(None, txt, origin, rot_matrix))
            try:
                elem.TextStyle.Height = h
                elem.TextStyle.Width = h
            except Exception:
                pass

            bridge.apply_symbology(elem, level=lvl, color=clr)
            bridge.add_element(elem)
            count += 1

        return f"Đã đặt thành công hàng loạt {count} nhãn văn bản."
