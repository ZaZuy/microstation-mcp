"""
src/tools/view.py
Các công cụ quản lý khung nhìn, điều khiển phóng to, thu nhỏ, pan và chụp ảnh bản vẽ trong MicroStation V8i.
"""

import os
from typing import Dict, Any, Optional
from src.core.ms_bridge import bridge


def register_view_tools(mcp):
    """Đăng ký các tool quản lý khung nhìn vào MCP Server."""

    @mcp.tool
    def fit_view(view_number: int = 1) -> str:
        """
        Căn toàn bộ nội dung bản vẽ vào cửa sổ khung nhìn (Fit View).

        :param view_number: Số hiệu cửa sổ View (1 đến 8, mặc định 1)
        """
        app = bridge.get_app()
        try:
            if 1 <= view_number <= app.Views.Count:
                app.Views(view_number).Fit(True)
                app.Views(view_number).Redraw()
                return f"Đã căn toàn màn hình cho View {view_number}."
        except Exception:
            pass

        # Fallback dùng Key-in
        app.CadInputQueue.SendKeyin(f"fit view {view_number}")
        return f"Đã gửi lệnh Fit View {view_number}."

    @mcp.tool
    def zoom_window(
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        view_number: int = 1,
    ) -> str:
        """
        Phóng to khung nhìn vào một vùng tọa độ hình chữ nhật xác định.

        :param min_x: Tọa độ X góc dưới trái
        :param min_y: Tọa độ Y góc dưới trái
        :param max_x: Tọa độ X góc trên phải
        :param max_y: Tọa độ Y góc trên phải
        :param view_number: Số hiệu View (mặc định 1)
        """
        app = bridge.get_app()
        try:
            v = app.Views(view_number)
            p1 = bridge.create_point(min_x, min_y, 0.0)
            p2 = bridge.create_point(max_x, max_y, 0.0)
            v.ZoomWindow(p1, p2)
            v.Redraw()
            return f"Đã zoom View {view_number} vào vùng [{min_x}, {min_y}] -> [{max_x}, {max_y}]."
        except Exception:
            # Fallback dùng Key-in
            app.CadInputQueue.SendKeyin(f"window view {view_number}; xy={min_x},{min_y}; xy={max_x},{max_y}")
            return f"Đã gửi lệnh zoom window View {view_number} vào vùng [{min_x}, {min_y}] -> [{max_x}, {max_y}]."

    @mcp.tool
    def pan_view(dx: float, dy: float, view_number: int = 1) -> str:
        """
        Dịch chuyển vùng quan sát của khung nhìn (Pan) theo độ dời (dX, dY).

        :param dx: Độ dời X theo đơn vị bản vẽ
        :param dy: Độ dời Y theo đơn vị bản vẽ
        :param view_number: Số hiệu View (mặc định 1)
        """
        app = bridge.get_app()
        try:
            v = app.Views(view_number)
            orig = v.Origin
            new_orig = bridge.create_point(orig.X + dx, orig.Y + dy, orig.Z)
            v.Origin = new_orig
            v.Redraw()
            return f"Đã pan View {view_number} theo độ dời ({dx}, {dy})."
        except Exception:
            app.CadInputQueue.SendKeyin(f"pan view {view_number}; xy={dx},{dy}")
            return f"Đã gửi lệnh pan View {view_number}."

    @mcp.tool
    def zoom_in(factor: float = 2.0, view_number: int = 1) -> str:
        """
        Phóng to khung nhìn theo một hệ số tỉ lệ.

        :param factor: Hệ số phóng to (mặc định 2.0)
        :param view_number: Số hiệu View (mặc định 1)
        """
        app = bridge.get_app()
        app.CadInputQueue.SendKeyin(f"zoom in {factor}")
        return f"Đã phóng to View {view_number} tỉ lệ {factor}x."

    @mcp.tool
    def zoom_out(factor: float = 2.0, view_number: int = 1) -> str:
        """
        Thu nhỏ khung nhìn theo một hệ số tỉ lệ.

        :param factor: Hệ số thu nhỏ (mặc định 2.0)
        :param view_number: Số hiệu View (mặc định 1)
        """
        app = bridge.get_app()
        app.CadInputQueue.SendKeyin(f"zoom out {factor}")
        return f"Đã thu nhỏ View {view_number} tỉ lệ {factor}x."

    @mcp.tool
    def get_view_info(view_number: int = 1) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết về khung nhìn hiện tại (tọa độ gốc, kích thước vùng hiển thị, trạng thái mở).

        :param view_number: Số hiệu View (1 đến 8)
        """
        app = bridge.get_app()
        if not (1 <= view_number <= app.Views.Count):
            return {"error": f"View số {view_number} không hợp lệ!"}

        v = app.Views(view_number)
        return {
            "view_number": view_number,
            "is_open": bool(v.IsOpen),
            "origin": [round(v.Origin.X, 3), round(v.Origin.Y, 3), round(v.Origin.Z, 3)],
            "extents": [round(v.Extents.X, 3), round(v.Extents.Y, 3), round(v.Extents.Z, 3)],
        }

    @mcp.tool
    def capture_view_image(output_path: str, view_number: int = 1) -> str:
        """
        Chụp khung nhìn hiện tại của MicroStation và xuất ra file ảnh (PNG hoặc JPG) để AI quan sát trực quan.

        :param output_path: Đường dẫn tuyệt đối file ảnh cần lưu (ví dụ 'D:\\output\\view1.png')
        :param view_number: Số hiệu View cần chụp
        """
        app = bridge.get_app()
        norm_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(norm_path), exist_ok=True)

        # Thử chụp trực tiếp từ HWND của View window qua Win32 GDI & PIL
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            v = app.Views(view_number)
            hwnd = int(getattr(v, "HWND", 0))
            if hwnd:
                left, top, right, bot = win32gui.GetClientRect(hwnd)
                w = right - left
                h = bot - top
                if w > 0 and h > 0:
                    hwnd_dc = win32gui.GetDC(hwnd)
                    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                    save_dc = mfc_dc.CreateCompatibleDC()
                    save_bitmap = win32ui.CreateBitmap()
                    save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
                    save_dc.SelectObject(save_bitmap)
                    save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)
                    bmpinfo = save_bitmap.GetInfo()
                    bmpstr = save_bitmap.GetBitmapBits(True)
                    im = Image.frombuffer(
                        "RGB",
                        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                        bmpstr, "raw", "BGRX", 0, 1
                    )
                    im.save(norm_path)
                    win32gui.DeleteObject(save_bitmap.GetHandle())
                    save_dc.DeleteDC()
                    mfc_dc.DeleteDC()
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
                    return f"Đã chụp khung nhìn View {view_number} thành công lưu tại: '{norm_path}'"
        except Exception:
            pass

        # Fallback Key-in
        try:
            cmd = f'save image "{norm_path}"'
            app.CadInputQueue.SendKeyin(cmd)
            return f"Đã gửi lệnh chụp màn hình View {view_number} lưu tại '{norm_path}'"
        except Exception as ex:
            return f"Lỗi khi chụp màn hình View: {ex}"
