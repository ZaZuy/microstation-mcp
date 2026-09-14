"""
src/tools/dimension.py
Các công cụ đo đạc, đo khoảng cách, diện tích và ghi kích thước (Dimensioning) nguyên thủy trong MicroStation V8i.
Toàn bộ là các API CAD cơ bản, không chứa thuật toán phức tạp hay phụ thuộc thư viện ngoài.
"""

import math
from typing import List, Optional, Dict, Any
from src.core.ms_bridge import bridge


def _get_polygon_from_element(el) -> Optional[List[List[float]]]:
    """Trích xuất danh sách tọa độ đỉnh [[x, y], ...] từ Shape, ComplexShape, LineString, Line."""
    if not el:
        return None
    el_type = int(el.Type)
    pts = []

    # Check IsVertexList (Shape, LineString, PointString)
    if getattr(el, "IsVertexList", False):
        try:
            vl = el.AsVertexList
            v_raw = vl.GetVertices()
            pts = [[round(p.X, 4), round(p.Y, 4)] for p in v_raw]
            if pts:
                return pts
        except Exception:
            pass

    # Shape (6) fallback
    if el_type == 6:
        try:
            se = el.AsShapeElement()
            try:
                vc = getattr(se, "VerticesCount", 0)
                for i in range(1, vc + 1):
                    pt = se.Vertex(i)
                    pts.append([round(pt.X, 4), round(pt.Y, 4)])
            except Exception:
                pass
            if not pts:
                v_raw = se.GetVertices()
                pts = [[round(p.X, 4), round(p.Y, 4)] for p in v_raw]
            if pts:
                return pts
        except Exception:
            pass

    # LineString (4) fallback
    elif el_type == 4:
        try:
            le = el.AsLineElement()
            v_raw = le.GetVertices()
            return [[round(p.X, 4), round(p.Y, 4)] for p in v_raw]
        except Exception:
            pass

    # ComplexShape (14) or ComplexString (12)
    elif el_type in (12, 14):
        try:
            ee = el.GetSubElements()
            while ee.MoveNext():
                sub = ee.Current
                sub_pts = _get_polygon_from_element(sub)
                if sub_pts:
                    if not pts:
                        pts.extend(sub_pts)
                    else:
                        if math.hypot(pts[-1][0] - sub_pts[0][0], pts[-1][1] - sub_pts[0][1]) < 0.05:
                            pts.extend(sub_pts[1:])
                        else:
                            pts.extend(sub_pts)
            return pts
        except Exception:
            pass

    # Line (3)
    elif el_type == 3:
        try:
            le = getattr(el, "AsLineElement", None)
            le = le() if callable(le) else le
            return [
                [round(le.StartPoint.X, 4), round(le.StartPoint.Y, 4)],
                [round(le.EndPoint.X, 4), round(le.EndPoint.Y, 4)],
            ]
        except Exception:
            pass

    return None


def _calc_centroid_and_area(pts: List[List[float]]):
    """Tính (area, perimeter, cx, cy) từ danh sách đỉnh bằng công thức Shoelace tiêu chuẩn."""
    n = len(pts)
    if n < 3:
        return 0.0, 0.0, 0.0, 0.0

    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-4 and n > 3:
        clean_pts = pts[:-1]
    else:
        clean_pts = pts

    m = len(clean_pts)
    signed_area = 0.0
    perimeter = 0.0
    cx = 0.0
    cy = 0.0

    for i in range(m):
        j = (i + 1) % m
        xi, yi = clean_pts[i][0], clean_pts[i][1]
        xj, yj = clean_pts[j][0], clean_pts[j][1]
        cross = xi * yj - xj * yi
        signed_area += cross
        perimeter += math.hypot(xj - xi, yj - yi)
        cx += (xi + xj) * cross
        cy += (yi + yj) * cross

    area = abs(signed_area) / 2.0
    if abs(signed_area) > 1e-6:
        cx = cx / (3.0 * signed_area)
        cy = cy / (3.0 * signed_area)
    else:
        cx = sum(p[0] for p in clean_pts) / m
        cy = sum(p[1] for p in clean_pts) / m

    return area, perimeter, cx, cy


