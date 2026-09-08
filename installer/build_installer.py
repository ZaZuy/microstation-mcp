"""
installer/build_installer.py
Đóng gói thành 1 file cài đặt duy nhất: Vigela_AI_App.exe
Bên trong nhúng sẵn:
  - Vigela_AI_Launcher.exe  (GUI launcher, standalone)
  - Vigela_MCP_Server.exe   (MCP server cho Claude/Antigravity, standalone)
Người dùng KHÔNG cần cài Python hay bất kỳ thứ gì thêm.
"""

import os
import sys
import shutil
import subprocess

INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(INSTALLER_DIR)
SETUP_GUI = os.path.join(INSTALLER_DIR, "setup_gui.py")
LAUNCHER_PY = os.path.join(PROJECT_ROOT, "launcher", "ai_launcher.py")
MCP_SERVER_PY = os.path.join(PROJECT_ROOT, "src", "main.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_temp")
LAUNCHER_EXE_NAME = "Vigela_AI_Launcher"
MCP_SERVER_EXE_NAME = "Vigela_MCP_Server"
INSTALLER_EXE_NAME = "Vigela_AI_App"


def build_one(py_exe, name, entry_py, extra_args, icon_path):
    """Đóng gói một file exe standalone."""
    cmd = [
        py_exe, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
    ] + extra_args + [entry_py]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return res.returncode == 0


def build_exe():
    print("=" * 60)
    print("ĐÓNG GÓI VIGELA AI APP (1 FILE DUY NHẤT)")
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

    # --- BƯỚC 1: Đóng gói Standalone GUI Launcher ---
    print("\n[1/3] Đang đóng gói Vigela_AI_Launcher.exe (GUI, standalone)...")
    launcher_cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconsole", "--onefile",
        "--name", LAUNCHER_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'launcher')};launcher",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'assets')};assets",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--hidden-import", "winreg",
        LAUNCHER_PY
    ]
    res1 = subprocess.run(launcher_cmd, cwd=PROJECT_ROOT)
    if res1.returncode != 0:
        print("Lỗi: Không thể đóng gói Vigela_AI_Launcher.exe!")
        return False
    launcher_exe = os.path.join(DIST_DIR, f"{LAUNCHER_EXE_NAME}.exe")
    print(f"    => {launcher_exe} ({os.path.getsize(launcher_exe)//1024//1024} MB)")

    # --- BƯỚC 2: Đóng gói Standalone MCP Server (console) ---
    print("\n[2/3] Đang đóng gói Vigela_MCP_Server.exe (MCP, standalone)...")
    mcp_cmd = [
        py_exe, "-m", "PyInstaller",
        "--onefile",          # console mode: Claude Desktop cần đọc stdout/stdin
        "--name", MCP_SERVER_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--hidden-import", "fastmcp",
        "--hidden-import", "anyio",
        "--hidden-import", "anyio.abc",
        "--hidden-import", "anyio._backends._asyncio",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32api",
        "--hidden-import", "pywintypes",
        "--hidden-import", "winreg",
        "--collect-all", "fastmcp",
        MCP_SERVER_PY
    ]
    res2 = subprocess.run(mcp_cmd, cwd=PROJECT_ROOT)
    if res2.returncode != 0:
        print("Lỗi: Không thể đóng gói Vigela_MCP_Server.exe!")
        return False
    mcp_exe = os.path.join(DIST_DIR, f"{MCP_SERVER_EXE_NAME}.exe")
    print(f"    => {mcp_exe} ({os.path.getsize(mcp_exe)//1024//1024} MB)")

    # --- BƯỚC 3: Đóng gói Installer và nhúng cả 2 exe vào bên trong ---
    print("\n[3/3] Đang đóng gói bộ cài đặt Vigela_AI_App.exe (nhúng launcher + MCP server)...")
    installer_cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconsole", "--onefile",
        "--name", INSTALLER_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'launcher')};launcher",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'assets')};assets",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'requirements.txt')};.",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'pyproject.toml')};.",
        # Nhúng cả 2 exe vào bên trong bộ cài
        "--add-data", f"{launcher_exe};.",
        "--add-data", f"{mcp_exe};.",
        "--hidden-import", "winreg",
        SETUP_GUI
    ]
    res3 = subprocess.run(installer_cmd, cwd=PROJECT_ROOT)
    if res3.returncode != 0:
        print("Lỗi: Không thể đóng gói bộ cài đặt Vigela_AI_App.exe!")
        return False

    # Dọn dẹp exe riêng lẻ, chỉ giữ lại bộ cài đặt tổng hợp
    for tmp_exe in [launcher_exe, mcp_exe]:
        if os.path.exists(tmp_exe):
            os.remove(tmp_exe)

    installer_path = os.path.join(DIST_DIR, f"{INSTALLER_EXE_NAME}.exe")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    print("\n" + "=" * 60)
    print("ĐÓNG GÓI HOÀN TẤT!")
    print(f"File cài đặt duy nhất: {installer_path}")
    print(f"Kích thước: {os.path.getsize(installer_path)//1024//1024} MB")
    print("Gửi file này cho người dùng, họ chỉ cần:")
    print("  1. Nhấp đúp Vigela_AI_App.exe")
    print("  2. Bấm 'Bắt Đầu Cài Đặt'")
    print("  3. Bấm 'Yes' để mở Vigela AI App")
    print("  => KHÔNG CẦN cài Python hay bất kỳ thứ gì thêm!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    build_exe()

