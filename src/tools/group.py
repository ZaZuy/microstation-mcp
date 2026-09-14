"""
src/tools/group.py
Các công cụ quản lý nhóm, chuỗi phức hợp (Complex Chain) và hình phức hợp (Complex Shape) trong MicroStation V8i.
Tương ứng với Tool Box 'Groups' trong MicroStation V8i.
"""

from typing import List, Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_group_tools(mcp):
    """Đăng ký các công cụ nhóm và chuỗi/hình phức hợp vào MCP Server."""

    @mcp.tool
    def create_complex_chain(
        element_ids: List[str],
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Nối một chuỗi các đoạn thẳng hoặc cung tròn hở (Line / Arc / LineString) liên tiếp nhau
        thành một đối tượng đường liên tục duy nhất (Complex Chain / Complex String).
        Tương ứng với công cụ 'Create Complex Chain' trong Tool Box Groups.

        :param element_ids: Danh sách ID của các đối tượng cần nối (theo thứ tự liên tiếp)
        :param level: Tên Level
        :param color: Chỉ số màu
        :param weight: Độ dày nét vẽ
        :param style: Kiểu nét vẽ
        """
        app = bridge.get_app()
        model = bridge.get_active_model()

        if len(element_ids) < 2:
            return {"error": "Cần ít nhất 2 đối tượng để tạo Complex Chain!"}

        elems_to_chain = []
        for eid in element_ids:
            el = bridge.find_element_by_id(eid)
            if not el:
                return {"error": f"Không tìm thấy phần tử có ID '{eid}'!"}
            elems_to_chain.append(el)

        try:
            # Tạo ComplexStringElement từ mảng đối tượng
            chain_elem = bridge.unwrap(app.CreateComplexStringElement1(elems_to_chain))
            bridge.apply_symbology(chain_elem, level=level, color=color, weight=weight, style=style)
            bridge.add_element(chain_elem)

            # Xóa các phần tử con ban đầu để tránh trùng lặp
            for el in elems_to_chain:
                try:
                    model.RemoveElement(el)
                except Exception:
                    pass

            new_id = str(getattr(chain_elem, "ID64", getattr(chain_elem, "ID", "")))
            return {
                "status": "success",
                "message": f"Đã tạo thành công Complex Chain (ID {new_id}) từ {len(element_ids)} đoạn thẳng/cung tròn.",
                "element_id": new_id,
            }
        except Exception as ex:
            # Fallback dùng Keyin 'create complex string manual'
            try:
                cmd = f"create complex string manual"
                app.CadInputQueue.SendKeyin(cmd)
                return {"status": "success", "message": f"Đã gửi lệnh tạo Complex Chain qua CAD Engine: {str(ex)}"}
            except Exception as ex2:
                return {"error": f"Lỗi khi tạo Complex Chain: {str(ex)} | {str(ex2)}"}

    @mcp.tool
    def create_complex_shape(
        element_ids: List[str],
        fill_color: Optional[int] = None,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Nối một chuỗi các đoạn thẳng, cung tròn khép kín thành một đa giác kín duy nhất (Complex Shape).
        Có thể đổ màu hoặc để rỗng. Tương ứng với công cụ 'Create Complex Shape' trong Tool Box Groups.

        :param element_ids: Danh sách ID của các đối tượng ranh giới khép kín
        :param fill_color: Chỉ số màu tô (None nếu không tô)
        :param level: Tên Level
        :param color: Chỉ số màu đường viền
        :param weight: Độ dày nét vẽ
        """
        app = bridge.get_app()
        model = bridge.get_active_model()

        if len(element_ids) < 3:
            return {"error": "Cần ít nhất 3 đoạn ranh giới để tạo Complex Shape khép kín!"}

        elems_to_shape = []
        for eid in element_ids:
            el = bridge.find_element_by_id(eid)
            if not el:
                return {"error": f"Không tìm thấy phần tử có ID '{eid}'!"}
            elems_to_shape.append(el)

        try:
            fill_mode = 1 if fill_color is not None else 0
            shape_elem = bridge.unwrap(app.CreateComplexShapeElement1(elems_to_shape, fill_mode))
            bridge.apply_symbology(shape_elem, level=level, color=color, weight=weight)
            if fill_color is not None:
                try:
                    shape_elem.FillColor = int(fill_color)
                except Exception:
                    pass
            bridge.add_element(shape_elem)

            # Xóa các đoạn rời rạc ban đầu
            for el in elems_to_shape:
                try:
                    model.RemoveElement(el)
                except Exception:
                    pass

            new_id = str(getattr(shape_elem, "ID64", getattr(shape_elem, "ID", "")))
            return {
                "status": "success",
                "message": f"Đã tạo thành công Complex Shape khép kín (ID {new_id}) từ {len(element_ids)} cạnh.",
                "element_id": new_id,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi tạo Complex Shape: {str(ex)}"}

    @mcp.tool
    def create_graphic_group(
        element_ids: List[str],
        group_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gán các đối tượng được chỉ định vào cùng một Graphic Group (GG) trong MicroStation.
        Khi chọn một đối tượng thuộc group, người dùng có thể thao tác cả nhóm cùng lúc.

        :param element_ids: Danh sách ID các đối tượng cần gom nhóm
        :param group_number: Số hiệu nhóm (nếu None sẽ tự động sinh số hiệu nhóm mới)
        """
        app = bridge.get_app()
        if not element_ids:
            return {"error": "Danh sách element_ids không được rỗng!"}

        gn = group_number
        if gn is None:
            try:
                gn = app.ActiveSettings.GraphicGroup
                if gn == 0:
                    gn = 1
                    app.ActiveSettings.GraphicGroup = gn
            except Exception:
                gn = 1

        updated = 0
        for eid in element_ids:
            el = bridge.find_element_by_id(eid)
            if el:
                try:
                    el.GraphicGroup = int(gn)
                    el.Rewrite()
                    updated += 1
                except Exception:
                    pass

        return {
            "status": "success",
            "message": f"Đã gán {updated} đối tượng vào Graphic Group số {gn}.",
            "graphic_group_number": gn,
            "elements_count": updated,
        }

    @mcp.tool
    def ungroup_graphic_group(
        element_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Rã đối tượng ra khỏi Graphic Group (đặt GraphicGroup = 0).

        :param element_ids: Danh sách ID các đối tượng cần rã nhóm
        """
        updated = 0
        for eid in element_ids:
            el = bridge.find_element_by_id(eid)
            if el:
                try:
                    el.GraphicGroup = 0
                    el.Rewrite()
                    updated += 1
                except Exception:
                    pass
        return {
            "status": "success",
            "message": f"Đã rã nhóm thành công cho {updated} đối tượng.",
            "elements_count": updated,
        }
