"""
src/core/screenshot.py
Module chụp ảnh màn hình MicroStation V8i và trả về Base64 PNG.
Tương thích chuẩn MCP ImageContent (giống AutoCAD MCP).
"""

import base64
import io
import os
import tempfile
from typing import Optional, Tuple
from src.core.ms_bridge import bridge

try:
    import win32gui
    import win32ui
    import win32con
    from PIL import Image
    HAS_WIN32_PIL = True
except ImportError:
    HAS_WIN32_PIL = False


def capture_microstation_screenshot(view_number: int = 1) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Chụp ảnh màn hình khung nhìn của MicroStation V8i.
    
    :param view_number: Số hiệu cửa sổ View (1 đến 8, mặc định 1)
    :return: (thành_công, base64_png, thông_báo_lỗi)
    """
    app = bridge.get_app()
    if not app:
        return False, None, "Không kết nối được với MicroStation V8i"

    # Cách 1: Chụp trực tiếp từ HWND của View thông qua Win32 GDI
    if HAS_WIN32_PIL:
        try:
            dgn = bridge.get_active_file()
            if 1 <= view_number <= dgn.Views.Count:
                v = dgn.Views(view_number)
                hwnd = int(getattr(v, "HWND", 0))
                
                # Nếu không lấy được HWND của View, thử lấy HWND chính của MicroStation
                if not hwnd:
                    hwnd = int(getattr(app, "hWnd", 0))

                if hwnd and win32gui.IsWindow(hwnd):
                    left, top, right, bot = win32gui.GetClientRect(hwnd)
                    w = right - left
                    h = bot - top
                    if w > 10 and h > 10:
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
                        
                        # Giải phóng GDI resources
                        win32gui.DeleteObject(save_bitmap.GetHandle())
                        save_dc.DeleteDC()
                        mfc_dc.DeleteDC()
                        win32gui.ReleaseDC(hwnd, hwnd_dc)

                        # Chuyển ảnh sang Base64 PNG
                        buffer = io.BytesIO()
                        im.save(buffer, format="PNG")
                        b64_str = base64.b64encode(buffer.getvalue()).decode("ascii")
                        return True, b64_str, None
        except Exception as ex:
            # Fallback sang cách 2
            pass

    # Cách 2: Sử dụng lệnh Key-in "save image" của MicroStation
    try:
        temp_dir = tempfile.gettempdir()
        temp_img = os.path.join(temp_dir, f"ms_view_{view_number}_capture.png")
        if os.path.exists(temp_img):
            try:
                os.remove(temp_img)
            except Exception:
                pass

        app.CadInputQueue.SendKeyin(f'save image "{temp_img}"')
        
        # Đợi file sinh ra
        import time
        for _ in range(10):
            time.sleep(0.1)
            if os.path.exists(temp_img) and os.path.getsize(temp_img) > 100:
                break

        if os.path.exists(temp_img):
            with open(temp_img, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("ascii")
            try:
                os.remove(temp_img)
            except Exception:
                pass
            return True, b64_str, None
        else:
            return False, None, "MicroStation không xuất được file ảnh qua key-in"
    except Exception as ex:
        return False, None, f"Lỗi khi chụp màn hình MicroStation: {ex}"
