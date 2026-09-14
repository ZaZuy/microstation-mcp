"""
src/tools/solids_3d.py
Các công cụ dựng hình khối 3D nguyên thủy (3D Primitives) trong MicroStation V8i.
Tương ứng với Tool Box '3D Primitives' / 'Solids' trong MicroStation V8i.
"""

from typing import Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_solids_tools(mcp):
    """Đăng ký các công cụ khối 3D vào MCP Server."""

    @mcp.tool
    def draw_slab(
        origin_x: float,
        origin_y: float,
        origin_z: float,
        length_x: float,
        length_y: float,
        height_z: float,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dựng một khối hộp chữ nhật 3D (Solid Slab / Box).
        Tương ứng với công cụ 'Place Slab' trong Tool Box 3D Primitives.

        :param origin_x: Tọa độ X góc gốc
        :param origin_y: Tọa độ Y góc gốc
        :param origin_z: Tọa độ Z góc gốc
        :param length_x: Chiều dài theo trục X
        :param length_y: Chiều rộng theo trục Y
        :param height_z: Chiều cao theo trục Z
        :param level: Tên Level
        :param color: Chỉ số màu
        """
        app = bridge.get_app()
        try:
            cmd = f"place slab block; dx={length_x},{length_y},{height_z}"
            app.CadInputQueue.SendKeyin(f"place slab block")
            p_org = bridge.create_point(origin_x, origin_y, origin_z)
            p_diag = bridge.create_point(origin_x + length_x, origin_y + length_y, origin_z + height_z)
            app.CadInputQueue.SendDataPoint(p_org, 1)
            app.CadInputQueue.SendDataPoint(p_diag, 1)
            app.CadInputQueue.SendReset()

            return {
                "status": "success",
                "message": f"Đã dựng khối hộp 3D (Slab) kích thước {length_x} x {length_y} x {height_z} tại ({origin_x}, {origin_y}, {origin_z}).",
                "origin": [origin_x, origin_y, origin_z],
                "dimensions": [length_x, length_y, height_z],
            }
        except Exception as ex:
            return {"error": f"Lỗi khi dựng khối 3D Slab: {str(ex)}"}

    @mcp.tool
    def draw_cylinder(
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
        height_z: float,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dựng một hình trụ tròn 3D (Cylinder / Cone) với bán kính đáy R và chiều cao H.
        Tương ứng với công cụ 'Place Cylinder' trong Tool Box 3D Primitives.

        :param center_x: Tọa độ X tâm đáy
        :param center_y: Tọa độ Y tâm đáy
        :param center_z: Tọa độ Z tâm đáy
        :param radius: Bán kính đáy hình trụ
        :param height_z: Chiều cao hình trụ
        :param level: Tên Level
        :param color: Chỉ số màu
        """
        app = bridge.get_app()
        try:
            p_base = bridge.create_point(center_x, center_y, center_z)
            p_top = bridge.create_point(center_x, center_y, center_z + height_z)
            cone_elem = bridge.unwrap(app.CreateConeElement2(None, float(radius), p_base, p_top))
            bridge.apply_symbology(cone_elem, level=level, color=color)
            bridge.add_element(cone_elem)
            new_id = str(getattr(cone_elem, "ID64", getattr(cone_elem, "ID", "")))

            return {
                "status": "success",
                "message": f"Đã dựng hình trụ 3D (Cylinder ID {new_id}) bán kính R={radius}, cao H={height_z}.",
                "element_id": new_id,
            }
        except Exception as ex:
            # Fallback keyin
            try:
                app.CadInputQueue.SendKeyin(f"place cylinder radius {radius} height {height_z}")
                app.CadInputQueue.SendDataPoint(bridge.create_point(center_x, center_y, center_z), 1)
                app.CadInputQueue.SendReset()
                return {"status": "success", "message": f"Đã gửi lệnh dựng hình trụ qua CAD Engine."}
            except Exception as ex2:
                return {"error": f"Lỗi khi dựng hình trụ 3D: {str(ex)} | {str(ex2)}"}

    @mcp.tool
    def draw_sphere(
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dựng một khối cầu tròn 3D (Sphere) với tâm C và bán kính R.
        Tương ứng với công cụ 'Place Sphere' trong Tool Box 3D Primitives.

        :param center_x: Tọa độ X tâm cầu
        :param center_y: Tọa độ Y tâm cầu
        :param center_z: Tọa độ Z tâm cầu
        :param radius: Bán kính khối cầu
        :param level: Tên Level
        :param color: Chỉ số màu
        """
        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin(f"place sphere radius {radius}")
            app.CadInputQueue.SendDataPoint(bridge.create_point(center_x, center_y, center_z), 1)
            app.CadInputQueue.SendReset()
            return {
                "status": "success",
                "message": f"Đã dựng khối cầu 3D (Sphere) tâm ({center_x}, {center_y}, {center_z}) bán kính R={radius}.",
            }
        except Exception as ex:
            return {"error": f"Lỗi khi dựng khối cầu: {str(ex)}"}

    @mcp.tool
    def draw_torus(
        center_x: float,
        center_y: float,
        center_z: float,
        primary_radius: float,
        secondary_radius: float,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dựng một hình xuyến 3D (Torus - hình vành khăn / bánh donut).
        Tương ứng với công cụ 'Place Torus' trong Tool Box 3D Primitives.

        :param center_x: Tọa độ X tâm
        :param center_y: Tọa độ Y tâm
        :param center_z: Tọa độ Z tâm
        :param primary_radius: Bán kính vòng ngoài
        :param secondary_radius: Bán kính tiết diện ống tròn
        :param level: Tên Level
        :param color: Chỉ số màu
        """
        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin(f"place torus radius1 {primary_radius} radius2 {secondary_radius}")
            app.CadInputQueue.SendDataPoint(bridge.create_point(center_x, center_y, center_z), 1)
            app.CadInputQueue.SendReset()
            return {
                "status": "success",
                "message": f"Đã dựng hình xuyến 3D (Torus) R1={primary_radius}, R2={secondary_radius}.",
            }
        except Exception as ex:
            return {"error": f"Lỗi khi dựng hình xuyến: {str(ex)}"}
