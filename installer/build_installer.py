"""
installer/build_installer.py
Đóng gói thành 1 file cài đặt duy nhất: Vigela_AI_App.exe
Bên trong nhúng sẵn:
  - Vigela_AI_Launcher.exe  (GUI launcher, standalone, không có cửa sổ đen)
  - Vigela_MCP_Server.exe   (MCP server console độc lập cho Claude/Antigravity)
Người dùng tải về 1 file duy nhất, mang sang bất kỳ máy tính nào cũng hoạt động 100% không cần Python!
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
SETUP_GUI = os.path.join(INSTALLER_DIR, "setup_gui.py")
LAUNCHER_PY = os.path.join(PROJECT_ROOT, "launcher", "ai_launcher.py")
MCP_SERVER_PY = os.path.join(PROJECT_ROOT, "src", "main.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_temp")
LAUNCHER_EXE_NAME = "Vigela_AI_Launcher"
MCP_SERVER_EXE_NAME = "Vigela_MCP_Server"
INSTALLER_EXE_NAME = "Vigela_AI_App"


def build_exe():
    print("=" * 60)
    print("BẮT ĐẦU ĐÓNG GÓI VIGELA AI APP TRỌN GÓI (STANDALONE 100%)")
    print("=" * 60)

    # Ưu tiên Python có đầy đủ Tkinter
    candidate_pythons = [
        r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\python.exe",
        sys.executable,
    ]
    py_exe = None
    for cand in candidate_pythons:
        if os.path.exists(cand):
            try:
                res = subprocess.run([cand, "-c", "import tkinter; print(tkinter.TkVersion)"], capture_output=True, text=True)
                if res.returncode == 0:
                    py_exe = cand
                    break
            except Exception:
                pass
    if not py_exe:
        py_exe = sys.executable
        if py_exe.lower().endswith("pythonw.exe"):
            py_exe = py_exe[:-5] + ".exe"

    print(f"Python thực thi: {py_exe}")
    icon_path = os.path.join(PROJECT_ROOT, "assets", "vigela_icon.ico")

    # Xóa sạch thư mục build & dist cũ
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    # =========================================================================
    # BƯỚC 1: Đóng gói Standalone GUI Launcher (Vigela_AI_Launcher.exe)
    # =========================================================================
    print("\n[1/3] Đang đóng gói Vigela_AI_Launcher.exe (GUI, không hiện terminal)...")
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
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'launcher')};launcher",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'assets')};assets",
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tcl8.6;_tcl_data",
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tk8.6;_tk_data",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32api",
        "--hidden-import", "pythoncom",
        "--hidden-import", "pywintypes",
        "--hidden-import", "winreg",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageTk",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        LAUNCHER_PY
    ]
    res1 = subprocess.run(launcher_cmd, cwd=PROJECT_ROOT)
    if res1.returncode != 0:
        print("Lỗi: Không thể đóng gói Vigela_AI_Launcher.exe!")
        return False
    launcher_exe = os.path.join(DIST_DIR, f"{LAUNCHER_EXE_NAME}.exe")
    print(f"    => Đã tạo: {launcher_exe} ({os.path.getsize(launcher_exe)//1024//1024} MB)")

    # =========================================================================
    # BƯỚC 2: Đóng gói Standalone MCP Server (Vigela_MCP_Server.exe)
    # =========================================================================
    print("\n[2/3] Đang đóng gói Vigela_MCP_Server.exe (MCP Console Server, 62 công cụ CAD)...")
    mcp_cmd = [
        py_exe, "-m", "PyInstaller",
        "--onefile",  # Chế độ console để giao tiếp stdio với Claude Desktop & Antigravity
        "--name", MCP_SERVER_EXE_NAME,
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", BUILD_DIR,
        "--clean",
        "--icon", icon_path,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')};src",
        "--hidden-import", "fastmcp",
        "--hidden-import", "mcp",
        "--hidden-import", "anyio",
        "--hidden-import", "anyio.abc",
        "--hidden-import", "anyio._backends._asyncio",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32api",
        "--hidden-import", "pythoncom",
        "--hidden-import", "pywintypes",
        "--hidden-import", "winreg",
        "--hidden-import", "PIL",
        "--collect-all", "fastmcp",
        "--collect-all", "mcp",
        "--collect-all", "anyio",
        "--collect-all", "pydantic",
        "--collect-all", "starlette",
        "--collect-all", "uvicorn",
        "--collect-all", "PIL",
        MCP_SERVER_PY
    ]
    res2 = subprocess.run(mcp_cmd, cwd=PROJECT_ROOT)
    if res2.returncode != 0:
        print("Lỗi: Không thể đóng gói Vigela_MCP_Server.exe!")
        return False
    mcp_exe = os.path.join(DIST_DIR, f"{MCP_SERVER_EXE_NAME}.exe")
    print(f"    => Đã tạo: {mcp_exe} ({os.path.getsize(mcp_exe)//1024//1024} MB)")

    # =========================================================================
    # BƯỚC 3: Đóng gói Bộ cài đặt duy nhất (Vigela_AI_App.exe) nhúng cả 2 file trên
    # =========================================================================
    print("\n[3/3] Đang đóng gói Bộ cài đặt tổng hợp: Vigela_AI_App.exe...")
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
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tcl8.6;_tcl_data",
        "--add-data", r"C:\Users\SERVER\AppData\Local\Programs\Python\Python314\tcl\tk8.6;_tk_data",
        # Nhúng cả 2 file exe vào bên trong bộ cài duy nhất
        "--add-data", f"{launcher_exe};.",
        "--add-data", f"{mcp_exe};.",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "win32api",
        "--hidden-import", "pythoncom",
        "--hidden-import", "pywintypes",
        "--hidden-import", "winreg",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.messagebox",
        "--hidden-import", "tkinter.filedialog",
        SETUP_GUI
    ]
    res3 = subprocess.run(installer_cmd, cwd=PROJECT_ROOT)
    if res3.returncode != 0:
        print("Lỗi: Không thể đóng gói bộ cài đặt Vigela_AI_App.exe!")
        return False

    # Sao chép trực tiếp file Vigela_MCP_Server.exe vào thư mục cài đặt hiện tại nếu có
    install_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "MicroStation-AI-CAD")
    if os.path.exists(install_dir) and os.path.exists(mcp_exe):
        try:
            target_mcp = os.path.join(install_dir, f"{MCP_SERVER_EXE_NAME}.exe")
            shutil.copy2(mcp_exe, target_mcp)
            print(f"    => Đã cập nhật trực tiếp vào thư mục cài đặt: {target_mcp}")
        except Exception as e:
            print(f"    (Không thể cập nhật vào thư mục cài đặt: {e})")

    installer_path = os.path.join(DIST_DIR, f"{INSTALLER_EXE_NAME}.exe")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    desktop_candidates = [
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    ]
    for d in desktop_candidates:
        if os.path.exists(d):
            try:
                dst = os.path.join(d, f"{INSTALLER_EXE_NAME}.exe")
                shutil.copy2(installer_path, dst)
                print(f"    => Đã sao chép ra màn hình Desktop: {dst}")
                break
            except Exception as e:
                print(f"    (Không thể copy ra Desktop: {e})")

    print("\n" + "=" * 60)
    print("ĐÓNG GÓI HOÀN TẤT THÀNH CÔNG!")
    print(f"File cài đặt duy nhất: {installer_path}")
    print(f"Kích thước: {os.path.getsize(installer_path)//1024//1024} MB")
    print("=" * 60)
    print("Ưu điểm khi mang sang máy khác:")
    print("  ✓ Không cần cài Python hay bất kỳ thư viện nào.")
    print("  ✓ Tự động trích xuất Vigela_AI_Launcher.exe (mở trực tiếp không màn hình đen).")
    print("  ✓ Tự động trích xuất Vigela_MCP_Server.exe (kết nối stdio chuẩn cho AI Agent).")
    print("  ✓ Tự động cấu hình MCP vào Claude Desktop & Google Antigravity.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    build_exe()

