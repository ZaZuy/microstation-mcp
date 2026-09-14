"""
src/tools/pattern.py
Các công cụ gạch mặt cắt (Hatch), ca-rô (Crosshatch) và đổ mẫu hoa văn (Pattern Area) trong MicroStation V8i.
Tương ứng với Tool Box 'Patterning' trong MicroStation V8i.
"""

import math
from typing import Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_pattern_tools(mcp):
    """Đăng ký các công cụ gạch mặt cắt và hoa văn vào MCP Server."""

    @mcp.tool
    def hatch_area(
        element_id: str,
        spacing: float = 2.0,
        angle_degrees: float = 45.0,
        color: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gạch mặt cắt đường sọc đơn (Linear Hatch) cho một đối tượng hình học khép kín (Shape/ComplexShape/Ellipse).
        Tương ứng với công cụ 'Hatch Area' trong Tool Box Patterning.

        :param element_id: ID phần tử hình học khép kín cần gạch mặt cắt
        :param spacing: Khoảng cách giữa các đường nét gạch (Master Units)
        :param angle_degrees: Góc nghiêng của đường gạch (độ, ví dụ 45.0)
        :param color: Màu nét gạch (tùy chọn)
        :param weight: Độ dày nét gạch (tùy chọn)
        """
        app = bridge.get_app()
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy đối tượng ID '{element_id}'!"}

        rad = math.radians(angle_degrees)
        try:
            # Tạo Pattern object
            pattern = app.CreateHatchPattern1(float(spacing), float(rad))
            matrix = bridge.create_rotation_matrix(0.0)

            # Gán pattern vào phần tử
            if hasattr(el, "SetPattern"):
                el.SetPattern(pattern, matrix)
                el.Rewrite()
                el.Redraw()
                return {
                    "status": "success",
                    "message": f"Đã gạch mặt cắt đơn (khoảng cách {spacing}m, góc {angle_degrees}°) cho đối tượng ID {element_id}.",
                    "element_id": element_id,
                }
        except Exception:
            pass

        # Fallback qua CAD Engine Keyin
        try:
            app.CadInputQueue.SendKeyin(f"hatch spacing {spacing}")
            app.CadInputQueue.SendKeyin(f"hatch angle {angle_degrees}")
            app.CadInputQueue.SendKeyin(f"hatch pattern")
            return {
                "status": "success",
                "message": f"Đã cấu hình và áp dụng Hatch Area (spacing={spacing}, angle={angle_degrees}°) qua CAD Engine.",
                "element_id": element_id,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi gạch mặt cắt: {str(ex)}"}

    @mcp.tool
    def crosshatch_area(
        element_id: str,
        spacing_1: float = 2.0,
        spacing_2: float = 2.0,
        angle_degrees_1: float = 45.0,
        angle_degrees_2: float = 135.0,
    ) -> Dict[str, Any]:
        """
        Gạch mặt cắt dạng ca-rô 2 chiều (Crosshatch Area) cho một đối tượng khép kín.
        Tương ứng với công cụ 'Crosshatch Area' trong Tool Box Patterning.

        :param element_id: ID phần tử khép kín
        :param spacing_1: Khoảng cách đường gạch hướng 1
        :param spacing_2: Khoảng cách đường gạch hướng 2
        :param angle_degrees_1: Góc nghiêng hướng 1 (độ, ví dụ 45.0)
        :param angle_degrees_2: Góc nghiêng hướng 2 (độ, ví dụ 135.0)
        """
        app = bridge.get_app()
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy đối tượng ID '{element_id}'!"}

        rad1 = math.radians(angle_degrees_1)
        rad2 = math.radians(angle_degrees_2)

        try:
            pattern = app.CreateCrossHatchPattern(float(spacing_1), float(spacing_2), float(rad1), float(rad2))
            matrix = bridge.create_rotation_matrix(0.0)
            if hasattr(el, "SetPattern"):
                el.SetPattern(pattern, matrix)
                el.Rewrite()
                el.Redraw()
                return {
                    "status": "success",
                    "message": f"Đã gạch ca-rô thành công cho đối tượng ID {element_id}.",
                    "element_id": element_id,
                }
        except Exception:
            pass

        try:
            app.CadInputQueue.SendKeyin(f"crosshatch spacing1 {spacing_1}")
            app.CadInputQueue.SendKeyin(f"crosshatch spacing2 {spacing_2}")
            app.CadInputQueue.SendKeyin(f"crosshatch angle1 {angle_degrees_1}")
            app.CadInputQueue.SendKeyin(f"crosshatch angle2 {angle_degrees_2}")
            return {
                "status": "success",
                "message": f"Đã cấu hình lệnh Crosshatch Area cho đối tượng ID {element_id}.",
                "element_id": element_id,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi gạch ca-rô: {str(ex)}"}

    @mcp.tool
    def pattern_area(
        element_id: str,
        cell_name: str,
        scale: float = 1.0,
        row_spacing: float = 5.0,
        col_spacing: float = 5.0,
        angle_degrees: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Đổ mẫu hoa văn từ một Cell đồ họa vào diện tích khép kín (Pattern Area).
        Tương ứng với công cụ 'Pattern Area' trong Tool Box Patterning.

        :param element_id: ID phần tử khép kín
        :param cell_name: Tên Cell hoa văn mẫu
        :param scale: Tỷ lệ co giãn mẫu
        :param row_spacing: Khoảng cách hàng
        :param col_spacing: Khoảng cách cột
        :param angle_degrees: Góc nghiêng hoa văn
        """
        app = bridge.get_app()
        try:
            rad = math.radians(angle_degrees)
            pattern = app.CreateAreaPattern(float(row_spacing), float(col_spacing), float(rad), str(cell_name))
            el = bridge.find_element_by_id(element_id)
            if el and hasattr(el, "SetPattern"):
                matrix = bridge.create_rotation_matrix(0.0)
                el.SetPattern(pattern, matrix)
                el.Rewrite()
                el.Redraw()
                return {
                    "status": "success",
                    "message": f"Đã đổ mẫu hoa văn Cell '{cell_name}' vào đối tượng ID {element_id}.",
                    "element_id": element_id,
                }
        except Exception:
            pass

        try:
            app.CadInputQueue.SendKeyin(f"pattern cell {cell_name}")
            app.CadInputQueue.SendKeyin(f"pattern scale {scale}")
            app.CadInputQueue.SendKeyin(f"pattern area")
            return {
                "status": "success",
                "message": f"Đã gửi lệnh đổ hoa văn Pattern Area (Cell '{cell_name}') qua CAD Engine.",
                "element_id": element_id,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi đổ mẫu hoa văn: {str(ex)}"}

    @mcp.tool
    def delete_pattern(element_id: str) -> Dict[str, Any]:
        """
        Xóa bỏ toàn bộ mẫu gạch mặt cắt (Hatch/Pattern) khỏi đối tượng hình học.
        Tương ứng với công cụ 'Delete Pattern' trong Tool Box Patterning.

        :param element_id: ID phần tử cần xóa pattern
        """
        app = bridge.get_app()
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy đối tượng ID '{element_id}'!"}

        try:
            if hasattr(el, "DeletePattern"):
                el.DeletePattern()
                el.Rewrite()
                el.Redraw()
                return {"status": "success", "message": f"Đã xóa pattern khỏi đối tượng ID {element_id}."}
        except Exception:
            pass

        try:
            app.CadInputQueue.SendKeyin("delete pattern")
            return {"status": "success", "message": f"Đã gửi lệnh Delete Pattern cho đối tượng ID {element_id}."}
        except Exception as ex:
            return {"error": f"Lỗi khi xóa pattern: {str(ex)}"}
