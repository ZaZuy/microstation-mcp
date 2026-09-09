"""
src/tools/dimension.py
Các công cụ đo đạc, đo khoảng cách, diện tích và ghi kích thước (Dimensioning) trong MicroStation V8i.
"""

import math
import os
from collections import defaultdict
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
            ce = el.AsComplexStringElement() if el_type == 12 else el.AsComplexShapeElement()
            ee = ce.Drop()
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
    """Tính (area, perimeter, cx, cy) từ danh sách đỉnh."""
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


def _dist_point_to_segment(px, py, x1, y1, x2, y2) -> float:
    dx = x2 - x1
    dy = y2 - y1
    l2 = dx * dx + dy * dy
    if l2 < 1e-8:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _max_deviation(poly1: List[List[float]], poly2: List[List[float]]) -> float:
    """Tính độ lệch lớn nhất từ các đỉnh poly1 đến các cạnh poly2."""
    max_d = 0.0
    n2 = len(poly2)
    for p in poly1:
        px, py = p[0], p[1]
        min_d = float("inf")
        for i in range(n2):
            j = (i + 1) % n2
            d = _dist_point_to_segment(px, py, poly2[i][0], poly2[i][1], poly2[j][0], poly2[j][1])
            if d < min_d:
                min_d = d
        if min_d > max_d:
            max_d = min_d
    return max_d


def _calc_polygon_area(poly: List[List[float]]) -> float:
    n = len(poly)
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        a += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
    return abs(a) / 2.0


def _point_in_polygon(px: float, py: float, poly: List[List[float]]) -> bool:
    inside = False
    n = len(poly)
    if n < 3:
        return False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if min(p1y, p2y) < py <= max(p1y, p2y):
            if px <= max(p1x, p2x):
                xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y + 1e-12) + p1x
                if p1x == p2x or px <= xinters:
                    inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _topological_chain_polygon(segments, seed_x: float, seed_y: float, tol: float = 0.08) -> Optional[List[List[float]]]:
    nodes = []

    def get_node(pt):
        for i, n in enumerate(nodes):
            if math.hypot(n[0] - pt[0], n[1] - pt[1]) < tol:
                return i
        nodes.append(pt)
        return len(nodes) - 1

    adj = defaultdict(set)
    for p1, p2 in segments:
        n1 = get_node(p1)
        n2 = get_node(p2)
        if n1 != n2:
            adj[n1].add(n2)
            adj[n2].add(n1)

    cycles = []

    def find_cycles_dfs(curr, start, path, max_depth=35):
        if len(path) > max_depth:
            return
        for nxt in adj[curr]:
            if nxt == start and len(path) >= 3:
                cycles.append(list(path))
            elif nxt not in path:
                find_cycles_dfs(nxt, start, path + [nxt], max_depth)

    for start_node in range(len(nodes)):
        find_cycles_dfs(start_node, start_node, [start_node])

    best_poly = None
    min_area = float("inf")
    for c_indices in cycles:
        poly = [list(nodes[idx]) for idx in c_indices]
        area = _calc_polygon_area(poly)
        if area > 1.0:
            if _point_in_polygon(seed_x, seed_y, poly):
                if area < min_area:
                    min_area = area
                    best_poly = poly
    return best_poly


