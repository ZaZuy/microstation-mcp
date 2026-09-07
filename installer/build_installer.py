"""
installer/build_installer.py
Kịch bản tự động đóng gói toàn bộ dự án thành file cài đặt độc lập Setup_MicroStation_AI.exe.
"""

import os
import sys
import shutil
import subprocess

INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(INSTALLER_DIR)
SETUP_GUI = os.path.join(INSTALLER_DIR, "setup_gui.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_temp")


def build_exe():
    print("=" * 60)
    print("BẮT ĐẦU ĐÓNG GÓI DUY NHẤT 1 FILE: VIGELA_AI_APP.EXE")
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

    # Đóng gói duy nhất 1 file cài đặt trọn gói: Vigela_AI_App.exe
    cmd = [
        py_exe,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "Vigela_AI_App",
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
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'README.md')};.",
        SETUP_GUI
    ]

    print("Đang biên dịch file duy nhất bằng PyInstaller...")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if res.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "Vigela_AI_App.exe")
        print("\n" + "=" * 60)
        print("ĐÓNG GÓI HOÀN TẤT!")
        print(f"File cài đặt duy nhất: {exe_path}")
        print("=" * 60)
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        return True
    else:
        print("Đóng gói thất bại! Mã lỗi:", res.returncode)
        return False


if __name__ == "__main__":
    build_exe()
