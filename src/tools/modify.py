"""
src/tools/modify.py
Các công cụ chỉnh sửa, biến đổi hình học (Move, Copy, Rotate, Scale, Mirror, Change Symbology, Drop).
"""

import math
from typing import Optional
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
        el.ScaleAll(origin, float(scale_factor))
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
    def change_element_symbology(
        element_id: str,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> str:
        """
        Thay đổi thuộc tính Level, Color, Weight, Style của một phần tử đã tồn tại theo ID.

        :param element_id: ID của phần tử cần chỉnh sửa
        :param level: Tên Level mới
        :param color: Chỉ số màu mới (0-255)
        :param weight: Độ dày nét mới (0-31)
        :param style: Kiểu nét mới (0-7)
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        bridge.apply_symbology(el, level=level, color=color, weight=weight, style=style)
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
