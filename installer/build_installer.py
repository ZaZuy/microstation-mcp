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
    print("BẮT ĐẦU ĐÓNG GÓI VIGELA AI APP & BỘ CÀI ĐẶT")
    print("=" * 60)

    py_exe = sys.executable
    if py_exe.lower().endswith("pythonw.exe"):
        py_exe = py_exe[:-5] + ".exe"

    icon_path = os.path.join(PROJECT_ROOT, "assets", "vigela_icon.ico")
    launcher_py = os.path.join(PROJECT_ROOT, "launcher", "ai_launcher.py")

    # Xóa thư mục build cũ
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    # 1. Đóng gói ứng dụng chính: Vigela_AI_App.exe
    print("\n--- 1/2. Đang đóng gói Vigela_AI_App.exe ---")
    app_cmd = [
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
        launcher_py
    ]
    res_app = subprocess.run(app_cmd, cwd=PROJECT_ROOT)

    # 2. Đóng gói bộ cài đặt: Setup_Vigela_AI.exe
    print("\n--- 2/2. Đang đóng gói bộ cài đặt Setup_Vigela_AI.exe ---")
    setup_cmd = [
        py_exe,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "Setup_Vigela_AI",
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
    res_setup = subprocess.run(setup_cmd, cwd=PROJECT_ROOT)

    if res_app.returncode == 0 or res_setup.returncode == 0:
        print("\n" + "=" * 60)
        print("ĐÓNG GÓI HOÀN TẤT THÀNH CÔNG!")
        if os.path.exists(os.path.join(DIST_DIR, "Vigela_AI_App.exe")):
            print(f"- Ứng dụng chạy trực tiếp: {os.path.join(DIST_DIR, 'Vigela_AI_App.exe')}")
        if os.path.exists(os.path.join(DIST_DIR, "Setup_Vigela_AI.exe")):
            print(f"- Bộ cài đặt 1-Click: {os.path.join(DIST_DIR, 'Setup_Vigela_AI.exe')}")
            # Sao chép thêm tên cũ để đảm bảo tương thích
            shutil.copy2(os.path.join(DIST_DIR, "Setup_Vigela_AI.exe"), os.path.join(DIST_DIR, "Setup_MicroStation_AI.exe"))
        print("=" * 60)
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        return True
    else:
        print("Đóng gói thất bại!")
        return False


if __name__ == "__main__":
    build_exe()
