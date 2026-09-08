"""
installer/build_installer.py
Đóng gói VIGELA AI APP thành 1 FILE DUY NHẤT HỢP NHẤT: Vigela_AI_App.exe
Hợp nhất toàn bộ:
  - GUI Launcher Dashboard (khi nhấp đúp)
  - MCP Server (khi chạy với --mcp)
  - 62 công cụ CAD kết nối MicroStation V8i
"""

import os
import sys
import shutil
import subprocess

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(INSTALLER_DIR)
UNIFIED_PY = os.path.join(PROJECT_ROOT, "app_unified.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_temp")
APP_EXE_NAME = "Vigela_AI_App"


def build_exe():
    print("=" * 60)
    print("ĐÓNG GÓI VIGELA AI APP (HỢP NHẤT 1 FILE DUY NHẤT)")
    print("=" * 60)

    py_exe = sys.executable
    if py_exe.lower().endswith("pythonw.exe"):
        py_exe = py_exe[:-5] + ".exe"

    icon_path = os.path.join(PROJECT_ROOT, "assets", "vigela_icon.ico")

    # Xóa sạch thư mục build & dist cũ
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    print("\nĐang đóng gói Vigela_AI_App.exe (Hợp nhất GUI + MCP Server)...")
    cmd = [
        py_exe, "-m", "PyInstaller",
        "--onefile",
        "--name", APP_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'launcher')};launcher",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'assets')};assets",
        "--hidden-import", "fastmcp",
        "--hidden-import", "anyio",
        "--hidden-import", "anyio.abc",
        "--hidden-import", "anyio._backends._asyncio",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32api",
        "--hidden-import", "pywintypes",
        "--hidden-import", "winreg",
        "--hidden-import", "win32gui",
        "--hidden-import", "win32ui",
        "--hidden-import", "win32con",
        "--hidden-import", "PIL",
        "--noconsole",
        "--collect-all", "fastmcp",
        UNIFIED_PY
    ]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print("Lỗi khi đóng gói Vigela_AI_App.exe!")
        return False

    app_exe = os.path.join(DIST_DIR, f"{APP_EXE_NAME}.exe")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    print("\n" + "=" * 60)
    print("ĐÓNG GÓI HOÀN TẤT THÀNH CÔNG!")
    print(f"File duy nhất: {app_exe} ({os.path.getsize(app_exe)//1024//1024} MB)")
    print("Ứng dụng hợp nhất 2-trong-1:")
    print("  - Nhấp đúp chuột: Mở giao diện Vigela AI Dashboard")
    print("  - Chạy tham số --mcp: Chạy MCP Server kết nối Claude Desktop & Antigravity")
    print("=" * 60)
    return True

if __name__ == "__main__":
    build_exe()
