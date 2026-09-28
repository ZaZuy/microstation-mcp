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
    def draw_smartline(
        points: List[List[float]],
        vertex_type: str = "sharp",
        rounding_radius: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Vẽ đường thông minh SmartLine (Place SmartLine) qua các đỉnh với tùy chọn góc nhọn hoặc bo tròn.
        Tương ứng với công cụ 'Place SmartLine' trong Tool Box Linear Elements.

        :param points: Danh sách tọa độ đỉnh [[x1, y1], [x2, y2], ...]
        :param vertex_type: Loại góc ('sharp' - nhọn, 'rounded' - bo tròn, 'chamfer' - vát góc)
        :param rounding_radius: Bán kính bo góc nếu vertex_type='rounded'
        :param level: Tên Level
        :param color: Chỉ số màu
        :param weight: Độ dày nét
        :param style: Kiểu nét
        """
        if len(points) < 2:
            return "Lỗi: Cần tối thiểu 2 điểm để vẽ SmartLine!"

        app = bridge.get_app()
        if vertex_type.lower() == "rounded" and rounding_radius > 0:
            try:
                app.CadInputQueue.SendKeyin(f"place smartline rounded {rounding_radius}")
                for pt in points:
                    z = pt[2] if len(pt) > 2 else 0.0
                    app.CadInputQueue.SendDataPoint(bridge.create_point(pt[0], pt[1], z), 1)
                app.CadInputQueue.SendReset()
                return f"Đã vẽ SmartLine bo tròn R={rounding_radius} qua {len(points)} điểm"
            except Exception:
                pass

        pt_objs = [bridge.create_point(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in points]
        is_closed = math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) < 1e-4 and len(points) >= 4

        if is_closed:
            el = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, 0))
        else:
            el = bridge.unwrap(app.CreateLineElement1(None, pt_objs))

        bridge.apply_symbology(el, level=level, color=color, weight=weight, style=style)
        bridge.add_element(el)
        return f"Đã vẽ SmartLine qua {len(points)} điểm ({'khép kín' if is_closed else 'hở'})"

    @mcp.tool
    def draw_multiline(
        points: List[List[float]],
        style_name: Optional[str] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> str:
        """
        Vẽ đường song song phức hợp Multi-line (Place Multi-line).
        Tương ứng với công cụ 'Place Multi-line' trong Tool Box Linear Elements.

        :param points: Danh sách tọa độ đỉnh [[x1, y1], [x2, y2], ...]
        :param style_name: Tên kiểu Multi-line style đã định nghĩa
        :param level: Tên Level
        :param color: Chỉ số màu
        :param weight: Độ dày nét
        """
        if len(points) < 2:
            return "Lỗi: Cần tối thiểu 2 điểm để vẽ Multi-line!"

        app = bridge.get_app()
        try:
            if level:
                app.CadInputQueue.SendKeyin(f"lv={level}")
            if color is not None:
                app.CadInputQueue.SendKeyin(f"co={color}")
            if weight is not None:
                app.CadInputQueue.SendKeyin(f"wt={weight}")
            if style_name:
                app.CadInputQueue.SendKeyin(f'active mlstyle "{style_name}"')

            app.CadInputQueue.SendKeyin("place multiline")
            for pt in points:
                z = pt[2] if len(pt) > 2 else 0.0
                app.CadInputQueue.SendDataPoint(bridge.create_point(pt[0], pt[1], z), 1)
            app.CadInputQueue.SendReset()
            return f"Đã vẽ Multi-line qua {len(points)} điểm"
        except Exception as ex:
            return f"Lỗi khi vẽ Multi-line: {ex}"

    @mcp.tool
    def draw_orthogonal_shape(
        points: List[List[float]],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
        fill_color: Optional[int] = None,
    ) -> str:
        """
        Vẽ đa giác góc vuông (Orthogonal Shape).
        Tương ứng với công cụ 'Place Orthogonal Shape' trong Tool Box Polygons.

        :param points: Danh sách các đỉnh góc vuông [[x1, y1], [x2, y2], ...]
        :param level: Tên Level
        :param color: Chỉ số màu viền
        :param weight: Độ dày nét
        :param style: Kiểu nét
        :param fill_color: Màu tô nền (tùy chọn)
        """
        if len(points) < 3:
            return "Lỗi: Hình đa giác góc vuông cần tối thiểu 3 đỉnh!"

        app = bridge.get_app()
        pt_objs = [bridge.create_point(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in points]
        fill_mode = 1 if fill_color is not None else 0

        shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, fill_mode))
        bridge.apply_symbology(shape_elem, level=level, color=color, weight=weight, style=style)
        if fill_color is not None:
            try:
                shape_elem.FillColor = int(fill_color)
            except Exception:
                pass
        bridge.add_element(shape_elem)
        return f"Đã vẽ đa giác góc vuông {len(points)} đỉnh"

    @mcp.tool
    def draw_regular_polygon(
        center_x: float,
        center_y: float,
        radius: float,
        num_edges: int = 5,
        rotation_deg: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        fill_color: Optional[int] = None,
    ) -> str:
        """
        Vẽ đa giác đều (Place Regular Polygon / Inscribed / Circumscribed Polygon).
        Tương ứng với công cụ 'Place Regular Polygon' trong Tool Box Polygons.

        :param center_x: Tọa độ X tâm đa giác
        :param center_y: Tọa độ Y tâm đa giác
        :param radius: Bán kính đường tròn ngoại tiếp đa giác
        :param num_edges: Số cạnh đa giác (tối thiểu 3: tam giác đều, ngũ giác, lục giác...)
        :param rotation_deg: Góc xoay ban đầu (độ)
        :param level: Tên Level
        :param color: Màu viền
        :param weight: Độ dày nét
        :param fill_color: Màu tô nền
        """
        if num_edges < 3:
            return "Lỗi: Đa giác phải có tối thiểu 3 cạnh!"
        if radius <= 0:
            return "Lỗi: Bán kính phải lớn hơn 0!"

        app = bridge.get_app()
        step = 2.0 * math.pi / num_edges
        start_rad = math.radians(rotation_deg)

        pt_objs = []
        for i in range(num_edges):
            ang = start_rad + i * step
            px = center_x + radius * math.cos(ang)
            py = center_y + radius * math.sin(ang)
            pt_objs.append(bridge.create_point(px, py, 0.0))

        fill_mode = 1 if fill_color is not None else 0
        shape_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, fill_mode))
        bridge.apply_symbology(shape_elem, level=level, color=color, weight=weight)
        if fill_color is not None:
            try:
                shape_elem.FillColor = int(fill_color)
            except Exception:
                pass
        bridge.add_element(shape_elem)
        return f"Đã vẽ đa giác đều {num_edges} cạnh tại tâm ({center_x}, {center_y}) bán kính {radius}"

    @mcp.tool
    def draw_half_circle(
        center_x: float,
        center_y: float,
        radius: float,
        start_angle_deg: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> str:
        """
        Vẽ nửa đường tròn (Half Circle / Semicircle Arc 180°).
        Tương ứng với công cụ 'Place Half Circle' trong Tool Box Circles.

        :param center_x: Tọa độ X tâm
        :param center_y: Tọa độ Y tâm
        :param radius: Bán kính
        :param start_angle_deg: Góc xuất phát (độ)
        :param level: Tên Level
        :param color: Màu nét
        :param weight: Độ dày nét
        """
        if radius <= 0:
            return "Lỗi: Bán kính phải lớn hơn 0!"

        app = bridge.get_app()
        center = bridge.create_point(center_x, center_y, 0.0)
        matrix = bridge.create_rotation_matrix(0.0)
        start_rad = math.radians(start_angle_deg)
        sweep_rad = math.pi  # 180 độ

        arc_elem = bridge.unwrap(app.CreateArcElement2(None, center, radius, radius, matrix, start_rad, sweep_rad))
        bridge.apply_symbology(arc_elem, level=level, color=color, weight=weight)
        bridge.add_element(arc_elem)
        return f"Đã vẽ nửa đường tròn tâm ({center_x}, {center_y}), R={radius}, start={start_angle_deg}°"

    @mcp.tool
    def construct_angle_bisector(
        x1: float,
        y1: float,
        vertex_x: float,
        vertex_y: float,
        x2: float,
        y2: float,
        length: float = 10.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Dựng đường phân giác góc giữa 2 tia tạo bởi 3 điểm (Construct Angle Bisector).
        Tương ứng với công cụ 'Construct Angle Bisector' trong Tool Box Linear Elements / Curves.

        :param x1: Tọa độ X điểm trên tia 1
        :param y1: Tọa độ Y điểm trên tia 1
        :param vertex_x: Tọa độ X của đỉnh góc
        :param vertex_y: Tọa độ Y của đỉnh góc
        :param x2: Tọa độ X điểm trên tia 2
        :param y2: Tọa độ Y điểm trên tia 2
        :param length: Chiều dài đoạn phân giác cần vẽ
        :param level: Tên Level
        :param color: Màu nét
        """
        v1_x, v1_y = x1 - vertex_x, y1 - vertex_y
        v2_x, v2_y = x2 - vertex_x, y2 - vertex_y
        len1 = math.hypot(v1_x, v1_y)
        len2 = math.hypot(v2_x, v2_y)

        if len1 < 1e-6 or len2 < 1e-6:
            return "Lỗi: Điểm trên tia trùng với đỉnh góc!"

        u1_x, u1_y = v1_x / len1, v1_y / len1
        u2_x, u2_y = v2_x / len2, v2_y / len2

        b_x = u1_x + u2_x
        b_y = u1_y + u2_y
        b_len = math.hypot(b_x, b_y)

        if b_len < 1e-6:
            # Góc bẹt 180 độ
            b_x, b_y = -u1_y, u1_x
            b_len = 1.0

        target_x = vertex_x + (b_x / b_len) * length
        target_y = vertex_y + (b_y / b_len) * length

        app = bridge.get_app()
        p_start = bridge.create_point(vertex_x, vertex_y, 0.0)
        p_end = bridge.create_point(target_x, target_y, 0.0)
        line = bridge.unwrap(app.CreateLineElement2(None, p_start, p_end))
        bridge.apply_symbology(line, level=level, color=color)
        bridge.add_element(line)
        return f"Đã dựng đường phân giác góc tại đỉnh ({vertex_x}, {vertex_y}) dài {length}"

    @mcp.tool
    def construct_min_distance_line(
        element_id1: str,
        element_id2: str,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Dựng đoạn thẳng nối khoảng cách ngắn nhất giữa hai phần tử (Construct Minimum Distance Line).
        Tương ứng với công cụ 'Construct Line Between Elements' trong Tool Box Linear Elements.

        :param element_id1: ID phần tử thứ nhất
        :param element_id2: ID phần tử thứ hai
        :param level: Tên Level
        :param color: Màu nét
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return f"Lỗi: Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("construct line minimum distance")
            r1 = el1.Range
            p1 = bridge.create_point((r1.Low.X + r1.High.X) / 2.0, (r1.Low.Y + r1.High.Y) / 2.0, 0.0)
            r2 = el2.Range
            p2 = bridge.create_point((r2.Low.X + r2.High.X) / 2.0, (r2.Low.Y + r2.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(p1, 1)
            app.CadInputQueue.SendDataPoint(p2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã dựng đoạn khoảng cách ngắn nhất giữa phần tử {element_id1} và {element_id2}"
        except Exception as ex:
            return f"Lỗi khi dựng đoạn khoảng cách ngắn nhất: {ex}"

    @mcp.tool
    def draw_points_along_element(
        element_id: str,
        num_points: int = 5,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Chấm các điểm mốc chia đều dọc theo một phần tử đường/đường cong (Construct Points Along Element).
        Tương ứng với công cụ 'Construct Points Along Element' trong Tool Box Points.

        :param element_id: ID của phần tử cần chia điểm
        :param num_points: Số lượng điểm cần chấm
        :param level: Tên Level
        :param color: Màu điểm
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID '{element_id}'!"

        app = bridge.get_app()
        pts_created = 0
        try:
            length = float(getattr(el, "Length", 0.0))
            if length > 0 and num_points > 1:
                step = length / float(num_points - 1)
                for i in range(num_points):
                    dist = i * step
                    pt = el.PointAtDistance(dist)
                    pt_elem = bridge.unwrap(app.CreatePointElement1(None, pt))
                    bridge.apply_symbology(pt_elem, level=level, color=color)
                    bridge.add_element(pt_elem)
                    pts_created += 1
                return f"Đã chia đều và vẽ {pts_created} điểm dọc theo phần tử ID {element_id}"
        except Exception:
            pass

        # Fallback Keyin
        try:
            app.CadInputQueue.SendKeyin(f"construct point distance")
            return f"Đã gửi lệnh chia điểm dọc phần tử ID {element_id}"
        except Exception as ex:
            return f"Lỗi khi chia điểm: {ex}"

    @mcp.tool
    def draw_points_at_intersection(
        element_id1: str,
        element_id2: str,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Tìm và chấm các điểm giao nhau giữa 2 phần tử hình học (Construct Point at Intersection).
        Tương ứng với công cụ 'Construct Point at Intersection' trong Tool Box Points.

        :param element_id1: ID phần tử thứ nhất
        :param element_id2: ID phần tử thứ hai
        :param level: Tên Level
        :param color: Màu điểm
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return f"Lỗi: Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"

        app = bridge.get_app()
        pts_count = 0
        try:
            matrix = bridge.create_rotation_matrix(0.0)
            pts = el1.GetIntersectionPoints(el2, matrix)
            if pts:
                for p in pts:
                    pt_elem = bridge.unwrap(app.CreatePointElement1(None, p))
                    bridge.apply_symbology(pt_elem, level=level, color=color)
                    bridge.add_element(pt_elem)
                    pts_count += 1
                return f"Đã vẽ {pts_count} điểm giao cắt giữa phần tử {element_id1} và {element_id2}"
        except Exception:
            pass

        try:
            app.CadInputQueue.SendKeyin("construct point intersection")
            r1 = el1.Range
            p1 = bridge.create_point((r1.Low.X + r1.High.X) / 2.0, (r1.Low.Y + r1.High.Y) / 2.0, 0.0)
            r2 = el2.Range
            p2 = bridge.create_point((r2.Low.X + r2.High.X) / 2.0, (r2.Low.Y + r2.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(p1, 1)
            app.CadInputQueue.SendDataPoint(p2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã gửi lệnh chấm điểm giao cắt giữa phần tử {element_id1} và {element_id2}"
        except Exception as ex:
            return f"Lỗi khi chấm điểm giao cắt: {ex}"

