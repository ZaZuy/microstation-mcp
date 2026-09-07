"""
src/tools/dimension.py
Các công cụ đo đạc, đo khoảng cách, diện tích và ghi kích thước (Dimensioning) trong MicroStation V8i.
"""

import math
from typing import List, Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_dimension_tools(mcp):
    """Đăng ký các tool đo đạc và ghi kích thước vào MCP Server."""

    @mcp.tool
    def measure_distance(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        z1: float = 0.0,
        z2: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Đo khoảng cách chính xác, độ dời trục (dX, dY, dZ) và góc giữa 2 điểm tọa độ.
        Không tạo thêm đối tượng vào bản vẽ, chỉ trả về số liệu tính toán.

        :param x1: Tọa độ X điểm 1
        :param y1: Tọa độ Y điểm 1
        :param x2: Tọa độ X điểm 2
        :param y2: Tọa độ Y điểm 2
        :param z1: Tọa độ Z điểm 1 (mặc định 0.0)
        :param z2: Tọa độ Z điểm 2 (mặc định 0.0)
        """
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        dist_2d = math.hypot(dx, dy)
        dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360.0

        return {
            "point_1": [round(x1, 4), round(y1, 4), round(z1, 4)],
            "point_2": [round(x2, 4), round(y2, 4), round(z2, 4)],
            "delta_x": round(dx, 4),
            "delta_y": round(dy, 4),
            "delta_z": round(dz, 4),
            "distance_2d": round(dist_2d, 4),
            "distance_3d": round(dist_3d, 4),
            "angle_degrees": round(angle_deg, 3),
            "slope_percent": round((dz / dist_2d * 100.0) if dist_2d > 1e-6 else 0.0, 2),
        }

    @mcp.tool
    def measure_area(points: List[List[float]]) -> Dict[str, Any]:
        """
        Tính toán diện tích và chu vi hình học của một đa giác bất kỳ từ danh sách các đỉnh.

        :param points: Danh sách tọa độ đỉnh [[x1, y1], [x2, y2], [x3, y3], ...] (tối thiểu 3 điểm)
        """
        if len(points) < 3:
            return {"error": "Cần tối thiểu 3 điểm để tính diện tích đa giác!"}

        n = len(points)
        area = 0.0
        perimeter = 0.0

        for i in range(n):
            j = (i + 1) % n
            xi, yi = float(points[i][0]), float(points[i][1])
            xj, yj = float(points[j][0]), float(points[j][1])
            area += xi * yj - xj * yi
            perimeter += math.hypot(xj - xi, yj - yi)

        area = abs(area) / 2.0

        return {
            "vertices_count": n,
            "area_square_units": round(area, 4),
            "area_hectares": round(area / 10000.0, 6),
            "perimeter_units": round(perimeter, 4),
        }

    @mcp.tool
    def dimension_linear(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        offset: float = 5.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        text_height: float = 2.0,
    ) -> str:
        """
        Vẽ đường gióng ghi kích thước thẳng (Linear Dimension) giữa 2 điểm.

        :param x1: Tọa độ X điểm đầu
        :param y1: Tọa độ Y điểm đầu
        :param x2: Tọa độ X điểm cuối
        :param y2: Tọa độ Y điểm cuối
        :param offset: Khoảng cách dịch đường kích thước vuông góc với đoạn thẳng
        :param level: Tên Level đặt đường kích thước
        :param color: Màu nét
        :param text_height: Chiều cao chữ số kích thước
        """
        app = bridge.get_app()
        matrix = bridge.create_rotation_matrix(0.0)

        p1 = bridge.create_point(x1, y1, 0.0)
        p2 = bridge.create_point(x2, y2, 0.0)

        # Tính vector pháp tuyến để offset đường kích thước
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return "Lỗi: Hai điểm trùng nhau, không thể ghi kích thước!"

        nx = -dy / length * offset
        ny = dx / length * offset

        p_dim = bridge.create_point(x1 + nx, y1 + ny, 0.0)

        try:
            # Dimension Type 0 = MsdDimensionTypeSize (Size Dimension)
            dim_elem = bridge.unwrap(app.CreateDimensionElement1(None, matrix, 0))
            dim_elem.InsertPoint(1, p1)
            dim_elem.InsertPoint(2, p2)
            dim_elem.InsertPoint(3, p_dim)
            bridge.apply_symbology(dim_elem, level=level, color=color)
            bridge.add_element(dim_elem)
            return f"Đã tạo đường kích thước giữa ({x1}, {y1}) và ({x2}, {y2}) dài {round(length, 3)}"
        except Exception as ex:
            # Fallback nếu Dimension element COM đòi template đặc thù: vẽ bằng line + text kỹ thuật
            line_elem = bridge.unwrap(app.CreateLineElement2(None, bridge.create_point(x1+nx, y1+ny), bridge.create_point(x2+nx, y2+ny)))
            bridge.apply_symbology(line_elem, level=level, color=color)
            bridge.add_element(line_elem)

            mid_x = (x1 + x2) / 2.0 + nx
            mid_y = (y1 + y2) / 2.0 + ny
            angle_deg = math.degrees(math.atan2(dy, dx))
            text_elem = bridge.unwrap(app.CreateTextElement1(None, f"{round(length, 2)}", bridge.create_point(mid_x, mid_y), bridge.create_rotation_matrix(angle_deg)))
            try:
                text_elem.TextStyle.Height = float(text_height)
                text_elem.TextStyle.Width = float(text_height)
            except Exception:
                pass
            bridge.apply_symbology(text_elem, level=level, color=color)
            bridge.add_element(text_elem)
            return f"Đã ghi kích thước (đoạn nối + text) chiều dài {round(length, 2)}"

    @mcp.tool
    def dimension_aligned(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        offset: float = 3.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Ghi kích thước song song (Aligned Dimension) với đoạn thẳng.
        """
        return dimension_linear(x1=x1, y1=y1, x2=x2, y2=y2, offset=offset, level=level, color=color)

    @mcp.tool
    def dimension_radius(
        cx: float,
        cy: float,
        radius: float,
        angle_deg: float = 45.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Ghi chú kích thước bán kính (Radius Dimension R=...) của đường tròn hoặc cung tròn.

        :param cx: Tọa độ X tâm
        :param cy: Tọa độ Y tâm
        :param radius: Bán kính
        :param angle_deg: Góc hướng mũi tên chỉ dẫn bán kính (độ)
        :param level: Tên Level
        :param color: Màu vẽ
        """
        app = bridge.get_app()
        rad = math.radians(angle_deg)
        px = cx + radius * math.cos(rad)
        py = cy + radius * math.sin(rad)

        p_center = bridge.create_point(cx, cy, 0.0)
        p_rim = bridge.create_point(px, py, 0.0)

        # Vẽ tia chỉ dẫn từ tâm ra viền
        line_elem = bridge.unwrap(app.CreateLineElement2(None, p_center, p_rim))
        bridge.apply_symbology(line_elem, level=level, color=color)
        bridge.add_element(line_elem)

        # Đặt text R=...
        label_x = cx + (radius * 0.6) * math.cos(rad)
        label_y = cy + (radius * 0.6) * math.sin(rad)
        text_elem = bridge.unwrap(app.CreateTextElement1(None, f"R={round(radius, 3)}", bridge.create_point(label_x, label_y), bridge.create_rotation_matrix(angle_deg)))
        bridge.apply_symbology(text_elem, level=level, color=color)
        bridge.add_element(text_elem)

        return f"Đã ghi chú bán kính R={radius} tại tâm ({cx}, {cy})"
