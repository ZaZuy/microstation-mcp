"""
src/tools/modify.py
Các công cụ chỉnh sửa, biến đổi hình học (Move, Copy, Rotate, Scale, Mirror, Change Symbology, Drop).
"""

import math
from typing import Optional, List, Dict, Any
from src.core.ms_bridge import bridge


def register_modify_tools(mcp):
    """Đăng ký các tool chỉnh sửa vào MCP Server."""

    @mcp.tool
    def move_element(element_id: str, dx: float, dy: float, dz: float = 0.0) -> str:
        """
        Di chuyển một phần tử trong bản vẽ theo độ dời vector (dX, dY, dZ).

        :param element_id: ID của phần tử cần di chuyển
        :param dx: Độ dời theo trục X
        :param dy: Độ dời theo trục Y
        :param dz: Độ dời theo trục Z (mặc định 0.0)
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        disp = bridge.create_point(dx, dy, dz)
        el.Move(disp)
        try:
            el.Rewrite()
            el.Redraw()
        except Exception:
            pass
        return f"Đã di chuyển phần tử ID {element_id} theo vector ({dx}, {dy}, {dz})"

    @mcp.tool
    def copy_element(element_id: str, dx: float, dy: float, dz: float = 0.0) -> str:
        """
        Sao chép (Copy/Clone) một phần tử sang vị trí mới với độ dời (dX, dY, dZ).

        :param element_id: ID của phần tử gốc
        :param dx: Độ dời theo trục X
        :param dy: Độ dời theo trục Y
        :param dz: Độ dời theo trục Z
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        new_el = el.Clone()
        disp = bridge.create_point(dx, dy, dz)
        new_el.Move(disp)
        bridge.add_element(new_el)

        new_id = str(getattr(new_el, "ID64", getattr(new_el, "ID", "Đã tạo")))
        return f"Đã sao chép phần tử ID {element_id} thành phần tử mới có ID {new_id} với độ dời ({dx}, {dy}, {dz})"

    @mcp.tool
    def rotate_element(
        element_id: str,
        origin_x: float,
        origin_y: float,
        angle_deg: float,
    ) -> str:
        """
        Xoay một phần tử quanh một điểm gốc một góc xác định (ngược chiều kim đồng hồ).

        :param element_id: ID của phần tử cần xoay
        :param origin_x: Tọa độ X của tâm xoay
        :param origin_y: Tọa độ Y của tâm xoay
        :param angle_deg: Góc xoay tính bằng độ
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        origin = bridge.create_point(origin_x, origin_y, 0.0)
        rad = math.radians(angle_deg)
        el.RotateAboutZ(origin, rad)
        try:
            el.Rewrite()
            el.Redraw()
        except Exception:
            pass
        return f"Đã xoay phần tử ID {element_id} quanh ({origin_x}, {origin_y}) góc {angle_deg}°"

    @mcp.tool
    def scale_element(
        element_id: str,
        origin_x: float,
        origin_y: float,
        scale_factor: float,
    ) -> str:
        """
        Phóng to hoặc thu nhỏ một phần tử theo tỷ lệ quanh một điểm gốc.

        :param element_id: ID phần tử
        :param origin_x: Tọa độ X tâm phóng
        :param origin_y: Tọa độ Y tâm phóng
        :param scale_factor: Hệ số tỉ lệ (ví dụ: 2.0 để gấp đôi, 0.5 để thu nhỏ 1 nửa)
        """
        if scale_factor <= 0:
            return "Lỗi: Hệ số tỉ lệ scale_factor phải lớn hơn 0!"

        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        origin = bridge.create_point(origin_x, origin_y, 0.0)
        sf = float(scale_factor)
        try:
            el.ScaleAll(origin, sf, sf, sf)
        except Exception:
            try:
                el.ScaleUniform(origin, sf)
            except Exception:
                el.ScaleAll(origin, sf, sf, 1.0)
        try:
            el.Rewrite()
            el.Redraw()
        except Exception:
            pass
        return f"Đã scale phần tử ID {element_id} tỉ lệ {scale_factor} lần quanh ({origin_x}, {origin_y})"

    @mcp.tool
    def mirror_element(
        element_id: str,
        p1_x: float,
        p1_y: float,
        p2_x: float,
        p2_y: float,
        copy: bool = False,
    ) -> str:
        """
        Lấy đối xứng (Mirror) một phần tử qua đường trục xác định bởi 2 điểm.

        :param element_id: ID phần tử
        :param p1_x: Tọa độ X điểm 1 của trục đối xứng
        :param p1_y: Tọa độ Y điểm 1 của trục đối xứng
        :param p2_x: Tọa độ X điểm 2 của trục đối xứng
        :param p2_y: Tọa độ Y điểm 2 của trục đối xứng
        :param copy: True nếu muốn giữ lại phần tử gốc (Mirror & Copy), False nếu chỉ lật phần tử gốc
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        target = el.Clone() if copy else el
        p1 = bridge.create_point(p1_x, p1_y, 0.0)
        p2 = bridge.create_point(p2_x, p2_y, 0.0)

        try:
            target.Mirror(p1, p2)
            if copy:
                bridge.add_element(target)
            else:
                target.Rewrite()
                target.Redraw()
            action = "nhân bản đối xứng" if copy else "lấy đối xứng"
            return f"Đã {action} phần tử ID {element_id} qua trục ({p1_x}, {p1_y}) -> ({p2_x}, {p2_y})"
        except Exception as ex:
            return f"Lỗi khi mirror phần tử: {ex}"

    @mcp.tool
    def fill_element(
        element_id: str,
        fill_color: int = 4,
        level: Optional[str] = None,
        keep_original: bool = True,
    ) -> str:
        """
        Đổ màu (Fill Color) cho một thửa đất hoặc đối tượng khép kín theo ID.
        Hỗ trợ đối tượng Shape, ComplexShape hoặc tự động chuyển đổi/tạo Shape từ LineString khép kín.

        :param element_id: ID của phần tử cần đổ màu
        :param fill_color: Chỉ số màu tô (0-255, bảng màu chuẩn MicroStation: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
        :param level: Tên Level mới cho đối tượng tô màu (nếu None sẽ giữ nguyên Level của đối tượng)
        :param keep_original: True nếu muốn giữ lại đường viền/đối tượng gốc ban đầu
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        model = bridge.get_active_model()
        el_type = int(el.Type)

        # Bật hiển thị Fill trên View nếu chưa bật
        try:
            app.CadInputQueue.SendKeyin(
                "vba execute On Error Resume Next: Dim vi As Integer: For vi = 1 To 8: "
                "If ActiveDesignFile.Views(vi).IsOpen Then "
                "ActiveDesignFile.Views(vi).DisplaysFill = True: "
                "ActiveDesignFile.Views(vi).Redraw: "
                "End If: Next"
            )
            for vi in range(4):
                app.CadInputQueue.SendKeyin(f"MDL KEYIN BENTLEY.VIEWATTRIBUTESDIALOG,VAD VIEWATTRIBUTESDIALOG SETATTRIBUTE {vi} Fill True")
        except Exception:
            pass

        # Trường hợp 1: Đối tượng là Shape (Type 6), ComplexShape (Type 14) hoặc IsClosedElement
        if el_type in (6, 14) or getattr(el, "IsClosedElement", False):
            filled_ok = False
            try:
                closed_el = el.AsClosedElement()
                closed_el.FillMode = 1  # msdFillModeFilled
                closed_el.FillColor = int(fill_color)
                if level:
                    try:
                        lvl_obj = dgn_file.Levels(level)
                    except Exception:
                        lvl_obj = None
                    if lvl_obj:
                        closed_el.Level = lvl_obj
                closed_el.Rewrite()
                closed_el.Redraw()
                filled_ok = True
            except Exception:
                pass

            if not filled_ok:
                try:
                    lvl_cmd = f'Dim oLvl As Level: Set oLvl = ActiveDesignFile.Levels("{level}"): Set oEl.Level = oLvl: ' if level else ""
                    app.CadInputQueue.SendKeyin(
                        f"vba execute On Error Resume Next: Dim oEl As Element: Set oEl = ActiveModelReference.GetElementByID(DLongFromLong({element_id})): "
                        f"If oEl.IsClosedElement Then "
                        f"Dim oC As ClosedElement: Set oC = oEl.AsClosedElement: "
                        f"oC.FillMode = 1: oC.FillColor = {int(fill_color)}: "
                        f"{lvl_cmd}oC.Rewrite: oC.Redraw: End If"
                    )
                    filled_ok = True
                except Exception:
                    pass

            if filled_ok:
                return f"Đã đổ màu {fill_color} cho đối tượng Shape/ComplexShape ID {element_id} thành công."

        # Trường hợp 2: Đối tượng là LineString (Type 4) hoặc các đối tượng dạng đường khép kín
        pts = []
        try:
            if el_type == 4:
                lse = el.AsLineStringElement()
                try:
                    cnt = getattr(lse, "VerticesCount", 0)
                    for i in range(1, cnt + 1):
                        v = lse.Vertex(i)
                        pts.append(bridge.create_point(v.X, v.Y, getattr(v, "Z", 0.0)))
                except Exception:
                    pass
                if not pts:
                    raw = lse.GetVertices()
                    for p in raw:
                        pts.append(bridge.create_point(p.X, p.Y, getattr(p, "Z", 0.0)))
        except Exception:
            pass

        if len(pts) >= 3:
            try:
                shape_elem = bridge.unwrap(app.CreateShapeElement1(el, pts, 1))
                shape_elem.FillColor = int(fill_color)
                shape_elem.Color = el.Color
                shape_elem.LineWeight = el.LineWeight
                shape_elem.LineStyle = el.LineStyle
                target_level = level if level else (el.Level.Name if el.Level else None)
                if target_level:
                    bridge.apply_symbology(shape_elem, level=target_level)

                bridge.add_element(shape_elem)
                new_id = str(getattr(shape_elem, "ID64", getattr(shape_elem, "ID", "Mới")))

                if not keep_original:
                    try:
                        model.RemoveElement(el)
                    except Exception:
                        pass
                return f"Đã tạo Shape tô màu {fill_color} thành công cho thửa đất ID {element_id} (Shape mới ID: {new_id}, viền màu {el.Color})."
            except Exception as ex:
                return f"Lỗi khi tạo Shape tô màu: {ex}"

        return f"Lỗi: Phần tử ID {element_id} không phải là hình khép kín hoặc không đủ đỉnh để tạo Shape."

    @mcp.tool
    def change_element_symbology(
        element_id: str,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
        filled: Optional[bool] = None,
        fill_color: Optional[int] = None,
    ) -> str:
        """
        Thay đổi thuộc tính Level, Color, Weight, Style, Fill của một phần tử đã tồn tại theo ID.

        :param element_id: ID của phần tử cần chỉnh sửa
        :param level: Tên Level mới
        :param color: Chỉ số màu mới (0-255, bảng màu chuẩn: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
        :param weight: Độ dày nét mới (0-31)
        :param style: Kiểu nét mới (0-7)
        :param filled: True để bật chế độ tô màu, False để tắt
        :param fill_color: Chỉ số màu tô (0-255, bảng màu chuẩn: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        bridge.apply_symbology(el, level=level, color=color, weight=weight, style=style)

        if filled is not None or fill_color is not None:
            fill_mode = 1 if (filled or (filled is None and fill_color is not None)) else 0
            fcolor = int(fill_color) if fill_color is not None else 4
            try:
                if getattr(el, "IsClosedElement", False):
                    closed = el.AsClosedElement()
                    closed.FillMode = fill_mode
                    if fill_color is not None:
                        closed.FillColor = fcolor
            except Exception:
                pass

            try:
                el_id = getattr(el, "ID64", getattr(el, "ID", element_id))
                app = bridge.get_app()
                fc_cmd = f"oEl.AsClosedElement.FillColor = {fcolor}: " if fill_color is not None else ""
                app.CadInputQueue.SendKeyin(
                    f"vba execute On Error Resume Next: Dim oEl As Element: Set oEl = ActiveModelReference.GetElementByID(DLongFromLong({el_id})): "
                    f"If oEl.IsClosedElement Then oEl.AsClosedElement.FillMode = {fill_mode}: {fc_cmd}oEl.Rewrite: oEl.Redraw: End If"
                )
            except Exception:
                pass

        try:
            el.Rewrite()
            el.Redraw()
        except Exception as ex:
            return f"Lỗi khi lưu thuộc tính phần tử: {ex}"

        return f"Đã cập nhật thuộc tính cho phần tử ID {element_id} thành công."

    @mcp.tool
    def drop_element(element_id: str) -> str:
        """
        Phân rã / phá khối (Explode / Drop) một phần tử phức hợp (Cell, Complex String, Complex Shape) thành các đoạn cơ bản.

        :param element_id: ID phần tử cần phân rã
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        try:
            # Phương án 1: Gọi DropEnumerator của MicroStation COM
            if hasattr(el, "Drop"):
                enum = el.Drop()
                count = 0
                while enum.MoveNext():
                    sub_el = enum.Current
                    bridge.add_element(sub_el)
                    count += 1
                model = bridge.get_active_model()
                model.RemoveElement(el)
                return f"Đã phân rã phần tử ID {element_id} thành {count} phần tử đơn lẻ."
        except Exception:
            pass

        # Phương án 2: Sử dụng Key-in lệnh drop
        try:
            app.CadInputQueue.SendKeyin(f"drop element")
            return f"Đã gửi lệnh phân rã phần tử ID {element_id}."
        except Exception as ex:
            return f"Lỗi khi drop phần tử: {ex}"

    @mcp.tool
    def move_parallel(
        element_id: str,
        distance: float,
        side_point_x: float,
        side_point_y: float,
        make_copy: bool = True,
    ) -> str:
        """
        Tạo đối tượng song song cách một khoảng xác định (Move/Copy Parallel / Offset).
        Tương ứng với công cụ 'Move Parallel' trong Tool Box Manipulate.

        :param element_id: ID của phần tử gốc
        :param distance: Khoảng cách song song (Offset distance)
        :param side_point_x: Tọa độ X của điểm chỉ định phía cần offset sang
        :param side_point_y: Tọa độ Y của điểm chỉ định phía cần offset sang
        :param make_copy: True để tạo bản sao song song (Copy), False để dịch chuyển phần tử gốc
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        try:
            mode_str = "copy" if make_copy else "move"
            app.CadInputQueue.SendKeyin(f"move parallel {mode_str}")
            app.CadInputQueue.SendKeyin(f"active distance {distance}")
            r = el.Range
            pt_elem = bridge.create_point((r.Low.X + r.High.X) / 2.0, (r.Low.Y + r.High.Y) / 2.0, 0.0)
            pt_side = bridge.create_point(side_point_x, side_point_y, 0.0)
            app.CadInputQueue.SendDataPoint(pt_elem, 1)
            app.CadInputQueue.SendDataPoint(pt_side, 1)
            app.CadInputQueue.SendReset()
            return f"Đã offset song song phần tử ID {element_id} khoảng cách {distance} ({mode_str})"
        except Exception as ex:
            return f"Lỗi khi thực hiện move parallel: {ex}"

    @mcp.tool
    def construct_circular_fillet(
        element_id1: str,
        element_id2: str,
        radius: float,
        trim_mode: bool = True,
    ) -> str:
        """
        Bo tròn góc giữa 2 đối tượng giao nhau bằng cung tròn bán kính R (Construct Circular Fillet).
        Tương ứng với công cụ 'Construct Circular Fillet' trong Tool Box Modify.

        :param element_id1: ID phần tử thứ nhất
        :param element_id2: ID phần tử thứ hai
        :param radius: Bán kính bo tròn góc
        :param trim_mode: True để tự động cắt gọn phần thừa sau khi bo tròn
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return f"Lỗi: Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"

        app = bridge.get_app()
        try:
            trim_str = "both" if trim_mode else "none"
            app.CadInputQueue.SendKeyin(f"construct fillet circular {radius}")
            r1 = el1.Range
            p1 = bridge.create_point((r1.Low.X + r1.High.X) / 2.0, (r1.Low.Y + r1.High.Y) / 2.0, 0.0)
            r2 = el2.Range
            p2 = bridge.create_point((r2.Low.X + r2.High.X) / 2.0, (r2.Low.Y + r2.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(p1, 1)
            app.CadInputQueue.SendDataPoint(p2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã bo tròn góc R={radius} giữa phần tử {element_id1} và {element_id2}"
        except Exception as ex:
            return f"Lỗi khi bo tròn fillet: {ex}"

    @mcp.tool
    def construct_chamfer(
        element_id1: str,
        element_id2: str,
        distance1: float,
        distance2: float,
        trim_mode: bool = True,
    ) -> str:
        """
        Vát góc giữa 2 đối tượng giao nhau (Construct Chamfer).
        Tương ứng với công cụ 'Construct Chamfer' trong Tool Box Modify.

        :param element_id1: ID phần tử thứ nhất
        :param element_id2: ID phần tử thứ hai
        :param distance1: Khoảng cách vát trên phần tử thứ nhất
        :param distance2: Khoảng cách vát trên phần tử thứ hai
        :param trim_mode: True để tự động xén phần thừa
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return f"Lỗi: Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin(f"construct chamfer {distance1} {distance2}")
            r1 = el1.Range
            p1 = bridge.create_point((r1.Low.X + r1.High.X) / 2.0, (r1.Low.Y + r1.High.Y) / 2.0, 0.0)
            r2 = el2.Range
            p2 = bridge.create_point((r2.Low.X + r2.High.X) / 2.0, (r2.Low.Y + r2.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(p1, 1)
            app.CadInputQueue.SendDataPoint(p2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã vát góc (d1={distance1}, d2={distance2}) giữa {element_id1} và {element_id2}"
        except Exception as ex:
            return f"Lỗi khi vát chamfer: {ex}"

    @mcp.tool
    def extend_line(
        element_id: str,
        distance: float,
        from_start: bool = False,
    ) -> str:
        """
        Kéo dài đoạn thẳng một khoảng cách xác định (Extend Line).
        Tương ứng với công cụ 'Extend Line' trong Tool Box Modify.

        :param element_id: ID phần tử đường thẳng
        :param distance: Độ dài kéo dài thêm (dương là dài ra, âm là ngắn lại)
        :param from_start: True nếu kéo dài về phía điểm đầu, False nếu kéo dài về phía điểm cuối
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        try:
            if el.Type == 3:  # LineElement
                le = el.AsLineElement()
                p1 = le.StartPoint
                p2 = le.EndPoint
                dx = p2.X - p1.X
                dy = p2.Y - p1.Y
                length = math.hypot(dx, dy)
                if length < 1e-6:
                    return "Lỗi: Đoạn thẳng có độ dài gần bằng 0!"

                ux = dx / length
                uy = dy / length

                if from_start:
                    new_start = bridge.create_point(p1.X - ux * distance, p1.Y - uy * distance, p1.Z)
                    le.StartPoint = new_start
                else:
                    new_end = bridge.create_point(p2.X + ux * distance, p2.Y + uy * distance, p2.Z)
                    le.EndPoint = new_end

                le.Rewrite()
                le.Redraw()
                return f"Đã kéo dài đoạn thẳng ID {element_id} thêm {distance} (tổng dài mới: {round(length + distance, 4)})"
        except Exception:
            pass

        try:
            app.CadInputQueue.SendKeyin(f"extend distance {distance}")
            return f"Đã gửi lệnh kéo dài đoạn thẳng ID {element_id}"
        except Exception as ex:
            return f"Lỗi khi kéo dài line: {ex}"

    @mcp.tool
    def extend_to_intersection(
        element_id1: str,
        element_id2: str,
    ) -> str:
        """
        Kéo dài 2 đoạn thẳng tới điểm giao nhau của chúng (Extend 2 Elements to Intersection).
        Tương ứng với công cụ 'Extend 2 Elements' / 'Extend to Intersection' trong Tool Box Modify.

        :param element_id1: ID phần tử thứ nhất
        :param element_id2: ID phần tử thứ hai
        """
        el1 = bridge.find_element_by_id(element_id1)
        el2 = bridge.find_element_by_id(element_id2)
        if not el1 or not el2:
            return f"Lỗi: Không tìm thấy phần tử {element_id1} hoặc {element_id2}!"

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("extend 2 elements")
            r1 = el1.Range
            p1 = bridge.create_point((r1.Low.X + r1.High.X) / 2.0, (r1.Low.Y + r1.High.Y) / 2.0, 0.0)
            r2 = el2.Range
            p2 = bridge.create_point((r2.Low.X + r2.High.X) / 2.0, (r2.Low.Y + r2.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(p1, 1)
            app.CadInputQueue.SendDataPoint(p2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã kéo dài 2 phần tử {element_id1} và {element_id2} tới giao điểm"
        except Exception as ex:
            return f"Lỗi khi kéo dài tới giao điểm: {ex}"

    @mcp.tool
    def trim_element(
        element_id: str,
        cutting_element_id: str,
    ) -> str:
        """
        Cắt xén một phần tử bằng đường biên cắt (Trim Element).
        Tương ứng với công cụ 'Trim Element' trong Tool Box Modify.

        :param element_id: ID phần tử cần bị cắt xén
        :param cutting_element_id: ID phần tử làm dao cắt (Cutting edge)
        """
        el = bridge.find_element_by_id(element_id)
        cutter = bridge.find_element_by_id(cutting_element_id)
        if not el or not cutter:
            return f"Lỗi: Không tìm thấy phần tử {element_id} hoặc dao cắt {cutting_element_id}!"

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("trim element")
            rc = cutter.Range
            pc = bridge.create_point((rc.Low.X + rc.High.X) / 2.0, (rc.Low.Y + rc.High.Y) / 2.0, 0.0)
            re = el.Range
            pe = bridge.create_point((re.Low.X + re.High.X) / 2.0, (re.Low.Y + re.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(pc, 1)
            app.CadInputQueue.SendDataPoint(pe, 1)
            app.CadInputQueue.SendReset()
            return f"Đã gửi lệnh xén phần tử {element_id} bằng dao cắt {cutting_element_id}"
        except Exception as ex:
            return f"Lỗi khi cắt xén: {ex}"

    @mcp.tool
    def insert_vertex(
        element_id: str,
        vertex_index: int,
        x: float,
        y: float,
        z: float = 0.0,
    ) -> str:
        """
        Thêm một đỉnh mới vào đối tượng LineString hoặc Shape (Insert Vertex).
        Tương ứng với công cụ 'Insert Vertex' trong Tool Box Modify.

        :param element_id: ID phần tử cần thêm đỉnh
        :param vertex_index: Vị trí chèn (1-based index)
        :param x: Tọa độ X đỉnh mới
        :param y: Tọa độ Y đỉnh mới
        :param z: Tọa độ Z đỉnh mới
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        pt = bridge.create_point(x, y, z)
        try:
            if hasattr(el, "InsertVertex"):
                el.InsertVertex(int(vertex_index), pt)
                el.Rewrite()
                el.Redraw()
                return f"Đã chèn đỉnh mới tại ({x}, {y}) vào vị trí {vertex_index} của phần tử ID {element_id}"
        except Exception:
            pass

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("insert vertex")
            app.CadInputQueue.SendDataPoint(pt, 1)
            app.CadInputQueue.SendReset()
            return f"Đã gửi lệnh thêm đỉnh ({x}, {y}) vào phần tử ID {element_id}"
        except Exception as ex:
            return f"Lỗi khi thêm đỉnh: {ex}"

    @mcp.tool
    def delete_vertex(
        element_id: str,
        vertex_index: int,
    ) -> str:
        """
        Xóa bớt một đỉnh khỏi đối tượng LineString hoặc Shape (Delete Vertex).
        Tương ứng với công cụ 'Delete Vertex' trong Tool Box Modify.

        :param element_id: ID phần tử cần xóa đỉnh
        :param vertex_index: Vị trí đỉnh cần xóa (1-based index)
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        try:
            if hasattr(el, "DeleteVertex"):
                el.DeleteVertex(int(vertex_index))
                el.Rewrite()
                el.Redraw()
                return f"Đã xóa đỉnh thứ {vertex_index} khỏi phần tử ID {element_id}"
        except Exception:
            pass

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("delete vertex")
            r = el.Range
            pt = bridge.create_point((r.Low.X + r.High.X) / 2.0, (r.Low.Y + r.High.Y) / 2.0, 0.0)
            app.CadInputQueue.SendDataPoint(pt, 1)
            app.CadInputQueue.SendReset()
            return f"Đã gửi lệnh xóa đỉnh thứ {vertex_index} của phần tử ID {element_id}"
        except Exception as ex:
            return f"Lỗi khi xóa đỉnh: {ex}"

    @mcp.tool
    def delete_part_of_element(
        element_id: str,
        p1_x: float,
        p1_y: float,
        p2_x: float,
        p2_y: float,
    ) -> str:
        """
        Cắt bỏ một đoạn giữa hai điểm trên một phần tử (Delete Partial / Cut Element).
        Tương ứng với công cụ 'Delete Partial' trong Tool Box Modify.

        :param element_id: ID phần tử
        :param p1_x: Tọa độ X điểm cắt thứ nhất
        :param p1_y: Tọa độ Y điểm cắt thứ nhất
        :param p2_x: Tọa độ X điểm cắt thứ hai
        :param p2_y: Tọa độ Y điểm cắt thứ hai
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("delete partial")
            pt1 = bridge.create_point(p1_x, p1_y, 0.0)
            pt2 = bridge.create_point(p2_x, p2_y, 0.0)
            app.CadInputQueue.SendDataPoint(pt1, 1)
            app.CadInputQueue.SendDataPoint(pt2, 1)
            app.CadInputQueue.SendReset()
            return f"Đã cắt bỏ đoạn giữa ({p1_x}, {p1_y}) và ({p2_x}, {p2_y}) trên phần tử ID {element_id}"
        except Exception as ex:
            return f"Lỗi khi cắt bỏ đoạn: {ex}"

    @mcp.tool
    def array_rectangular(
        element_id: str,
        rows: int,
        cols: int,
        delta_x: float,
        delta_y: float,
    ) -> str:
        """
        Tạo mảng đối tượng dạng lưới hàng - cột chữ nhật (Construct Rectangular Array).
        Tương ứng với công cụ 'Construct Array (Rectangular)' trong Tool Box Manipulate.

        :param element_id: ID phần tử gốc cần nhân bản
        :param rows: Số lượng hàng (dọc theo trục Y, tối thiểu 1)
        :param cols: Số lượng cột (ngang theo trục X, tối thiểu 1)
        :param delta_x: Khoảng cách giữa các cột
        :param delta_y: Khoảng cách giữa các hàng
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        if rows < 1 or cols < 1:
            return "Lỗi: Số hàng và số cột phải >= 1!"

        created_count = 0
        for r in range(rows):
            for c in range(cols):
                if r == 0 and c == 0:
                    continue  # Đối tượng gốc đã có sẵn
                cloned = el.Clone()
                disp = bridge.create_point(c * delta_x, r * delta_y, 0.0)
                cloned.Move(disp)
                bridge.add_element(cloned)
                created_count += 1

        return f"Đã tạo mảng chữ nhật {rows}x{cols} gồm {created_count + 1} đối tượng (tạo mới {created_count}) với bước nhảy ({delta_x}, {delta_y})"

    @mcp.tool
    def array_polar(
        element_id: str,
        count: int,
        center_x: float,
        center_y: float,
        total_angle_deg: float = 360.0,
        rotate_items: bool = True,
    ) -> str:
        """
        Tạo mảng đối tượng xoay tròn quanh tâm (Construct Polar / Circular Array).
        Tương ứng với công cụ 'Construct Array (Polar)' trong Tool Box Manipulate.

        :param element_id: ID phần tử gốc
        :param count: Tổng số đối tượng sau khi nhân bản (tối thiểu 2)
        :param center_x: Tọa độ X tâm xoay
        :param center_y: Tọa độ Y tâm xoay
        :param total_angle_deg: Tổng góc phân bố (360 độ là cả vòng tròn kín)
        :param rotate_items: True nếu các đối tượng xoay theo góc phân bố, False nếu giữ nguyên phương
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        if count < 2:
            return "Lỗi: Số lượng phần tử trong mảng xoay phải >= 2!"

        step_deg = total_angle_deg / float(count) if abs(total_angle_deg - 360.0) < 1e-4 else total_angle_deg / float(count - 1)
        center = bridge.create_point(center_x, center_y, 0.0)
        created_count = 0

        for i in range(1, count):
            cur_angle_deg = i * step_deg
            cloned = el.Clone()
            rad = math.radians(cur_angle_deg)
            cloned.RotateAboutZ(center, rad)
            bridge.add_element(cloned)
            created_count += 1

        return f"Đã tạo mảng xoay quanh tâm ({center_x}, {center_y}) gồm {count} đối tượng trải góc {total_angle_deg}°"

    @mcp.tool
    def align_elements(
        element_ids: List[str],
        alignment: str = "left",
    ) -> str:
        """
        Căn lề hàng loạt đối tượng theo cạnh trái, phải, trên, dưới hoặc tâm (Align Elements).
        Tương ứng với công cụ 'Align Elements' trong Tool Box Manipulate.

        :param element_ids: Danh sách ID các phần tử cần căn chỉnh (tối thiểu 2)
        :param alignment: Kiểu căn lề ('left', 'right', 'top', 'bottom', 'center_x', 'center_y')
        """
        if len(element_ids) < 2:
            return "Lỗi: Cần tối thiểu 2 phần tử để căn lề!"

        elems = []
        for eid in element_ids:
            el = bridge.find_element_by_id(eid)
            if el:
                elems.append(el)

        if len(elems) < 2:
            return "Lỗi: Không đủ phần tử hợp lệ để căn lề!"

        # Lấy phần tử đầu tiên làm chuẩn mốc (Reference)
        base_el = elems[0]
        base_rng = base_el.Range

        align_mode = alignment.lower().strip()
        updated = 0

        for el in elems[1:]:
            rng = el.Range
            dx, dy = 0.0, 0.0
            if align_mode == "left":
                dx = base_rng.Low.X - rng.Low.X
            elif align_mode == "right":
                dx = base_rng.High.X - rng.High.X
            elif align_mode == "bottom":
                dy = base_rng.Low.Y - rng.Low.Y
            elif align_mode == "top":
                dy = base_rng.High.Y - rng.High.Y
            elif align_mode == "center_x":
                base_cx = (base_rng.Low.X + base_rng.High.X) / 2.0
                cx = (rng.Low.X + rng.High.X) / 2.0
                dx = base_cx - cx
            elif align_mode == "center_y":
                base_cy = (base_rng.Low.Y + base_rng.High.Y) / 2.0
                cy = (rng.Low.Y + rng.High.Y) / 2.0
                dy = base_cy - cy

            disp = bridge.create_point(dx, dy, 0.0)
            el.Move(disp)
            el.Rewrite()
            el.Redraw()
            updated += 1

        return f"Đã căn lề {align_mode.upper()} cho {updated} phần tử theo đối tượng mốc ID {element_ids[0]}"

    @mcp.tool
    def drop_complex(element_id: str) -> str:
        """
        Rã khối phức hợp (Complex Chain, Complex Shape, Graphic Group) thành các đối tượng đơn lẻ.
        Tương ứng với công cụ 'Drop Complex Status' trong Tool Box Drop.

        :param element_id: ID phần tử cần rã khối
        """
        return drop_element(element_id=element_id)