def register_dimension_tools(mcp):
    """Đăng ký các công cụ đo đạc và ghi kích thước nguyên thủy vào MCP Server."""

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
    def measure_area(
        points: Optional[List[List[float]]] = None,
        element_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tính toán diện tích và chu vi của một đối tượng hình học (Shape/ComplexShape/LineString)
        hoặc từ danh sách tọa độ đỉnh do người dùng truyền vào.

        :param points: Danh sách tọa độ đỉnh [[x1, y1], [x2, y2], ...] (tối thiểu 3 điểm)
        :param element_id: ID của phần tử hình học đã có trong bản vẽ (ví dụ: '233345')
        """
        pts = points

        if element_id:
            el = bridge.find_element_by_id(element_id)
            if not el:
                return {"error": f"Không tìm thấy phần tử có ID '{element_id}' trong bản vẽ!"}

            # Thử lấy trực tiếp từ thuộc tính ClosedElement nếu có
            try:
                if getattr(el, "IsClosedElement", lambda: False)():
                    area = float(el.Area())
                    perimeter = float(el.Perimeter())
                    pts = _get_polygon_from_element(el)
                    return {
                        "element_id": str(element_id),
                        "type": getattr(el, "Type", None),
                        "level": el.Level.Name if el.Level else "",
                        "vertices_count": len(pts) if pts else 0,
                        "area_square_units": round(area, 4),
                        "area_hectares": round(area / 10000.0, 6),
                        "perimeter_units": round(perimeter, 4),
                    }
            except Exception:
                pass

            pts = _get_polygon_from_element(el)
            if not pts or len(pts) < 3:
                return {"error": f"Phần tử ID '{element_id}' không phải là hình khép kín hoặc không đủ đỉnh!"}

        if not pts or len(pts) < 3:
            return {"error": "Cần truyền 'element_id' hợp lệ hoặc danh sách 'points' có tối thiểu 3 điểm!"}

        area, perimeter, cx, cy = _calc_centroid_and_area(pts)

        res = {
            "vertices_count": len(pts),
            "area_square_units": round(area, 4),
            "area_hectares": round(area / 10000.0, 6),
            "perimeter_units": round(perimeter, 4),
            "centroid": [round(cx, 3), round(cy, 3)],
        }
        if element_id:
            res["element_id"] = str(element_id)
        return res

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

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return "Lỗi: Hai điểm trùng nhau, không thể ghi kích thước!"

        nx = -dy / length * offset
        ny = dx / length * offset

        p_dim = bridge.create_point(x1 + nx, y1 + ny, 0.0)

        try:
            dim_elem = bridge.unwrap(app.CreateDimensionElement1(None, matrix, 0))
            dim_elem.InsertPoint(1, p1)
            dim_elem.InsertPoint(2, p2)
            dim_elem.InsertPoint(3, p_dim)
            bridge.apply_symbology(dim_elem, level=level, color=color)
            bridge.add_element(dim_elem)
            return f"Đã tạo đường kích thước giữa ({x1}, {y1}) và ({x2}, {y2}) dài {round(length, 3)}"
        except Exception:
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

        line_elem = bridge.unwrap(app.CreateLineElement2(None, p_center, p_rim))
        bridge.apply_symbology(line_elem, level=level, color=color)
        bridge.add_element(line_elem)

        text_elem = bridge.unwrap(app.CreateTextElement1(None, f"R={round(radius, 2)}", p_rim, bridge.create_rotation_matrix(angle_deg)))
        bridge.apply_symbology(text_elem, level=level, color=color)
        bridge.add_element(text_elem)

        return f"Đã ghi chú bán kính R={radius} tại tâm ({cx}, {cy})"

    @mcp.tool
    def measure_length(element_id: str) -> Dict[str, Any]:
        """
        Đo chiều dài thực của một phần tử hình học dạng đường (Line, LineString, Arc, ComplexString, Curve).
        Tương ứng với công cụ 'Measure Length' trong Tool Box Measure.

        :param element_id: ID của phần tử cần đo
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy phần tử có ID '{element_id}'!"}

        length = 0.0
        try:
            length = float(getattr(el, "Length", 0.0))
        except Exception:
            pass

        if length <= 0:
            pts = _get_polygon_from_element(el)
            if pts and len(pts) >= 2:
                for i in range(len(pts) - 1):
                    length += math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])

        return {
            "element_id": str(element_id),
            "type": getattr(el, "Type", None),
            "level": el.Level.Name if el.Level else "",
            "length_units": round(length, 4),
        }

    @mcp.tool
    def measure_angle_between_lines(element_id1: str, element_id2: str) -> Dict[str, Any]:
        """
        Đo góc hình học giữa hai đoạn thẳng trong không gian 2D (Measure Angle Between Lines).
        Tương ứng với công cụ 'Measure Angle Between Lines' trong Tool Box Measure.

        :param element_id1: ID đoạn thẳng thứ nhất
        :param element_id2: ID đoạn thẳng thứ hai
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return {"error": f"Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"}

        pts1 = _get_polygon_from_element(el1)
        pts2 = _get_polygon_from_element(el2)
        if not pts1 or len(pts1) < 2 or not pts2 or len(pts2) < 2:
            return {"error": "Cả hai phần tử phải có tối thiểu 2 điểm để xác định phương hướng!"}

        v1_x = pts1[-1][0] - pts1[0][0]
        v1_y = pts1[-1][1] - pts1[0][1]
        v2_x = pts2[-1][0] - pts2[0][0]
        v2_y = pts2[-1][1] - pts2[0][1]

        len1 = math.hypot(v1_x, v1_y)
        len2 = math.hypot(v2_x, v2_y)
        if len1 < 1e-6 or len2 < 1e-6:
            return {"error": "Một trong hai đoạn thẳng có độ dài bằng 0!"}

        dot = (v1_x * v2_x + v1_y * v2_y) / (len1 * len2)
        dot = max(-1.0, min(1.0, dot))
        angle_rad = math.acos(dot)
        angle_deg = math.degrees(angle_rad)

        return {
            "element_id1": element_id1,
            "element_id2": element_id2,
            "angle_degrees": round(angle_deg, 3),
            "angle_radians": round(angle_rad, 5),
            "supplementary_angle_degrees": round(180.0 - angle_deg, 3),
        }

    @mcp.tool
    def dimension_angular(
        center_x: float,
        center_y: float,
        p1_x: float,
        p1_y: float,
        p2_x: float,
        p2_y: float,
        offset_radius: float = 5.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Ghi kích thước góc giữa hai tia xuất phát từ đỉnh (Dimension Angular).
        Tương ứng với công cụ 'Dimension Angular' trong Tool Box Dimensioning.

        :param center_x: Tọa độ X đỉnh góc
        :param center_y: Tọa độ Y đỉnh góc
        :param p1_x: Tọa độ X điểm trên cạnh thứ nhất
        :param p1_y: Tọa độ Y điểm trên cạnh thứ nhất
        :param p2_x: Tọa độ X điểm trên cạnh thứ hai
        :param p2_y: Tọa độ Y điểm trên cạnh thứ hai
        :param offset_radius: Bán kính cung tròn ghi kích thước
        :param level: Tên Level
        :param color: Màu nét
        """
        app = bridge.get_app()
        ang1 = math.atan2(p1_y - center_y, p1_x - center_x)
        ang2 = math.atan2(p2_y - center_y, p2_x - center_x)

        sweep = ang2 - ang1
        while sweep < 0:
            sweep += 2 * math.pi
        while sweep > 2 * math.pi:
            sweep -= 2 * math.pi

        center = bridge.create_point(center_x, center_y, 0.0)
        matrix = bridge.create_rotation_matrix(0.0)

        arc = bridge.unwrap(app.CreateArcElement2(None, center, offset_radius, offset_radius, matrix, ang1, sweep))
        bridge.apply_symbology(arc, level=level, color=color)
        bridge.add_element(arc)

        mid_angle = ang1 + sweep / 2.0
        tx = center_x + (offset_radius + 1.5) * math.cos(mid_angle)
        ty = center_y + (offset_radius + 1.5) * math.sin(mid_angle)
        deg_val = round(math.degrees(sweep), 1)

        text_elem = bridge.unwrap(app.CreateTextElement1(None, f"{deg_val}°", bridge.create_point(tx, ty, 0.0), matrix))
        bridge.apply_symbology(text_elem, level=level, color=color)
        bridge.add_element(text_elem)

        return f"Đã ghi kích thước góc {deg_val}° tại đỉnh ({center_x}, {center_y})"

    @mcp.tool
    def dimension_element(
        element_id: str,
        offset: float = 3.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Ghi kích thước tự động cho một phần tử (Dimension Element).
        Tương ứng với công cụ 'Dimension Element' trong Tool Box Dimensioning.

        :param element_id: ID phần tử cần ghi kích thước
        :param offset: Khoảng cách dịch đường kích thước
        :param level: Tên Level
        :param color: Màu nét
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        pts = _get_polygon_from_element(el)
        if not pts or len(pts) < 2:
            return "Lỗi: Phần tử không có đủ điểm để ghi kích thước!"

        return dimension_linear(
            x1=pts[0][0],
            y1=pts[0][1],
            x2=pts[1][0],
            y2=pts[1][1],
            offset=offset,
            level=level,
            color=color,
        )

