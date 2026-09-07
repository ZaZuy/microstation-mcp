"""
src/tools/drawing.py
Các công cụ vẽ hình học trong MicroStation V8i cho AI.
Bao gồm: đoạn thẳng, polyline, đa giác, hình chữ nhật, đường tròn, cung tròn, elip, điểm mốc, đường cong, cell.
"""

import math
from typing import List, Optional, Any
from src.core.ms_bridge import bridge


def register_drawing_tools(mcp):
    """Đăng ký các tool vẽ hình học vào MCP Server."""

    @mcp.tool
    def draw_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        z1: float = 0.0,
        z2: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ một đoạn thẳng (Line) giữa 2 điểm trong MicroStation V8i.

        :param x1: Tọa độ X điểm đầu
        :param y1: Tọa độ Y điểm đầu
        :param x2: Tọa độ X điểm cuối
        :param y2: Tọa độ Y điểm cuối
        :param z1: Tọa độ Z điểm đầu (mặc định 0.0)
        :param z2: Tọa độ Z điểm cuối (mặc định 0.0)
        :param level: Tên Level để đặt phần tử (ví dụ: 'Default', 'ThietKe'...)
        :param color: Chỉ số màu (0-255)
        :param weight: Độ dày nét (0-31)
        :param style: Kiểu nét (0=solid, 1=dash, 2=dot...)
        """
        app = bridge.get_app()
        p1 = bridge.create_point(x1, y1, z1)
        p2 = bridge.create_point(x2, y2, z2)

        line_elem = bridge.unwrap(app.CreateLineElement2(None, p1, p2))
        bridge.apply_symbology(line_elem, level=level, color=color, weight=weight, style=style)
        bridge.add_element(line_elem)

        return f"Đã vẽ đoạn thẳng từ ({x1}, {y1}) đến ({x2}, {y2})"

    @mcp.tool
    def draw_linestring(
        points: List[List[float]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ đường gấp khúc (LineString / Polyline) qua danh sách các tọa độ điểm.

        :param points: Danh sách các tọa độ [[x1, y1], [x2, y2], [x3, y3], ...]
        :param level: Tên Level
        :param color: Chỉ số màu (0-255)
        :param weight: Độ dày nét (0-31)
        :param style: Kiểu nét (0=solid, 1=dash...)
        """
        if len(points) < 2:
            return "Lỗi: Cần tối thiểu 2 điểm để vẽ linestring!"

        app = bridge.get_app()
        pt_objs = []
        for pt in points:
            x = float(pt[0])
            y = float(pt[1])
            z = float(pt[2]) if len(pt) > 2 else 0.0
            pt_objs.append(bridge.create_point(x, y, z))

        linestring_elem = bridge.unwrap(app.CreateLineElement1(None, pt_objs))
        bridge.apply_symbology(linestring_elem, level=level, color=color, weight=weight, style=style)
        bridge.add_element(linestring_elem)

        return f"Đã vẽ linestring với {len(points)} điểm"

    @mcp.tool
    def draw_shape(
        points: List[List[float]],
        filled: bool = False,
        fill_color: Optional[int] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ đa giác khép kín (Shape / Polygon) trong MicroStation V8i.

        :param points: Danh sách các đỉnh [[x1, y1], [x2, y2], [x3, y3], ...] (tối thiểu 3 điểm)
        :param filled: True nếu muốn tô màu kín hình dạng
        :param fill_color: Màu tô (chỉ số màu 0-255 nếu filled=True)
        :param level: Tên Level
        :param color: Chỉ số màu viền
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if len(points) < 3:
            return "Lỗi: Cần tối thiểu 3 điểm để tạo hình đa giác!"

        app = bridge.get_app()
        pt_objs = []
        for pt in points:
            x = float(pt[0])
            y = float(pt[1])
            z = float(pt[2]) if len(pt) > 2 else 0.0
            pt_objs.append(bridge.create_point(x, y, z))

        fill_mode = 1 if filled else 0
        shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, fill_mode))
        bridge.apply_symbology(shape_elem, level=level, color=color, weight=weight, style=style)

        if filled and fill_color is not None:
            try:
                shape_elem.FillColor = int(fill_color)
            except Exception:
                pass

        bridge.add_element(shape_elem)
        return f"Đã vẽ đa giác Shape {len(points)} đỉnh thành công"

    @mcp.tool
    def draw_rectangle(
        x: float,
        y: float,
        width: float,
        height: float,
        rotation_deg: float = 0.0,
        filled: bool = False,
        fill_color: Optional[int] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ hình chữ nhật với điểm gốc (x, y) và chiều rộng (width), chiều cao (height).

        :param x: Tọa độ X góc dưới trái
        :param y: Tọa độ Y góc dưới trái
        :param width: Chiều rộng
        :param height: Chiều cao
        :param rotation_deg: Góc xoay theo độ quanh góc dưới trái (mặc định 0)
        :param filled: True nếu muốn tô màu nền hình chữ nhật
        :param fill_color: Màu nền tô
        :param level: Tên Level
        :param color: Màu viền (0-255)
        :param weight: Độ dày viền
        :param style: Kiểu viền
        """
        local_pts = [
            (0.0, 0.0),
            (width, 0.0),
            (width, height),
            (0.0, height)
        ]

        rad = math.radians(rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        global_pts = []
        for lx, ly in local_pts:
            gx = x + (lx * cos_a - ly * sin_a)
            gy = y + (lx * sin_a + ly * cos_a)
            global_pts.append([gx, gy, 0.0])

        return draw_shape(
            points=global_pts,
            filled=filled,
            fill_color=fill_color,
            level=level,
            color=color,
            weight=weight,
            style=style,
        )

    @mcp.tool
    def draw_circle(
        cx: float,
        cy: float,
        radius: float,
        cz: float = 0.0,
        filled: bool = False,
        fill_color: Optional[int] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ đường tròn (Circle) với tâm (cx, cy) và bán kính (radius).

        :param cx: Tọa độ X tâm đường tròn
        :param cy: Tọa độ Y tâm đường tròn
        :param radius: Bán kính đường tròn
        :param cz: Tọa độ Z tâm (mặc định 0.0)
        :param filled: True nếu muốn tô màu kín
        :param fill_color: Màu tô nền
        :param level: Tên Level
        :param color: Màu viền
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if radius <= 0:
            return "Lỗi: Bán kính phải lớn hơn 0!"

        app = bridge.get_app()
        center = bridge.create_point(cx, cy, cz)
        matrix = bridge.create_rotation_matrix(0.0)
        fill_mode = 1 if filled else 0

        ellipse_elem = bridge.unwrap(app.CreateEllipseElement2(None, center, radius, radius, matrix, fill_mode))
        bridge.apply_symbology(ellipse_elem, level=level, color=color, weight=weight, style=style)

        if filled and fill_color is not None:
            try:
                ellipse_elem.FillColor = int(fill_color)
            except Exception:
                pass

        bridge.add_element(ellipse_elem)
        return f"Đã vẽ đường tròn tại tâm ({cx}, {cy}) với bán kính {radius}"

    @mcp.tool
    def draw_arc(
        cx: float,
        cy: float,
        radius: float,
        start_angle_deg: float,
        sweep_angle_deg: float,
        cz: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ cung tròn (Arc) với tâm, bán kính, góc bắt đầu và góc quét.

        :param cx: Tọa độ X tâm
        :param cy: Tọa độ Y tâm
        :param radius: Bán kính
        :param start_angle_deg: Góc bắt đầu tính bằng độ (0 là hướng trục X)
        :param sweep_angle_deg: Góc quét tính bằng độ (dương là ngược chiều kim đồng hồ)
        :param cz: Tọa độ Z tâm (mặc định 0.0)
        :param level: Tên Level
        :param color: Màu nét
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        app = bridge.get_app()
        center = bridge.create_point(cx, cy, cz)
        matrix = bridge.create_rotation_matrix(0.0)

        start_rad = math.radians(start_angle_deg)
        sweep_rad = math.radians(sweep_angle_deg)

        arc_elem = bridge.unwrap(app.CreateArcElement2(None, center, radius, radius, matrix, start_rad, sweep_rad))
        bridge.apply_symbology(arc_elem, level=level, color=color, weight=weight, style=style)
        bridge.add_element(arc_elem)

        return f"Đã vẽ cung tròn tâm ({cx}, {cy}), R={radius}, start={start_angle_deg}°, sweep={sweep_angle_deg}°"

    @mcp.tool
    def draw_ellipse(
        cx: float,
        cy: float,
        primary_radius: float,
        secondary_radius: float,
        rotation_deg: float = 0.0,
        cz: float = 0.0,
        filled: bool = False,
        fill_color: Optional[int] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ hình Elip (Ellipse) trong MicroStation V8i.

        :param cx: Tọa độ X tâm
        :param cy: Tọa độ Y tâm
        :param primary_radius: Bán kính trục chính (bán trục lớn)
        :param secondary_radius: Bán kính trục phụ (bán trục bé)
        :param rotation_deg: Góc xoay của elip tính bằng độ
        :param cz: Tọa độ Z tâm
        :param filled: True nếu muốn tô màu kín
        :param fill_color: Màu nền tô
        :param level: Tên Level
        :param color: Màu viền
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if primary_radius <= 0 or secondary_radius <= 0:
            return "Lỗi: Cả hai bán kính phải lớn hơn 0!"

        app = bridge.get_app()
        center = bridge.create_point(cx, cy, cz)
        matrix = bridge.create_rotation_matrix(rotation_deg)
        fill_mode = 1 if filled else 0

        ellipse_elem = bridge.unwrap(app.CreateEllipseElement2(None, center, primary_radius, secondary_radius, matrix, fill_mode))
        bridge.apply_symbology(ellipse_elem, level=level, color=color, weight=weight, style=style)

        if filled and fill_color is not None:
            try:
                ellipse_elem.FillColor = int(fill_color)
            except Exception:
                pass

        bridge.add_element(ellipse_elem)
        return f"Đã vẽ hình elip tại tâm ({cx}, {cy}) với bán trục R1={primary_radius}, R2={secondary_radius}, góc xoay {rotation_deg}°"

    @mcp.tool
    def draw_point(
        x: float,
        y: float,
        z: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: int = 5,
    ) -> str:
        """
        Vẽ một điểm mốc / Point Marker tại tọa độ (x, y, z). Thường dùng cho mốc trắc địa, đỉnh ranh giới.

        :param x: Tọa độ X
        :param y: Tọa độ Y
        :param z: Tọa độ Z
        :param level: Tên Level
        :param color: Màu điểm
        :param weight: Độ lớn nét điểm (mặc định 5 để dễ nhìn thấy)
        """
        app = bridge.get_app()
        pt = bridge.create_point(x, y, z)

        try:
            pt_elem = bridge.unwrap(app.CreatePointMarkerElement1(None, pt, 0))
        except Exception:
            # Fallback nếu hệ thống không hỗ trợ PointMarker: vẽ đoạn thẳng độ dài 0
            pt_elem = bridge.unwrap(app.CreateLineElement2(None, pt, pt))

        bridge.apply_symbology(pt_elem, level=level, color=color, weight=weight)
        bridge.add_element(pt_elem)
        return f"Đã đặt điểm mốc tại ({x}, {y}, {z})"

    @mcp.tool
    def draw_bspline_curve(
        points: List[List[float]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ đường cong trơn (Smooth Curve / Spline) qua danh sách các điểm điều khiển hoặc nội suy.

        :param points: Danh sách tọa độ các điểm [[x1, y1], [x2, y2], ...] (tối thiểu 3 điểm)
        :param level: Tên Level
        :param color: Màu nét
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if len(points) < 3:
            return "Lỗi: Cần tối thiểu 3 điểm để dựng đường cong trơn!"

        app = bridge.get_app()
        pt_objs = []
        for pt in points:
            x = float(pt[0])
            y = float(pt[1])
            z = float(pt[2]) if len(pt) > 2 else 0.0
            pt_objs.append(bridge.create_point(x, y, z))

        curve_elem = bridge.unwrap(app.CreateCurveElement1(None, pt_objs))
        bridge.apply_symbology(curve_elem, level=level, color=color, weight=weight, style=style)
        bridge.add_element(curve_elem)

        return f"Đã vẽ đường cong trơn qua {len(points)} điểm"

    @mcp.tool
    def place_cell(
        cell_name: str,
        x: float,
        y: float,
        scale: float = 1.0,
        rotation_deg: float = 0.0,
        level: Optional[str] = None,
    ) -> str:
        """
        Chèn một Cell (khối block ký hiệu) từ Cell Library vào bản vẽ.

        :param cell_name: Tên của Cell cần chèn
        :param x: Tọa độ X đặt cell
        :param y: Tọa độ Y đặt cell
        :param scale: Tỉ lệ phóng to/thu nhỏ (mặc định 1.0)
        :param rotation_deg: Góc xoay theo độ
        :param level: Tên Level
        """
        app = bridge.get_app()
        origin = bridge.create_point(x, y, 0.0)
        matrix = bridge.create_rotation_matrix(rotation_deg)

        try:
            scale_point = bridge.create_point(scale, scale, scale)
            cell_elem = bridge.unwrap(app.CreateCellElement2(cell_name, origin, scale_point, True, matrix))
            bridge.apply_symbology(cell_elem, level=level)
            bridge.add_element(cell_elem)
            return f"Đã chèn cell '{cell_name}' tại ({x}, {y}) với tỉ lệ {scale}"
        except Exception as ex:
            return f"Không thể chèn cell '{cell_name}'. Vui lòng kiểm tra xem cell library đã được đính kèm vào MicroStation chưa. Chi tiết: {ex}"
