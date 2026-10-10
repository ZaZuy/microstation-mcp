"""
src/core/screenshot.py
Module chụp ảnh màn hình MicroStation V8i chuyên nghiệp.
Học hỏi và nâng cấp từ Win32ScreenshotProvider của AutoCAD MCP v3.1:
1. Xử lý Per-Monitor DPI Awareness (chống méo hình khi màn hình scale 125%/150%).
2. Sử dụng Win32 PrintWindow (PW_RENDERFULLCONTENT = 2) cho phép chụp cả khi cửa sổ bị che.
3. Fallback BitBlt trên Device Context nếu PrintWindow không hỗ trợ.
4. Fallback MicroStation Key-in 'save image' nếu chạy headless/remote desktop.
5. Quản lý tài nguyên GDI nghiêm ngặt (luôn giải phóng handle trong finally).
6. Mã hóa trực tiếp sang Base64 PNG chuẩn MCP ImageContent.
"""

from __future__ import annotations
import base64
import io
import os
import sys
import tempfile
import time
from typing import Optional, Tuple
import logging

from src.core.ms_bridge import bridge

logger = logging.getLogger(__name__)

# Cờ khởi tạo DPI một lần duy nhất
_DPI_INITIALIZED = False


def ensure_dpi_awareness() -> None:
    """Đảm bảo tiến trình nhận diện đúng DPI của màn hình Windows."""
    global _DPI_INITIALIZED
    if _DPI_INITIALIZED or sys.platform != "win32":
        return

    import ctypes
    user32 = ctypes.windll.user32

    # 1. Thử Per-Monitor V2 (Windows 10 1703+)
    try:
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            dpi_aware_v2 = ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            if user32.SetProcessDpiAwarenessContext(dpi_aware_v2):
                _DPI_INITIALIZED = True
                return
    except Exception:
        pass

    # 2. Thử SetProcessDpiAwareness qua Shcore.dll (Windows 8.1+)
    try:
        shcore = ctypes.windll.shcore
        PROCESS_PER_MONITOR_DPI_AWARE = 2
        if shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE) == 0:
            _DPI_INITIALIZED = True
            return
    except Exception:
        pass

    # 3. Fallback SetProcessDPIAware cơ bản
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

    _DPI_INITIALIZED = True


def capture_microstation_screenshot(view_number: int = 1) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Chụp ảnh khung nhìn của MicroStation V8i và trả về Base64 PNG.
    
    :param view_number: Số hiệu View cần chụp (1 đến 8, mặc định 1)
    :return: (thành_công, base64_png, lỗi_nếu_có)
    """
    if sys.platform != "win32":
        return False, None, "Tính năng chỉ hỗ trợ trên Windows"

    app = bridge.get_app()
    if not app:
        return False, None, "Không thể kết nối tới MicroStation V8i"

    ensure_dpi_awareness()

    # Xác định HWND của cửa sổ View hoặc cửa sổ chính
    hwnd = None
    try:
        dgn = bridge.get_active_file()
        if 1 <= view_number <= dgn.Views.Count:
            v = dgn.Views(view_number)
            hwnd = int(getattr(v, "HWND", 0))
    except Exception:
        pass

    if not hwnd:
        try:
            hwnd = int(getattr(app, "hWnd", 0))
        except Exception:
            pass

    # --- Phương pháp 1: Chụp qua Win32 PrintWindow / BitBlt ---
    if hwnd:
        try:
            import ctypes
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            if win32gui.IsWindow(hwnd):
                left, top, right, bot = win32gui.GetClientRect(hwnd)
                width = right - left
                height = bot - top

                if width > 10 and height > 10:
                    hwnd_dc = None
                    mfc_dc = None
                    save_dc = None
                    bitmap = None

                    try:
                        hwnd_dc = win32gui.GetDC(hwnd)
                        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                        save_dc = mfc_dc.CreateCompatibleDC()

                        bitmap = win32ui.CreateBitmap()
                        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
                        save_dc.SelectObject(bitmap)

                        # Thử PrintWindow với cờ PW_RENDERFULLCONTENT (0x00000002)
                        PW_RENDERFULLCONTENT = 2
                        pw_res = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
                        
                        # Nếu PrintWindow không ra ảnh, fallback BitBlt
                        if pw_res != 1:
                            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

                        bmpinfo = bitmap.GetInfo()
                        bmpstr = bitmap.GetBitmapBits(True)

                        img = Image.frombuffer(
                            "RGB",
                            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                            bmpstr,
                            "raw",
                            "BGRX",
                            0,
                            1,
                        )

                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        buf.seek(0)
                        b64_str = base64.b64encode(buf.read()).decode("ascii")
                        return True, b64_str, None

                    finally:
                        if bitmap is not None:
                            win32gui.DeleteObject(bitmap.GetHandle())
                        if save_dc is not None:
                            save_dc.DeleteDC()
                        if mfc_dc is not None:
                            mfc_dc.DeleteDC()
                        if hwnd_dc is not None:
                            win32gui.ReleaseDC(hwnd, hwnd_dc)

        except Exception as ex:
            logger.warning(f"Win32 capture thất bại, chuyển sang phương án MicroStation Key-in: {ex}")

    # --- Phương pháp 2: Fallback dùng MicroStation native keyin 'save image' ---
    try:
        temp_dir = tempfile.gettempdir()
        temp_img = os.path.join(temp_dir, f"ms_capture_view{view_number}_{int(time.time()*1000)}.png")
        if os.path.exists(temp_img):
            try:
                os.remove(temp_img)
            except Exception:
                pass

        app.CadInputQueue.SendKeyin(f'save image "{temp_img}"')

        # Chờ file xuất hiện (tối đa 1 giây)
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
            return False, None, "Không thể trích xuất ảnh từ MicroStation V8i"

    except Exception as ex:
        return False, None, f"Lỗi chụp màn hình: {ex}"