def _extract_parcel_polygon_at(model, seed_x: float, seed_y: float, search_radius: float = 35.0, preferred_level: Optional[str] = None) -> Optional[List[List[float]]]:
    """Tìm và trích xuất đa giác thửa đất khép kín chứa hạt giống (seed_x, seed_y) trong model DGN bất kỳ."""
    cache = model.GraphicalElementCache
    min_x = seed_x - search_radius
    max_x = seed_x + search_radius
    min_y = seed_y - search_radius
    max_y = seed_y + search_radius

    best_poly = None
    min_area = float("inf")
    level_matched_poly = None
    level_matched_min_area = float("inf")
    segments = []

    for idx in range(1, cache.Count + 1):
        try:
            el = cache.GetElement(idx)
            if not el:
                continue
            rng = el.Range
            if rng.High.X < min_x or rng.Low.X > max_x or rng.High.Y < min_y or rng.Low.Y > max_y:
                continue

            el_type = int(el.Type)
            is_level_match = bool(preferred_level and getattr(el, "Level", None) and el.Level.Name.strip().lower() == preferred_level.strip().lower())

            # Kiểm tra Shape (6), LineString (4), ComplexShape (14)
            if el_type in (4, 6, 12, 14):
                poly = _get_polygon_from_element(el)
                if poly and len(poly) >= 3:
                    # Kiểm tra xem có khép kín hay không (hoặc gần khép kín trong 0.25m)
                    if math.hypot(poly[0][0] - poly[-1][0], poly[0][1] - poly[-1][1]) < 0.25:
                        area = _calc_polygon_area(poly)
                        if 1.0 < area < 5000.0 and _point_in_polygon(seed_x, seed_y, poly):
                            if is_level_match and area < level_matched_min_area:
                                level_matched_min_area = area
                                level_matched_poly = poly
                            if area < min_area:
                                min_area = area
                                best_poly = poly

            # Đồng thời gom các đoạn Line/LineString để phòng trường hợp thửa ghép từ nhiều đoạn rời
            if el_type == 3:  # Line
                try:
                    le = getattr(el, "AsLineElement", None)
                    le = le() if callable(le) else le
                    p1 = (round(le.StartPoint.X, 4), round(le.StartPoint.Y, 4))
                    p2 = (round(le.EndPoint.X, 4), round(le.EndPoint.Y, 4))
                    segments.append((p1, p2))
                except Exception:
                    pass
            elif el_type == 4 or getattr(el, "IsVertexList", False):  # LineString / VertexList
                try:
                    vl = getattr(el, "AsVertexList", None)
                    vl = vl() if callable(vl) else vl
                    v_raw = vl.GetVertices()
                    pts_ls = [(round(p.X, 4), round(p.Y, 4)) for p in v_raw]
                    for vi in range(len(pts_ls) - 1):
                        segments.append((pts_ls[vi], pts_ls[vi + 1]))
                except Exception:
                    pass
            elif el_type == 6:  # Shape
                try:
                    se = getattr(el, "AsShapeElement", None)
                    se = se() if callable(se) else se
                    pts_s = []
                    try:
                        vc = getattr(se, "VerticesCount", 0)
                        for vi in range(1, vc + 1):
                            pt = se.Vertex(vi)
                            pts_s.append((round(pt.X, 4), round(pt.Y, 4)))
                    except Exception:
                        pass
                    if not pts_s:
                        raw = se.GetVertices()
                        pts_s = [(round(p.X, 4), round(p.Y, 4)) for p in raw]
                    for vi in range(len(pts_s) - 1):
                        segments.append((pts_s[vi], pts_s[vi + 1]))
                except Exception:
                    pass
        except Exception:
            continue

    if level_matched_poly:
        return level_matched_poly

    if best_poly:
        return best_poly

    if segments:
        try:
            from shapely.ops import polygonize
            from shapely.geometry import LineString as SLineString, Point as SPoint
            pt = SPoint(seed_x, seed_y)
            matched_polys = []
            for sp in polygonize([SLineString([p1, p2]) for p1, p2 in segments]):
                if 1.0 < sp.area < 5000.0 and (sp.contains(pt) or sp.distance(pt) < 0.1):
                    matched_polys.append(sp)
            if matched_polys:
                matched_polys.sort(key=lambda p: p.area)
                return [[round(x, 4), round(y, 4)] for x, y in matched_polys[0].exterior.coords]
        except Exception:
            pass
        return _topological_chain_polygon(segments, seed_x, seed_y)

    return None


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
    def compare_parcels(
        element_id_1: str,
        element_id_2: str,
        tolerance: float = 0.05,
    ) -> Dict[str, Any]:
        """
        So sánh chi tiết 2 thửa đất (ví dụ: thửa đo đạc hiện trạng vs thửa trích lục bản đồ địa chính).
        Tính toán chênh lệch diện tích (ΔS), chu vi (ΔP), độ lệch tâm (Centroid offset),
        độ lệch ranh giới lớn nhất (Max deviation), và đánh giá mức độ trùng khớp.

        :param element_id_1: ID phần tử thửa đất thứ 1 (ví dụ: '233345')
        :param element_id_2: ID phần tử thửa đất thứ 2
        :param tolerance: Dung sai cho phép tính bằng mét (mặc định 0.05m = 5cm)
        """
        el1 = bridge.find_element_by_id(element_id_1)
        if not el1:
            return {"error": f"Không tìm thấy thửa đất thứ 1 có ID '{element_id_1}'"}

        el2 = bridge.find_element_by_id(element_id_2)
        if not el2:
            return {"error": f"Không tìm thấy thửa đất thứ 2 có ID '{element_id_2}'"}

        pts1 = _get_polygon_from_element(el1)
        pts2 = _get_polygon_from_element(el2)

        if not pts1 or len(pts1) < 3:
            return {"error": f"Thửa 1 (ID {element_id_1}) không thể trích xuất đa giác khép kín!"}
        if not pts2 or len(pts2) < 3:
            return {"error": f"Thửa 2 (ID {element_id_2}) không thể trích xuất đa giác khép kín!"}

        s1, p1, cx1, cy1 = _calc_centroid_and_area(pts1)
        s2, p2, cx2, cy2 = _calc_centroid_and_area(pts2)

        delta_s = round(s1 - s2, 4)
        pct_s = round((abs(delta_s) / s2 * 100.0) if s2 > 1e-6 else 0.0, 2)
        delta_p = round(p1 - p2, 4)
        centroid_shift = round(math.hypot(cx1 - cx2, cy1 - cy2), 4)

        dev_1_to_2 = _max_deviation(pts1, pts2)
        dev_2_to_1 = _max_deviation(pts2, pts1)
        max_boundary_deviation = round(max(dev_1_to_2, dev_2_to_1), 4)

        # Đánh giá kết quả
        if abs(delta_s) <= tolerance and centroid_shift <= tolerance and max_boundary_deviation <= tolerance:
            status = "HOÀN TOÀN TRÙNG KHỚP (100% Khớp ranh giới & diện tích)"
        elif centroid_shift <= 1.0 and max_boundary_deviation <= 0.5:
            status = "GẦN TRÙNG KHỚP (Có sai lệch nhỏ ranh giới hoặc diện tích)"
        elif centroid_shift <= 5.0:
            status = "TRÙNG VỊ TRÍ (Ranh giới có sai khác đáng kể)"
        else:
            status = "KHÔNG TRÙNG NHAU (Hai vị trí hoàn toàn khác nhau)"

        report_md = (
            f"### Kết Quả So Sánh 2 Thửa Đất\n"
            f"- **Thửa 1 (ID: {element_id_1}, Level: {el1.Level.Name if el1.Level else ''}):**\n"
            f"  - Diện tích: **{round(s1, 2)} m²** | Chu vi: {round(p1, 2)} m | Số đỉnh: {len(pts1)}\n"
            f"  - Tâm thửa: ({round(cx1, 2)}, {round(cy1, 2)})\n"
            f"- **Thửa 2 (ID: {element_id_2}, Level: {el2.Level.Name if el2.Level else ''}):**\n"
            f"  - Diện tích: **{round(s2, 2)} m²** | Chu vi: {round(p2, 2)} m | Số đỉnh: {len(pts2)}\n"
            f"  - Tâm thửa: ({round(cx2, 2)}, {round(cy2, 2)})\n"
            f"- **Chênh lệch & Sai số:**\n"
            f"  - Chênh lệch diện tích: **ΔS = {delta_s:+g} m²** ({pct_s}%)\n"
            f"  - Chênh lệch chu vi: **ΔP = {delta_p:+g} m**\n"
            f"  - Độ lệch tâm thửa: **{centroid_shift} m**\n"
            f"  - Sai lệch ranh giới lớn nhất: **{max_boundary_deviation} m**\n"
            f"- **Đánh giá:** **{status}**\n"
        )

        return {
            "status": status,
            "parcel_1": {
                "id": str(element_id_1),
                "level": el1.Level.Name if el1.Level else "",
                "area_m2": round(s1, 4),
                "perimeter_m": round(p1, 4),
                "vertices_count": len(pts1),
                "centroid": [round(cx1, 3), round(cy1, 3)],
            },
            "parcel_2": {
                "id": str(element_id_2),
                "level": el2.Level.Name if el2.Level else "",
                "area_m2": round(s2, 4),
                "perimeter_m": round(p2, 4),
                "vertices_count": len(pts2),
                "centroid": [round(cx2, 3), round(cy2, 3)],
            },
            "comparison": {
                "delta_area_m2": delta_s,
                "percent_area_diff": pct_s,
                "delta_perimeter_m": delta_p,
                "centroid_shift_m": centroid_shift,
                "max_boundary_deviation_m": max_boundary_deviation,
            },
            "summary_report": report_md,
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

    @mcp.tool
    def analyze_parcel_overlap(
        seed_x: Optional[float] = None,
        seed_y: Optional[float] = None,
        reference_file: Optional[str] = None,
        parcel_level: Optional[str] = None,
        search_radius: float = 35.0,
        target_level_surplus: str = "Level 11",
        target_level_deficit: str = "Level 12",
        surplus_color: int = 4,
        deficit_color: int = 3,
        fill_mode: str = "outline",
        auto_label: bool = True,
        text_height: float = 0.35,
    ) -> Dict[str, Any]:
        """
        Tự động tìm thửa đất trong file reference đang đè trùng với thửa đất trên file hiện tại.
        Phần diện tích trùng nhau thì để rỗng (không tô màu / none).
        Tự động bóc tách các mẩu thừa (Dư) và mẩu thiếu (Thiếu) ra 2 màu riêng biệt (mặc định Vàng và Đỏ),
        vẽ viền hoặc đổ màu và đánh số diện tích (m²) cho từng mẩu.
        Chạy 100% ngầm siêu tốc, KHÔNG đổi file bản vẽ, KHÔNG chuyển đổi khung nhìn.

        :param seed_x: Tọa độ X hạt giống (nếu None sẽ tự động lấy tâm màn hình hoặc tâm thửa hiện tại)
        :param seed_y: Tọa độ Y hạt giống
        :param reference_file: Đường dẫn file reference (nếu None tự động dò file reference đính kèm)
        :param parcel_level: Tên level của thửa đất (ví dụ: 'Level 10')
        :param search_radius: Bán kính tìm kiếm quanh điểm hạt giống (mặc định 35m)
        :param target_level_surplus: Level chứa các mẩu Dư (mặc định 'Level 11')
        :param target_level_deficit: Level chứa các mẩu Thiếu (mặc định 'Level 12')
        :param surplus_color: Màu các mẩu Dư (mặc định 4 - Vàng)
        :param deficit_color: Màu các mẩu Thiếu (mặc định 3 - Đỏ)
        :param fill_mode: Kiểu thể hiện ('outline': chỉ vẽ viền không fill, 'solid': đổ màu kín, 'none': chỉ vẽ viền)
        :param auto_label: Tự động ghi nhãn text diện tích (m²) vào tâm từng mẩu
        :param text_height: Chiều cao chữ ghi chú
        """
        app = bridge.get_app()
        active_dgn = bridge.get_active_file()
        active_model = bridge.get_active_model()
        cur_dir = os.path.dirname(getattr(active_dgn, "FullName", ""))

        # 1. Tự động xác định tọa độ hạt giống nếu chưa truyền
        if seed_x is None or seed_y is None:
            if parcel_level:
                try:
                    sc = active_model.GraphicalElementCache
                    for idx in range(1, sc.Count + 1):
                        el = sc.GetElement(idx)
                        if el and getattr(el, "Level", None) and el.Level.Name.strip().lower() == parcel_level.strip().lower():
                            if int(el.Type) in (4, 6, 12, 14):
                                rng = el.Range
                                seed_x = (rng.Low.X + rng.High.X) / 2.0
                                seed_y = (rng.Low.Y + rng.High.Y) / 2.0
                                break
                except Exception:
                    pass
            if seed_x is None or seed_y is None:
                try:
                    v1 = active_dgn.Views(1)
                    if v1.IsOpen:
                        seed_x = v1.Origin.X + v1.Extents.X / 2.0
                        seed_y = v1.Origin.Y + v1.Extents.Y / 2.0
                except Exception:
                    pass

        if seed_x is None or seed_y is None:
            return {"error": "Không thể tự xác định điểm hạt giống. Vui lòng cung cấp seed_x, seed_y!"}

        # 2. Xác định file Reference đính kèm
        ref_path = None
        if reference_file:
            if os.path.isabs(reference_file) and os.path.exists(reference_file):
                ref_path = reference_file
            elif cur_dir:
                cand = os.path.join(cur_dir, os.path.basename(reference_file))
                if os.path.exists(cand):
                    ref_path = cand

        if not ref_path:
            attachments = active_model.Attachments
            for i in range(1, attachments.Count + 1):
                try:
                    att = attachments.Item(i)
                    aname = getattr(att, "AttachName", "")
                    if cur_dir:
                        cand = os.path.join(cur_dir, os.path.basename(aname))
                        if os.path.exists(cand):
                            ref_path = cand
                            break
                    if os.path.exists(aname):
                        ref_path = aname
                        break
                except Exception:
                    continue

        if not ref_path or not os.path.exists(ref_path):
            return {"error": "Không tìm thấy file tham chiếu (Reference) nào đang đính kèm hoặc đường dẫn không hợp lệ!"}

        # 3. Trích xuất ranh giới thửa file hiện tại
        poly_active = _extract_parcel_polygon_at(active_model, seed_x, seed_y, search_radius, preferred_level=parcel_level)
        if not poly_active or len(poly_active) < 3:
            return {"error": f"Không thể trích xuất ranh giới thửa đất hiện tại quanh tọa độ ({round(seed_x, 2)}, {round(seed_y, 2)})!"}

        # 4. Trích xuất ranh giới thửa trong file reference ở chế độ nền (Background - không switch view)
        bg_dgn = None
        poly_ref = None
        try:
            bg_dgn = app.OpenDesignFileForProgram(ref_path, True)
            bg_model = bg_dgn.DefaultModelReference
            poly_ref = _extract_parcel_polygon_at(bg_model, seed_x, seed_y, search_radius, preferred_level=parcel_level)
        finally:
            if bg_dgn:
                try:
                    bg_dgn.Close()
                except Exception:
                    pass

        if not poly_ref or len(poly_ref) < 3:
            return {"error": f"Không thể trích xuất ranh giới thửa đất từ file tham chiếu '{os.path.basename(ref_path)}' quanh tọa độ ({round(seed_x, 2)}, {round(seed_y, 2)})!"}

        # 5. Phân tích hình học bằng Shapely
        from shapely.geometry import Polygon, MultiPolygon
        from shapely.validation import make_valid

        p_act = make_valid(Polygon(poly_active))
        p_ref = make_valid(Polygon(poly_ref))

        if not p_act.is_valid or p_act.is_empty:
            return {"error": "Đa giác thửa hiện tại không hợp lệ!"}
        if not p_ref.is_valid or p_ref.is_empty:
            return {"error": "Đa giác thửa tham chiếu không hợp lệ!"}

        area_active = round(p_act.area, 3)
        area_ref = round(p_ref.area, 3)

        # Phần trùng nhau (intersection)
        p_inter = p_act.intersection(p_ref)
        inter_area = round(p_inter.area, 3) if not p_inter.is_empty else 0.0

        # Mẩu Dư (Active \ Ref)
        p_surplus = p_act.difference(p_ref)

        # Mẩu Thiếu (Ref \ Active)
        p_deficit = p_ref.difference(p_act)

        def _get_clean_polys(geom, min_area=0.01):
            if geom.is_empty:
                return []
            res = []
            if isinstance(geom, Polygon):
                if geom.area >= min_area:
                    res.append(geom)
            elif isinstance(geom, MultiPolygon):
                for g in geom.geoms:
                    if g.area >= min_area:
                        res.append(g)
            return res

        surplus_geoms = _get_clean_polys(p_surplus)
        deficit_geoms = _get_clean_polys(p_deficit)

        # 6. Vẽ các mẩu kết quả vào bản vẽ hiện hành
        is_filled = (fill_mode.lower() == "solid")
        created_elements = []
        surplus_details = []
        deficit_details = []

        # Vẽ các mẩu Dư (Vàng)
        for i, g in enumerate(surplus_geoms, 1):
            coords = list(g.exterior.coords)
            pt_objs = [bridge.create_point(x, y, 0.0) for x, y in coords]
            f_mode = 1 if is_filled else 0
            shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, f_mode))
            bridge.apply_symbology(shape_elem, level=target_level_surplus, color=surplus_color, weight=2)
            if is_filled:
                try:
                    shape_elem.FillColor = int(surplus_color)
                except Exception:
                    pass
            bridge.add_element(shape_elem)
            eid = str(getattr(shape_elem, "ID64", getattr(shape_elem, "ID", "")))
            created_elements.append(eid)
            c_area = round(g.area, 3)
            cx, cy = round(g.centroid.x, 3), round(g.centroid.y, 3)

            if auto_label and c_area >= 0.01:
                t_elem = bridge.unwrap(app.CreateTextElement1(None, f"Dư: {c_area} m2", bridge.create_point(cx, cy, 0.0), bridge.create_rotation_matrix(0.0)))
                try:
                    t_elem.TextStyle.Height = float(text_height)
                    t_elem.TextStyle.Width = float(text_height)
                except Exception:
                    pass
                bridge.apply_symbology(t_elem, level=target_level_surplus, color=surplus_color)
                bridge.add_element(t_elem)
                created_elements.append(str(getattr(t_elem, "ID64", getattr(t_elem, "ID", ""))))

            surplus_details.append({"index": i, "id": eid, "area_m2": c_area, "centroid": [cx, cy]})

        # Vẽ các mẩu Thiếu (Đỏ)
        for i, g in enumerate(deficit_geoms, 1):
            coords = list(g.exterior.coords)
            pt_objs = [bridge.create_point(x, y, 0.0) for x, y in coords]
            f_mode = 1 if is_filled else 0
            shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, f_mode))
            bridge.apply_symbology(shape_elem, level=target_level_deficit, color=deficit_color, weight=2)
            if is_filled:
                try:
                    shape_elem.FillColor = int(deficit_color)
                except Exception:
                    pass
            bridge.add_element(shape_elem)
            eid = str(getattr(shape_elem, "ID64", getattr(shape_elem, "ID", "")))
            created_elements.append(eid)
            c_area = round(g.area, 3)
            cx, cy = round(g.centroid.x, 3), round(g.centroid.y, 3)

            if auto_label and c_area >= 0.01:
                t_elem = bridge.unwrap(app.CreateTextElement1(None, f"Thiếu: {c_area} m2", bridge.create_point(cx, cy, 0.0), bridge.create_rotation_matrix(0.0)))
                try:
                    t_elem.TextStyle.Height = float(text_height)
                    t_elem.TextStyle.Width = float(text_height)
                except Exception:
                    pass
                bridge.apply_symbology(t_elem, level=target_level_deficit, color=deficit_color)
                bridge.add_element(t_elem)
                created_elements.append(str(getattr(t_elem, "ID64", getattr(t_elem, "ID", ""))))

            deficit_details.append({"index": i, "id": eid, "area_m2": c_area, "centroid": [cx, cy]})

        # Luôn bật hiển thị các level kết quả trong tất cả các View
        try:
            for lvl_to_show in [target_level_surplus, target_level_deficit]:
                try:
                    lvl_obj = active_dgn.Levels(lvl_to_show)
                except Exception:
                    lvl_obj = None
                if lvl_obj:
                    for vi in range(1, active_dgn.Views.Count + 1):
                        try:
                            active_dgn.Views(vi).ShowLevel(lvl_obj)
                        except Exception:
                            pass
                    lvl_obj.IsDisplayed = True
            active_dgn.RewriteLevels()
        except Exception:
            pass

        # Cập nhật và vẽ lại khung nhìn
        try:
            app.CadInputQueue.SendKeyin("update all")
            for vi in range(1, active_dgn.Views.Count + 1):
                try:
                    active_dgn.Views(vi).Redraw()
                except Exception:
                    pass
        except Exception:
            pass

        total_surplus = round(sum(d["area_m2"] for d in surplus_details), 3)
        total_deficit = round(sum(d["area_m2"] for d in deficit_details), 3)

        report_md = (
            f"### Kết Quả Tự Động Bóc Tách Chênh Lệch Thửa Đất\n"
            f"- **Thửa hiện tại:** S = **{area_active} m²**\n"
            f"- **Thửa tham chiếu (Reference):** S = **{area_ref} m²** (File: `{os.path.basename(ref_path)}`)\n"
            f"- **Phần trùng khớp:** S = **{inter_area} m²** (giữ rỗng, không vẽ đè)\n"
            f"- **Phần DƯ (Vàng):** {len(surplus_details)} mẩu, tổng **{total_surplus} m²**\n"
            f"- **Phần THIẾU (Đỏ):** {len(deficit_details)} mẩu, tổng **{total_deficit} m²**\n"
            f"- **Trạng thái:** Đã vẽ trực tiếp các mẩu vào bản vẽ hiện tại (100% ngầm, không switch view)."
        )

        return {
            "status": "success",
            "summary": report_md,
            "area_active_m2": area_active,
            "area_reference_m2": area_ref,
            "area_intersection_m2": inter_area,
            "surplus_pieces": surplus_details,
            "deficit_pieces": deficit_details,
            "created_element_ids": created_elements,
        }

    @mcp.tool
    def create_final_parcel(
        seed_x: Optional[float] = None,
        seed_y: Optional[float] = None,
        search_radius: float = 35.0,
        target_level: str = "Level 11",
        color: int = 3,
        weight: int = 2,
        delete_inner_elements: bool = True,
        auto_label: bool = True,
        text_height: float = 0.4,
        simplify_tolerance: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Tạo thửa đất T3 (kết quả cuối cùng sau khi so sánh và giữ lại các phần diện tích).
        Chỉ vẽ đúng 1 LineString/Shape duy nhất bao trọn đường viền ngoài cùng của thửa kết quả,
        và tự động xóa sạch toàn bộ các đường nét (line đỏ/xanh) hoặc text thừa nằm bên trong.

        :param seed_x: Tọa độ X hạt giống (nếu None tự động lấy tâm View 1)
        :param seed_y: Tọa độ Y hạt giống
        :param search_radius: Bán kính tìm kiếm (mặc định 35m)
        :param target_level: Level lưu ranh giới thửa kết quả (mặc định 'Level 11')
        :param color: Màu nét vẽ ranh giới ngoài cùng (mặc định 3 - Đỏ)
        :param weight: Độ dày nét (mặc định 2)
        :param delete_inner_elements: Tự động xóa sạch các đường line/mẩu thừa nằm bên trong ranh giới
        :param auto_label: Tự động ghi nhãn tổng diện tích (m²) vào tâm thửa
        :param text_height: Chiều cao text nhãn diện tích
        :param simplify_tolerance: Dung sai nắn thẳng các gờ răng cưa nhỏ (mặc định 0.05m = 5cm)
        """
        app = bridge.get_app()
        active_dgn = bridge.get_active_file()
        active_model = bridge.get_active_model()
        cache = active_model.GraphicalElementCache

        if seed_x is None or seed_y is None:
            try:
                v1 = active_dgn.Views(1)
                if v1.IsOpen:
                    seed_x = v1.Origin.X + v1.Extents.X / 2.0
                    seed_y = v1.Origin.Y + v1.Extents.Y / 2.0
            except Exception:
                pass

        if seed_x is None or seed_y is None:
            return {"error": "Vui lòng cung cấp tọa độ seed_x, seed_y!"}

        min_x = seed_x - search_radius
        max_x = seed_x + search_radius
        min_y = seed_y - search_radius
        max_y = seed_y + search_radius

        from shapely.geometry import Polygon, MultiPolygon, Point
        from shapely.ops import unary_union
        from shapely.validation import make_valid

        # 1. Thu thập tất cả đa giác trong phạm vi
        polys_to_merge = []
        inner_candidate_elements = []

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
                if not el:
                    continue
                rng = el.Range
                if rng.High.X < min_x or rng.Low.X > max_x or rng.High.Y < min_y or rng.Low.Y > max_y:
                    continue

                el_type = int(el.Type)
                if el_type in (3, 4, 6, 12, 14, 17):
                    inner_candidate_elements.append(el)

                if el_type in (4, 6, 12, 14):
                    poly_pts = _get_polygon_from_element(el)
                    if poly_pts and len(poly_pts) >= 3:
                        poly_obj = make_valid(Polygon(poly_pts))
                        if poly_obj.is_valid and poly_obj.area > 0.01:
                            polys_to_merge.append(poly_obj)
            except Exception:
                continue

        if not polys_to_merge:
            return {"error": "Không tìm thấy đa giác nào để hợp nhất thành thửa kết quả!"}

        # 2. Hợp nhất thành đa giác ngoài cùng
        merged = unary_union(polys_to_merge)
        if isinstance(merged, MultiPolygon):
            best_g = None
            max_a = 0.0
            for g in merged.geoms:
                if g.area > max_a:
                    max_a = g.area
                    best_g = g
            merged = best_g if best_g else merged.geoms[0]

        if simplify_tolerance > 0:
            merged = merged.simplify(simplify_tolerance, preserve_topology=True)

        outer_coords = list(merged.exterior.coords)
        final_area = round(merged.area, 3)
        cx, cy = round(merged.centroid.x, 3), round(merged.centroid.y, 3)

        # 3. Vẽ đường viền ngoài cùng duy nhất (LineString khép kín)
        pt_objs = [bridge.create_point(x, y, 0.0) for x, y in outer_coords]
        line_elem = bridge.unwrap(app.CreateLineElement1(None, pt_objs))
        bridge.apply_symbology(line_elem, level=target_level, color=color, weight=weight)
        bridge.add_element(line_elem)
        new_id = str(getattr(line_elem, "ID64", getattr(line_elem, "ID", "")))

        # 4. Xóa sạch các đối tượng bên trong ranh giới nếu được yêu cầu
        deleted_count = 0
        if delete_inner_elements:
            check_geom = merged.buffer(-0.02)
            for el in inner_candidate_elements:
                try:
                    eid = str(getattr(el, "ID64", getattr(el, "ID", "")))
                    if eid == new_id:
                        continue
                    rng = el.Range
                    mid_x = (rng.Low.X + rng.High.X) / 2.0
                    mid_y = (rng.Low.Y + rng.High.Y) / 2.0
                    if check_geom.contains(Point(mid_x, mid_y)):
                        active_model.RemoveElement(el)
                        deleted_count += 1
                except Exception:
                    continue

        # 5. Ghi nhãn diện tích
        if auto_label:
            t_elem = bridge.unwrap(app.CreateTextElement1(None, f"S = {final_area} m2", bridge.create_point(cx, cy, 0.0), bridge.create_rotation_matrix(0.0)))
            try:
                t_elem.TextStyle.Height = float(text_height)
                t_elem.TextStyle.Width = float(text_height)
            except Exception:
                pass
            bridge.apply_symbology(t_elem, level=target_level, color=color)
            bridge.add_element(t_elem)

        # 6. Căn vừa khung nhìn
        try:
            app.CadInputQueue.SendKeyin("fit all")
            app.CadInputQueue.SendKeyin("update all")
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Đã tạo thửa kết quả T3 (ID {new_id}) diện tích {final_area} m² và xóa {deleted_count} đối tượng thừa bên trong.",
            "final_parcel": {
                "id": new_id,
                "area_m2": final_area,
                "centroid": [cx, cy],
                "vertices_count": len(outer_coords),
                "deleted_inner_elements_count": deleted_count,
            },
        }

