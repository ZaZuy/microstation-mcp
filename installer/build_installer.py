"""
installer/build_installer.py
Đóng gói thành 1 file cài đặt duy nhất: Vigela_AI_App.exe
Bên trong nhúng sẵn Vigela_AI_Launcher.exe (standalone, không cần Python).
Người dùng chỉ cần nhấp đúp Vigela_AI_App.exe để cài đặt và chạy.
"""

import os
import sys
import shutil
import subprocess

INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(INSTALLER_DIR)
SETUP_GUI = os.path.join(INSTALLER_DIR, "setup_gui.py")
LAUNCHER_PY = os.path.join(PROJECT_ROOT, "launcher", "ai_launcher.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_temp")
LAUNCHER_EXE_NAME = "Vigela_AI_Launcher"
INSTALLER_EXE_NAME = "Vigela_AI_App"


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

    # --- BƯỚC 1: Đóng gói Standalone Launcher (không cần Python) ---
    print("\n[1/2] Đang đóng gói Vigela_AI_Launcher.exe (standalone)...")
    launcher_cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
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

    # --- BƯỚC 2: Đóng gói Installer và nhúng Launcher vào bên trong ---
    print("\n[2/2] Đang đóng gói bộ cài đặt Vigela_AI_App.exe (nhúng launcher)...")
    installer_cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
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
        # Nhúng Vigela_AI_Launcher.exe vào bên trong bộ cài
        "--add-data", f"{launcher_exe};.",
        "--hidden-import", "winreg",
        SETUP_GUI
    ]
    res2 = subprocess.run(installer_cmd, cwd=PROJECT_ROOT)
    if res2.returncode != 0:
        print("Lỗi: Không thể đóng gói bộ cài đặt Vigela_AI_App.exe!")
        return False

    # Dọn dẹp launcher exe riêng lẻ, chỉ giữ lại bộ cài đặt tổng hợp
    if os.path.exists(launcher_exe):
        os.remove(launcher_exe)

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

