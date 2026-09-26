"""
installer/build_configurator.py
Script đóng gói công cụ 1-Click Vigela_AutoConfig.exe bằng PyInstaller.
Tạo ra tệp thực thi độc lập duy nhất với quyền Administrator (UAC Admin)
để người dùng chỉ cần click 1 lần là tự cấu hình và kích hoạt MicroStation V8i Native MCP.
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
CONFIGURATOR_PY = os.path.join(INSTALLER_DIR, "native_configurator.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_configurator_temp")
OUTPUT_EXE_NAME = "Vigela_AutoConfig"


def build_configurator_exe():
    print("=" * 65)
    print("  ĐÓNG GÓI 1-CLICK ALL-IN-ONE CONFIGURATOR (Vigela_AutoConfig.exe)")
    print("=" * 65)

    py_candidates = [
        r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\python.exe",
        sys.executable,
    ]
    py_exe = None
    for cand in py_candidates:
        if os.path.exists(cand):
            try:
                res = subprocess.run([cand, "-c", "import PyInstaller; print(PyInstaller.__version__)"], capture_output=True, text=True)
                if res.returncode == 0:
                    py_exe = cand
                    print(f"[*] Sử dụng Python: {py_exe} (PyInstaller {res.stdout.strip()})")
                    break
            except Exception:
                pass

    if not py_exe:
        print("[!] Không tìm thấy Python có cài đặt PyInstaller!")
        return False

    icon_path = os.path.join(PROJECT_ROOT, "assets", "vigela_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(PROJECT_ROOT, "launcher", "vigela_icon.ico")

    # Dọn dẹp build temp cũ
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    cmd = [
        py_exe, "-m", "PyInstaller",
        "--onefile",
        "--name", OUTPUT_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'mdl')};mdl",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'assets')};assets",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'launcher')};launcher",
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tcl8.6;_tcl_data",
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tk8.6;_tk_data",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32file",
        "--hidden-import", "win32pipe",
        "--hidden-import", "pythoncom",
        "--hidden-import", "pywintypes",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.messagebox",
        CONFIGURATOR_PY
    ]

    print("\n[*] Đang chạy PyInstaller...")
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        print("[X] Đóng gói thất bại!")
        return False

    out_exe = os.path.join(DIST_DIR, f"{OUTPUT_EXE_NAME}.exe")
    if os.path.exists(out_exe):
        size_mb = os.path.getsize(out_exe) / (1024 * 1024)
        print("\n" + "=" * 65)
        print(f"  [THANH CONG] File thực thi: {out_exe}")
        print(f"  Kích thước: {size_mb:.2f} MB")
        print("  Tính năng: 1-Click Run As Admin, Auto-Load, Live Key-in, MCP Config")
        print("=" * 65)
        return True
    return False


if __name__ == "__main__":
    success = build_configurator_exe()
    sys.exit(0 if success else 1)
