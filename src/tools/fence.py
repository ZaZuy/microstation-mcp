"""
src/tools/fence.py
Các công cụ đặt vùng ranh chọn (Fence) và tập hợp chọn (Selection Set) trong MicroStation V8i.
Tương ứng với Tool Box 'Fence' và 'Selection' trong MicroStation V8i.
"""

from typing import List, Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_fence_tools(mcp):
    """Đăng ký các công cụ Fence và Selection vào MCP Server."""

    @mcp.tool
    def place_fence(
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        mode: str = "inside",
    ) -> Dict[str, Any]:
        """
        Đặt một vùng Fence hình chữ nhật để thao tác hàng loạt trên bản vẽ MicroStation V8i.
        Tương ứng với công cụ 'Place Fence' trong Tool Box Fence.

        :param min_x: Tọa độ X góc dưới trái
        :param min_y: Tọa độ Y góc dưới trái
        :param max_x: Tọa độ X góc trên phải
        :param max_y: Tọa độ Y góc trên phải
        :param mode: Chế độ tác động ('inside' - bên trong, 'overlap' - chạm mép, 'clip' - cắt xén)
        """
        app = bridge.get_app()
        try:
            # Dùng keyin CAD chuẩn
            app.CadInputQueue.SendKeyin(f"set fence {mode}")
            app.CadInputQueue.SendKeyin(f"place fence block")
            pt1 = bridge.create_point(min_x, min_y, 0.0)
            pt2 = bridge.create_point(max_x, max_y, 0.0)
            app.CadInputQueue.SendDataPoint(pt1, 1)
            app.CadInputQueue.SendDataPoint(pt2, 1)

            return {
                "status": "success",
                "message": f"Đã đặt Fence chữ nhật từ ({min_x}, {min_y}) đến ({max_x}, {max_y}) ở chế độ {mode}.",
                "bounds": [min_x, min_y, max_x, max_y],
                "mode": mode,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi đặt Fence: {str(ex)}"}

    @mcp.tool
    def clear_fence() -> str:
        """
        Hủy bỏ vùng Fence đang có trên màn hình MicroStation.
        """
        app = bridge.get_app()
        try:
            app.ActiveDesignFile.Fence.Clear()
        except Exception:
            pass
        try:
            app.CadInputQueue.SendKeyin("choose default")
        except Exception:
            pass
        return "Đã hủy bỏ vùng Fence."

    @mcp.tool
    def modify_fence_contents(action: str = "delete") -> Dict[str, Any]:
        """
        Thao tác trên toàn bộ các đối tượng nằm trong vùng Fence hiện hành (Xóa, Copy, v.v.).
        Tương ứng với công cụ 'Manipulate Fence Contents' / 'Delete Fence' trong Tool Box Fence.

        :param action: Hành động thực hiện ('delete' - xóa toàn bộ đối tượng trong fence)
        """
        app = bridge.get_app()
        try:
            if action.lower() == "delete":
                app.CadInputQueue.SendKeyin("fence delete")
                # Gửi data point xác nhận
                app.CadInputQueue.SendDataPoint(bridge.create_point(0, 0, 0), 1)
                return {"status": "success", "message": "Đã thực thi lệnh xóa toàn bộ đối tượng trong Fence."}
            else:
                return {"error": f"Hành động '{action}' chưa được hỗ trợ, vui lòng chọn 'delete'."}
        except Exception as ex:
            return {"error": f"Lỗi khi thao tác trên nội dung Fence: {str(ex)}"}

    @mcp.tool
    def select_elements_by_criteria(
        level: Optional[str] = None,
        color: Optional[int] = None,
        element_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Chọn các đối tượng thỏa mãn điều kiện vào Selection Set của MicroStation.
        Tương ứng với công cụ 'Select by Attributes' trong Tool Box Selection.

        :param level: Tên Level cần chọn
        :param color: Chỉ số màu cần chọn
        :param element_type: Loại phần tử ('Line', 'LineString', 'Shape', 'Text')
        """
        app = bridge.get_app()
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache

        selected_count = 0
        try:
            # Xóa selection cũ
            app.ActiveModelReference.EmptySelectionSet()
        except Exception:
            pass

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
                if not el or not getattr(el, "IsGraphical", False):
                    continue

                if level and (not el.Level or el.Level.Name.lower() != level.lower()):
                    continue
                if color is not None and el.Color != color:
                    continue
                if element_type:
                    el_type_int = int(el.Type)
                    type_map = {"line": 3, "linestring": 4, "shape": 6, "text": 17, "cell": 2}
                    req_type = type_map.get(element_type.lower())
                    if req_type and el_type_int != req_type:
                        continue

                app.ActiveModelReference.SelectElement(el)
                selected_count += 1
            except Exception:
                continue

        return {
            "status": "success",
            "message": f"Đã chọn {selected_count} đối tượng vào Selection Set.",
            "selected_count": selected_count,
        }

    @mcp.tool
    def clear_selection() -> str:
        """
        Bỏ chọn toàn bộ đối tượng (Clear Selection Set).
        Tương ứng với nhấn chuột ra ngoài trong Element Selection.
        """
        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin("choose none")
            app.CadInputQueue.SendReset()
            return "Đã bỏ chọn toàn bộ đối tượng."
        except Exception as ex:
            return f"Lỗi khi bỏ chọn: {str(ex)}"
