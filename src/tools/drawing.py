"""
src/tools/drawing.py
Các công cụ vẽ hình học trong MicroStation V8i cho AI.
Bao gồm: đoạn thẳng, polyline, đa giác, hình chữ nhật, đường tròn, cung tròn, elip, điểm mốc, đường cong, cell.
"""

import os
import math
from collections import defaultdict
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

    @mcp.tool
    def create_region(
        method: str = "flood",
        seed_x: Optional[float] = None,
        seed_y: Optional[float] = None,
        element_ids: Optional[List[str]] = None,
        fill_type: str = "opaque",
        fill_color: int = 4,
        outline_color: Optional[int] = None,
        level: Optional[str] = None,
        keep_original: bool = True,
        auto_enable_view_fill: bool = True,
    ) -> str:
        """
        Tự động tạo vùng kín và đổ màu nền (Create Region) toàn diện trong MicroStation V8i.
        Hỗ trợ 4 phương pháp không gian: Flood (nhận diện vùng từ điểm bên trong), Union (hợp nhất các vùng),
        Intersection (giao nhau) và Difference (trừ vùng).

        :param method: Phương pháp tạo vùng ('flood', 'union', 'intersection', 'difference')
        :param seed_x: Tọa độ X điểm bên trong vùng (bắt buộc cho method='flood')
        :param seed_y: Tọa độ Y điểm bên trong vùng (bắt buộc cho method='flood')
        :param element_ids: Danh sách ID các đối tượng cần tính toán (cho method='union', 'intersection', 'difference')
        :param fill_type: Chế độ tô màu ('opaque' - tô đặc kín, 'outline' - tô đặc có viền, 'none' - rỗng)
        :param fill_color: Chỉ số màu nền tô (0-255, bảng màu chuẩn MicroStation: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
        :param outline_color: Chỉ số màu đường viền bao quanh (0-255, tùy chọn)
        :param level: Tên Level đặt đối tượng mới (mặc định giữ nguyên level active)
        :param keep_original: True nếu muốn giữ lại các đoạn ranh giới gốc
        :param auto_enable_view_fill: True để tự động bật thuộc tính hiển thị Fill trên các View của MicroStation


        """
        app = bridge.get_app()
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        count_before = cache.Count

        if auto_enable_view_fill:
            try:
                # Keyin chuẩn V8i để bật Fill cho các view đang mở (không dùng VBA)
                for vi in range(1, 9):
                    app.CadInputQueue.SendKeyin(f"view on fill {vi}")
                app.CadInputQueue.SendKeyin("update all")
            except Exception:
                pass

        ft_code = 1 if fill_type.lower() in ("opaque", "solid") else (2 if fill_type.lower() == "outline" else 0)

        # Cấu hình thuộc tính Active cho vùng mới tạo (không dùng SetCExpressionValue - gây popup)
        if level:
            app.CadInputQueue.SendKeyin(f"lv={level}")
        if outline_color is not None:
            app.CadInputQueue.SendKeyin(f"co={outline_color}")

        # Set active fill color qua keyin chuẩn (tránh VBA SetCExpressionValue)
        app.CadInputQueue.SendKeyin(f"active color {int(fill_color)}")
        app.CadInputQueue.SendKeyin(f"active fillcolor {int(fill_color)}")
        if ft_code > 0:
            app.CadInputQueue.SendKeyin("active fill on")
        else:
            app.CadInputQueue.SendKeyin("active fill off")

        m = str(method).lower().strip()
        app.CadInputQueue.SendKeyin(f"create region {m}")

        if m == "flood":
            if seed_x is None or seed_y is None:
                return "Lỗi: Phương pháp 'flood' yêu cầu cung cấp tọa độ seed_x và seed_y bên trong vùng!"
            pt = bridge.create_point(seed_x, seed_y, 0.0)
            app.CadInputQueue.SendDataPoint(pt, 1)
            app.CadInputQueue.SendDataPoint(pt, 1)
            app.CadInputQueue.SendReset()
        elif m in ("union", "intersection", "difference"):
            if not element_ids or len(element_ids) < 2:
                return f"Lỗi: Phương pháp '{method}' yêu cầu danh sách element_ids chứa tối thiểu 2 ID phần tử!"
            last_pt = None
            for eid in element_ids:
                el = bridge.find_element_by_id(eid)
                if el:
                    rng = el.Range
                    last_pt = bridge.create_point((rng.Low.X + rng.High.X) / 2.0, (rng.Low.Y + rng.High.Y) / 2.0, 0.0)
                    app.CadInputQueue.SendDataPoint(last_pt, 1)
            if last_pt:
                app.CadInputQueue.SendDataPoint(last_pt, 1)
            app.CadInputQueue.SendReset()
        else:
            return f"Lỗi: Phương pháp '{method}' không hợp lệ! Vui lòng chọn trong: 'flood', 'union', 'intersection', 'difference'."

        count_after = cache.Count
        new_ids = []
        if count_after > count_before:
            for idx in range(count_before + 1, count_after + 1):
                try:
                    el = cache.GetElement(idx)
                    if not el:
                        continue
                    eid = str(getattr(el, "ID64", getattr(el, "ID", "")))
                    if not eid:
                        continue
                    new_ids.append(eid)

                    if getattr(el, "IsClosedElement", False):
                        try:
                            closed = el.AsClosedElement()
                            closed.FillMode = ft_code
                            closed.FillColor = int(fill_color)
                            if outline_color is not None:
                                el.Color = int(outline_color)
                            closed.Rewrite()
                            closed.Redraw()
                        except Exception:
                            pass

                    # Đồng thời gửi lệnh VBA chuẩn để đảm bảo MicroStation cập nhật triệt để
                    outline_cmd = f"oEl.Color = {int(outline_color)}: " if outline_color is not None else ""
                    app.CadInputQueue.SendKeyin(
                        f"vba execute On Error Resume Next: Dim oEl As Element: Set oEl = ActiveModelReference.GetElementByID(DLongFromLong({eid})): "
                        f"If oEl.IsClosedElement Then "
                        f"Dim oC As ClosedElement: Set oC = oEl.AsClosedElement: "
                        f"oC.FillMode = {ft_code}: oC.FillColor = {int(fill_color)}: "
                        f"{outline_cmd}oC.Rewrite: oC.Redraw: End If"
                    )
                except Exception:
                    pass

            id_str = ", ".join(new_ids) if new_ids else "Mới"
            return f"Đã tạo vùng ({m.upper()}) thành công! Đối tượng mới ID: {id_str}, màu tô nền: {fill_color} ({fill_type}), viền: {outline_color if outline_color is not None else 'Giữ nguyên'}."

        return f"Đã gửi lệnh tạo vùng ({m.upper()}) với chế độ tô {fill_type} màu {fill_color}."

    @mcp.tool
    def flood_fill_region(
        seed_x: float,
        seed_y: float,
        fill_color: int = 4,
        fill_type: str = "opaque",
        outline_color: Optional[int] = None,
        level: Optional[str] = None,
    ) -> str:
        """
        Tự động nhận diện đường bao khép kín xung quanh một điểm tọa độ hạt giống (Seed Point)
        và đổ màu kín vào diện tích đó (tương đương công cụ Create Region Flood trong MicroStation).

        :param seed_x: Tọa độ X điểm bên trong thửa đất / vùng cần đổ màu
        :param seed_y: Tọa độ Y điểm bên trong thửa đất / vùng cần đổ màu
        :param fill_color: Chỉ số màu tô (0-255, bảng màu chuẩn MicroStation: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
        :param fill_type: Chế độ tô ('opaque' - tô đặc kín, 'outline' - tô đặc có viền, 'none')
        :param outline_color: Chỉ số màu đường viền (tùy chọn)
        :param level: Tên Level đặt đối tượng Shape tô màu (mặc định theo level active)
        """
        return create_region(
            method="flood",
            seed_x=seed_x,
            seed_y=seed_y,
            fill_type=fill_type,
            fill_color=fill_color,
            outline_color=outline_color,
            level=level,
            auto_enable_view_fill=True,
        )

    @mcp.tool
    def copy_reference_parcel(
        seed_x: float,
        seed_y: float,
        reference_file: Optional[str] = None,
        target_level: str = "Level 11",
        color: int = 3,
        weight: int = 2,
        fill_color: Optional[int] = 3,
        label_text: Optional[str] = None,
        search_radius: float = 25.0,
    ) -> str:
        """
        Sao chép và tạo Region ranh giới thửa đất từ file Reference đang đính kèm vào thẳng file hiện hành mà không cần đổi file.
        Xử lý tức thì (< 1 giây), không làm gián đoạn màn hình, tự động đóng kín các đoạn thẳng rời rạc thành Shape khép kín.

        :param seed_x: Tọa độ X của điểm nằm bên trong thửa đất
        :param seed_y: Tọa độ Y của điểm nằm bên trong thửa đất
        :param reference_file: Đường dẫn hoặc tên file Reference (nếu None sẽ tự động lấy file tham chiếu đang đính kèm)
        :param target_level: Level lưu hình thửa mới trên file hiện hành (mặc định 'Level 11')
        :param color: Chỉ số màu đường viền (mặc định 3 - Đỏ)
        :param weight: Độ dày nét vẽ (mặc định 2)
        :param fill_color: Chỉ số màu tô nền (mặc định 3 - Đỏ, None nếu rỗng)
        :param label_text: Nhãn ghi chú đặt vào tâm thửa (nếu có)
        :param search_radius: Bán kính tìm kiếm quanh điểm hạt giống (mặc định 25m)
        """
        app = bridge.get_app()
        active_dgn = bridge.get_active_file()
        active_model = bridge.get_active_model()

        # 1. Xác định đường dẫn file reference
        ref_path = None
        cur_dir = os.path.dirname(getattr(active_dgn, "FullName", ""))
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
            return "Lỗi: Không tìm thấy file tham chiếu (Reference) nào đang đính kèm hoặc đường dẫn không hợp lệ!"

        # 2. Đọc các đoạn ranh giới từ file reference ở chế độ nền (Background)
        bg_dgn = None
        segments = []
        try:
            bg_dgn = app.OpenDesignFileForProgram(ref_path, True)
            bg_model = bg_dgn.DefaultModelReference
            cache = bg_model.GraphicalElementCache

            min_x = seed_x - search_radius
            max_x = seed_x + search_radius
            min_y = seed_y - search_radius
            max_y = seed_y + search_radius

            for idx in range(1, cache.Count + 1):
                try:
                    el = cache.GetElement(idx)
                    if not el:
                        continue
                    rng = el.Range
                    if rng.High.X < min_x or rng.Low.X > max_x or rng.High.Y < min_y or rng.Low.Y > max_y:
                        continue

                    el_type = int(el.Type)
                    if el_type == 3:  # Line
                        le = el.AsLineElement()
                        p1 = (round(le.StartPoint.X, 3), round(le.StartPoint.Y, 3))
                        p2 = (round(le.EndPoint.X, 3), round(le.EndPoint.Y, 3))
                        segments.append((p1, p2))
                    elif el_type == 4:  # LineString
                        lse = el.AsLineStringElement()
                        pts_ls = []
                        try:
                            vcount = getattr(lse, "VerticesCount", 0)
                            for vi in range(1, vcount + 1):
                                pt = lse.Vertex(vi)
                                pts_ls.append((round(pt.X, 3), round(pt.Y, 3)))
                        except Exception:
                            pass
                        if not pts_ls:
                            raw = lse.GetVertices()
                            pts_ls = [(round(p.X, 3), round(p.Y, 3)) for p in raw]
                        for vi in range(len(pts_ls) - 1):
                            segments.append((pts_ls[vi], pts_ls[vi + 1]))
                    elif el_type == 6:  # Shape
                        se = el.AsShapeElement()
                        pts_s = []
                        try:
                            vcount = getattr(se, "VerticesCount", 0)
                            for vi in range(1, vcount + 1):
                                pt = se.Vertex(vi)
                                pts_s.append((round(pt.X, 3), round(pt.Y, 3)))
                        except Exception:
                            pass
                        if not pts_s:
                            raw = se.GetVertices()
                            pts_s = [(round(p.X, 3), round(p.Y, 3)) for p in raw]
                        for vi in range(len(pts_s) - 1):
                            segments.append((pts_s[vi], pts_s[vi + 1]))
                except Exception:
                    continue
        finally:
            if bg_dgn:
                try:
                    bg_dgn.Close()
                except Exception:
                    pass

        if not segments:
            return f"Không tìm thấy đoạn ranh giới nào trong file tham chiếu tại vùng ({seed_x}, {seed_y}) với bán kính {search_radius}m."

        # 3. Thuật toán Topological Chaining khép góc đa giác
        def point_in_polygon(px, py, poly):
            inside = False
            n = len(poly)
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

        def calc_area(poly):
            n = len(poly)
            a = 0.0
            for i in range(n):
                j = (i + 1) % n
                a += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
            return abs(a) / 2.0

        # Xây dựng đồ thị các đỉnh với dung sai hở ranh 8cm
        nodes = []
        tol = 0.08

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

        # Tìm các chu trình kín đơn (simple cycles) bằng DFS
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

        # Lọc chu trình bao quanh hạt giống seed_x, seed_y và có diện tích nhỏ nhất
        best_poly = None
        min_area = float("inf")

        for c_indices in cycles:
            poly = [nodes[idx] for idx in c_indices]
            area = calc_area(poly)
            if area > 1.0:  # loại bỏ đa giác quá nhỏ / rác
                if point_in_polygon(seed_x, seed_y, poly):
                    if area < min_area:
                        min_area = area
                        best_poly = poly

        if not best_poly:
            return f"Không thể tự động khép góc kín thửa đất chứa điểm ({seed_x}, {seed_y}) từ các đoạn ranh giới tham chiếu."

        # 4. Vẽ Shape khép kín trực tiếp vào file hiện hành
        pt_objs = [bridge.create_point(x, y, 0.0) for x, y in best_poly]
        fill_mode = 1 if fill_color is not None else 0
        shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, fill_mode))
        bridge.apply_symbology(shape_elem, level=target_level, color=color, weight=weight)
        if fill_color is not None:
            try:
                shape_elem.FillColor = int(fill_color)
            except Exception:
                pass
        bridge.add_element(shape_elem)
        shape_id = str(getattr(shape_elem, "ID64", getattr(shape_elem, "ID", "")))

        # 5. Ghi nhãn text nếu có yêu cầu
        if label_text:
            try:
                lbl_pt = bridge.create_point(seed_x, seed_y, 0.0)
                mat = bridge.create_rotation_matrix(0.0)
                te = bridge.unwrap(app.CreateTextElement1(None, str(label_text), lbl_pt, mat))
                bridge.apply_symbology(te, level=target_level, color=color, weight=1)
                try:
                    te.TextStyle.Height = 0.6
                    te.TextStyle.Width = 0.6
                except Exception:
                    pass
                bridge.add_element(te)
            except Exception:
                pass

        try:
            shape_elem.Redraw()
        except Exception:
            pass

        # Tính chu vi
        perim = 0.0
        n_pts = len(best_poly)
        for i in range(n_pts):
            j = (i + 1) % n_pts
            perim += math.hypot(best_poly[j][0] - best_poly[i][0], best_poly[j][1] - best_poly[i][1])

        return (
            f"Đã sao chép và tạo Region thành công từ Reference!\n"
            f"- Đối tượng mới: ShapeElement ID {shape_id}\n"
            f"- Level: {target_level}, Màu viền: {color}, Màu tô: {fill_color}\n"
            f"- Số đỉnh: {len(best_poly)}\n"
            f"- Diện tích: {round(min_area, 3)} m²\n"
            f"- Chu vi: {round(perim, 3)} m\n"
            f"- Tọa độ các đỉnh: {best_poly}"
        )



