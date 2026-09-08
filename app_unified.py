"""
app_unified.py
File thực thi HỢP NHẤT (All-in-One) của Vigela AI CAD.
Hợp nhất:
  - MCP Server (--mcp): Cho các AI Agent kết nối MicroStation V8i (62 công cụ CAD)
  - Installer Wizard (lần đầu): Chạy setup_gui khi chưa cài đặt hoặc truyền --install
  - GUI Dashboard Launcher (khi nhấp đúp và đã cài đặt): Quản lý tiến trình, tự đồng bộ cấu hình
"""

import os
import sys
import ctypes

# Thiết lập đường dẫn dự án
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Thư mục cài đặt mặc định
INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs",
    "MicroStation-AI-CAD",
)

# Tệp đánh dấu đã hoàn tất cài đặt
INSTALL_MARKER = os.path.join(INSTALL_DIR, ".installed")


def is_mcp_mode() -> bool:
    """Kiểm tra xem tiến trình có đang được gọi ở chế độ MCP Server hay không."""
    if "--mcp" in sys.argv:
        return True
    if len(sys.argv) > 1 and sys.argv[1] in ("--transport", "stdio", "--port", "--host"):
        return True
    return False


def is_install_mode() -> bool:
    """Kiểm tra xem có cần chạy installer hay không."""
    # Bắt buộc install khi truyền tham số --install
    if "--install" in sys.argv:
        return True

    # Lấy đường dẫn exe đang chạy hiện tại
    if getattr(sys, "frozen", False):
        # Đang chạy dưới dạng PyInstaller exe
        current_exe = os.path.normcase(os.path.abspath(sys.executable))
    else:
        # Đang chạy dưới dạng script Python (dev mode)
        current_exe = os.path.normcase(os.path.abspath(sys.argv[0]))

    # Đường dẫn exe trong thư mục cài đặt
    installed_exe = os.path.normcase(os.path.join(INSTALL_DIR, "Vigela_AI_App.exe"))

    # Nếu exe đang chạy KHÔNG nằm trong thư mục cài đặt → cần cài đặt
    if current_exe != installed_exe:
        return True

    # Đang chạy từ thư mục cài đặt nhưng chưa có marker → cần cài lại
    if not os.path.exists(INSTALL_MARKER):
        return True

    return False


def hide_console():
    """Ẩn cửa sổ console trên Windows."""
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass


def main():
    if is_mcp_mode():
        # --- CHẾ ĐỘ 1: MCP SERVER (Console / stdio) ---
        from src.main import main as run_mcp_server
        run_mcp_server()

    elif is_install_mode():
        # --- CHẾ ĐỘ 2: INSTALLER WIZARD (lần đầu hoặc --install) ---
        hide_console()
        from installer.setup_gui import main as run_installer
        run_installer()

    else:
        # --- CHẾ ĐỘ 3: GUI LAUNCHER DASHBOARD (đã cài đặt) ---
        hide_console()
        from launcher.ai_launcher import main as run_launcher
        run_launcher()


if __name__ == "__main__":
    main()

