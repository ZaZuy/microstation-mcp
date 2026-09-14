"""
src/tools/raster.py
Các công cụ quản lý, đính kèm và điều khiển ảnh quét Raster (TIFF, GeoTIFF, PNG, JPG, PDF)
thông qua Raster Manager trong MicroStation V8i.
"""

import os
from typing import Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_raster_tools(mcp):
    """Đăng ký các công cụ Raster Manager vào MCP Server."""

    @mcp.tool
    def attach_raster_image(
        image_path: str,
        view_number: int = 1,
        fixed: bool = True,
    ) -> Dict[str, Any]:
        """
        Đính kèm một file ảnh quét (TIFF, GeoTIFF, PNG, JPG, BMP) vào bản vẽ MicroStation V8i
        làm lớp ảnh nền (Raster Underlay) qua Raster Manager.

        :param image_path: Đường dẫn tuyệt đối đến file ảnh quét
        :param view_number: Số hiệu View hiển thị ảnh (mặc định 1)
        :param fixed: Nếu True, tự động gắn cố định không mở hộp thoại tương tác
        """
        if not os.path.exists(image_path):
            return {"error": f"Không tìm thấy file ảnh: '{image_path}'"}

        app = bridge.get_app()
        norm_path = os.path.abspath(image_path)

        try:
            # Nạp MDL Raster nếu chưa nạp
            app.CadInputQueue.SendKeyin("mdl load raster")
        except Exception:
            pass

        try:
            flag = "fixed" if fixed else "interactive"
            cmd = f'raster attach {flag} "{norm_path}"'
            app.CadInputQueue.SendKeyin(cmd)
            app.CadInputQueue.SendKeyin(f"raster fit {view_number}")
            app.CadInputQueue.SendKeyin("update all")

            return {
                "status": "success",
                "message": f"Đã đính kèm ảnh raster '{os.path.basename(norm_path)}' vào bản vẽ và căn vừa View {view_number}.",
                "image_path": norm_path,
                "view": view_number,
            }
        except Exception as ex:
            return {"error": f"Lỗi khi đính kèm ảnh raster: {str(ex)}"}

    @mcp.tool
    def detach_raster_image(
        detach_all: bool = True,
        raster_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gỡ bỏ ảnh quét raster khỏi bản vẽ MicroStation V8i.

        :param detach_all: Nếu True, gỡ bỏ toàn bộ các file ảnh raster đang đính kèm
        :param raster_index: Chỉ số raster cụ thể cần gỡ (nếu detach_all=False)
        """
        app = bridge.get_app()
        try:
            if detach_all:
                app.CadInputQueue.SendKeyin("raster detach all")
                msg = "Đã gỡ bỏ toàn bộ ảnh raster khỏi bản vẽ."
            else:
                idx = raster_index if raster_index is not None else 1
                app.CadInputQueue.SendKeyin(f"raster detach {idx}")
                msg = f"Đã gỡ bỏ ảnh raster số {idx}."

            app.CadInputQueue.SendKeyin("update all")
            return {"status": "success", "message": msg}
        except Exception as ex:
            return {"error": f"Lỗi khi gỡ ảnh raster: {str(ex)}"}

    @mcp.tool
    def fit_raster(view_number: int = 1) -> str:
        """
        Tự động căn chỉnh khung nhìn (Zoom fit) vừa khít với phạm vi ảnh raster đang mở.

        :param view_number: Số hiệu View cần căn (mặc định 1)
        """
        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin(f"raster fit {view_number}")
            app.CadInputQueue.SendKeyin("update all")
            return f"Đã căn khung nhìn View {view_number} khớp với phạm vi ảnh raster."
        except Exception as ex:
            return f"Lỗi khi căn khung nhìn raster: {str(ex)}"

    @mcp.tool
    def set_raster_display(
        display: bool = True,
        view_number: int = 1,
    ) -> str:
        """
        Bật hoặc tắt hiển thị ảnh quét raster trên màn hình MicroStation V8i.

        :param display: True để hiển thị, False để ẩn ảnh
        :param view_number: Số hiệu View cần thao tác
        """
        app = bridge.get_app()
        state = "on" if display else "off"
        try:
            app.CadInputQueue.SendKeyin(f"raster display {state} {view_number}")
            app.CadInputQueue.SendKeyin("update all")
            return f"Đã {'bật' if display else 'tắt'} hiển thị ảnh raster trên View {view_number}."
        except Exception as ex:
            return f"Lỗi khi đổi trạng thái hiển thị raster: {str(ex)}"
