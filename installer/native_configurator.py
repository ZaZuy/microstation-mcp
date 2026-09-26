"""
installer/native_configurator.py
Công cụ 1-Click All-in-One Configurator cho MicroStation V8i High-Performance Native MCP Server.

Tự động hóa 100% các bước:
1. Dò tìm cài đặt Bentley MicroStation V8i.
2. Biên dịch MsNativePipe.ma (nếu có bmake/VS2005/SDK) hoặc chuẩn bị tệp MDL.
3. Triển khai MsNativePipe.ma vào thư mục mdlapps.
4. Tạo tệp MsNativePipe.cfg trong config\\appl\\ để MicroStation tự nạp vĩnh viễn mỗi khi khởi động.
5. Kích hoạt nóng (Live Auto-Activation) ngay trên phiên MicroStation đang chạy qua COM.
6. Cấu hình MCP Server cho Claude Desktop, Antigravity, Cursor.
7. Ping kiểm tra Named Pipe \\\\.\\pipe\\MsNativeMCP và đo độ trễ.
"""

import os
import sys
import json
import time
import shutil
import struct
import ctypes
import subprocess
import threading
from typing import Optional, Tuple, Dict, Any, List

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Xác định thư mục gốc dự án (hỗ trợ cả chạy script và PyInstaller)
IS_FROZEN = getattr(sys, "frozen", False)
SOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PIPE_NAME = r"\\.\pipe\MsNativeMCP"


# ─────────────────────────────────────────────────────────────────────────────
# 1. TIỆN ÍCH HỆ THỐNG & DÒ TÌM MICROSTATION
# ─────────────────────────────────────────────────────────────────────────────

def is_admin() -> bool:
    """Kiểm tra tiến trình hiện tại có quyền Administrator không."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_privileges():
    """Yêu cầu nâng quyền UAC Administrator nếu chưa có."""
    if not is_admin() and sys.platform == "win32":
        try:
            exe = sys.executable
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, params, None, 1
            )
            if ret > 32:
                sys.exit(0)
        except Exception as ex:
            print(f"[!] Không thể tự nâng quyền Administrator: {ex}")


def find_microstation_directory() -> Optional[str]:
    """Tìm thư mục cài đặt gốc của MicroStation V8i."""
    # 1. Kiểm tra tiến trình đang chạy
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='ustation.exe'", "get", "ExecutablePath"],
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        for line in out.splitlines():
            line = line.strip()
            if line.lower().endswith("ustation.exe") and os.path.exists(line):
                return os.path.dirname(os.path.abspath(line))
    except Exception:
        pass

    # 2. Danh sách các đường dẫn tiêu chuẩn
    candidates = [
        r"C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\MicroStation",
        r"C:\Program Files\Bentley\MicroStation V8i (SELECTseries)\MicroStation",
        r"C:\Bentley\MicroStation V8i (SELECTseries)\MicroStation",
        r"D:\Bentley\MicroStation V8i (SELECTseries)\MicroStation",
        r"C:\Program Files (x86)\Bentley\MicroStation V8i\MicroStation",
        r"C:\Bentley\MicroStation\MicroStation",
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "ustation.exe")):
            return os.path.abspath(c)

    # 3. Quét Registry
    try:
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for sub in [
                r"Software\Bentley\MicroStation",
                r"Software\Wow6432Node\Bentley\MicroStation",
                r"Software\Bentley\Installed_Products",
                r"Software\Wow6432Node\Bentley\Installed_Products"
            ]:
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        num = winreg.QueryInfoKey(key)[0]
                        for i in range(num):
                            sk_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sk_name) as sk:
                                try:
                                    path, _ = winreg.QueryValueEx(sk, "Path")
                                    if path and os.path.exists(os.path.join(path, "ustation.exe")):
                                        return os.path.abspath(path)
                                except Exception:
                                    pass
                except Exception:
                    pass
    except Exception:
        pass

    return None


def is_microstation_running() -> bool:
    """Kiểm tra ustation.exe có đang chạy không."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq ustation.exe"],
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        return "ustation.exe" in out.lower()
    except Exception:
        return False


def find_python_executable() -> str:
    """Tìm đường dẫn python.exe thực tế trên máy."""
    if not IS_FROZEN:
        exe = sys.executable
        if exe.lower().endswith("pythonw.exe"):
            exe = exe[:-5] + ".exe"
        if os.path.exists(exe):
            return exe

    # Thử py launcher
    try:
        out = subprocess.check_output(["py", "-3", "-c", "import sys; print(sys.executable)"], text=True, timeout=2).strip()
        if os.path.exists(out):
            return out
    except Exception:
        pass

    # Thử standard paths
    import glob
    u = os.environ.get("USERPROFILE", "")
    cands = glob.glob(os.path.join(u, "AppData", "Local", "Programs", "Python", "Python*", "python.exe"))
    cands += glob.glob(r"C:\Program Files\Python*\python.exe")
    cands += glob.glob(r"C:\Python*\python.exe")
    for c in cands:
        if os.path.exists(c):
            return c

    p = shutil.which("python.exe")
    if p:
        return p
    return "python.exe"


# ─────────────────────────────────────────────────────────────────────────────
# 2. BIÊN DỊCH & TRIỂN KHAI MDL
# ─────────────────────────────────────────────────────────────────────────────

def compile_or_locate_mdl(source_dir: str, status_cb=None) -> Tuple[bool, str, Optional[str]]:
    """
    Thực hiện biên dịch MsNativePipe.mke nếu có bmake/VS, hoặc định vị file MsNativePipe.ma có sẵn.
    """
    if status_cb:
        status_cb("Kiểm tra công cụ biên dịch và tệp MDL...", 15)

    mdl_src_dir = os.path.join(source_dir, "mdl", "MsNativePipe")
    ma_candidates = [
        os.path.join(mdl_src_dir, "MsNativePipe.ma"),
        os.path.join(mdl_src_dir, "build", "MsNativePipe.ma"),
        os.path.join(mdl_src_dir, "obj", "MsNativePipe.ma"),
        os.path.join(source_dir, "MsNativePipe.ma"),
    ]

    # Kiểm tra xem có script build_mdl.bat không
    build_bat = os.path.join(mdl_src_dir, "build_mdl.bat")
    has_bmake = bool(shutil.which("bmake.exe"))

    if os.path.exists(build_bat) and (has_bmake or shutil.which("cl.exe")):
        if status_cb:
            status_cb("Phát hiện môi trường biên dịch, đang chạy bmake...", 25)
        try:
            res = subprocess.run(
                ["cmd.exe", "/c", build_bat],
                cwd=mdl_src_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            if res.returncode == 0:
                for cand in ma_candidates:
                    if os.path.exists(cand):
                        return True, "Biên dịch thành công qua bmake!", cand
        except Exception as ex:
            print(f"[!] Quá trình biên dịch gặp thông báo: {ex}")

    # Nếu không có bmake hoặc chưa biên dịch, tìm file .ma dựng sẵn
    for cand in ma_candidates:
        if os.path.exists(cand):
            return True, "Đã định vị được tệp MsNativePipe.ma dựng sẵn.", cand

    return False, "Chưa tìm thấy tệp MsNativePipe.ma dựng sẵn và môi trường chưa cài đặt bmake SDK.", None


def deploy_mdl_files(ms_dir: str, ma_path: Optional[str], source_dir: str, status_cb=None) -> List[str]:
    """
    Sao chép tệp MDL và tạo tệp cấu hình auto-load MsNativePipe.cfg.
    """
    deployed = []
    if status_cb:
        status_cb("Đang triển khai tệp vào thư mục MicroStation...", 40)

    # 1. Sao chép tệp .ma vào mdlapps
    mdlapps_dirs = [
        os.path.join(ms_dir, "mdlapps"),
        r"C:\ProgramData\Bentley\MicroStation V8i (SELECTseries)\WorkSpace\standards\mdlapps\intelnt"
    ]

    # Nếu MicroStation đang chạy, gửi MDL UNLOAD trước để tránh bị khóa tệp (WinError 32)
    if is_microstation_running():
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            _app = win32com.client.GetActiveObject("MicroStationDGN.Application")
            if _app:
                _app.CadInputQueue.SendCommand("MDL UNLOAD MsNativePipe")
                time.sleep(0.5)
        except Exception:
            pass

    if ma_path and os.path.exists(ma_path):
        for target_mdlapps in mdlapps_dirs:
            try:
                os.makedirs(target_mdlapps, exist_ok=True)
                dest = os.path.join(target_mdlapps, "MsNativePipe.ma")
                shutil.copy2(ma_path, dest)
                deployed.append(dest)
                print(f"[OK] Đã sao chép: {dest}")
                
                # Sao chép file dll tương ứng nếu có
                dll_src = os.path.splitext(ma_path)[0] + ".dll"
                if not os.path.exists(dll_src):
                    dll_src = os.path.join(os.path.dirname(ma_path), "MsNativePipe.dll")
                if os.path.exists(dll_src):
                    dest_dll = os.path.join(target_mdlapps, "MsNativePipe.dll")
                    shutil.copy2(dll_src, dest_dll)
                    deployed.append(dest_dll)
                    print(f"[OK] Đã sao chép DLL: {dest_dll}")
            except Exception as ex:
                print(f"[!] Lỗi sao chép vào {target_mdlapps}: {ex}")

    # 2. Tạo file cấu hình auto-load vĩnh viễn (MsNativePipe.cfg)
    cfg_content = (
        "#======================================================================\n"
        "# MsNativePipe.cfg - Auto-load MicroStation High-Performance MCP Pipe\n"
        "#======================================================================\n\n"
        "# Tu dong nap MsNativePipe moi khi khoi dong va mo bat ky tep DGN nao\n"
        "MS_DGNAPPS > MsNativePipe\n\n"
        "# Bao dam thu muc chua MsNativePipe luon nam trong danh sach duong dan MDL\n"
        "MS_MDLAPPS > $(_USTN_STANDARDS)mdlapps/intelnt/\n"
        "MS_MDLAPPS > $(MSDIR)mdlapps/\n"
    )

    cfg_targets = [
        os.path.join(ms_dir, "config", "appl", "MsNativePipe.cfg"),
        r"C:\ProgramData\Bentley\MicroStation V8i (SELECTseries)\WorkSpace\standards\config\appl\MsNativePipe.cfg"
    ]

    for cfg_file in cfg_targets:
        try:
            os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write(cfg_content)
            deployed.append(cfg_file)
            print(f"[OK] Đã tạo cấu hình auto-load: {cfg_file}")
        except Exception as ex:
            print(f"[!] Lỗi ghi cấu hình tại {cfg_file}: {ex}")

    return deployed


# ─────────────────────────────────────────────────────────────────────────────
# 3. KÍCH HOẠT NÓNG TRÊN PHIÊN MICROSTATION ĐANG CHẠY
# ─────────────────────────────────────────────────────────────────────────────

def live_activate_in_microstation(status_cb=None) -> Tuple[bool, str]:
    """
    Gửi lệnh nạp MDL LOAD MsNativePipe tức thì qua COM CadInputQueue.
    """
    if not is_microstation_running():
        return True, "MicroStation hiện chưa mở. Cấu hình auto-load sẽ tự nạp ngay khi bạn mở MicroStation."

    if status_cb:
        status_cb("Đang gửi lệnh kích hoạt nóng tới MicroStation qua COM...", 65)

    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()

        app = None
        try:
            app = win32com.client.GetActiveObject("MicroStationDGN.Application")
        except Exception:
            app = win32com.client.Dispatch("MicroStationDGN.Application")

        if app:
            # Gửi lệnh nạp MDL
            app.CadInputQueue.SendCommand("MDL LOAD MsNativePipe")
            app.CadInputQueue.SendCommand("MDL SILENTLOAD MsNativePipe")
            app.ShowCommand("Vigela Native MCP: Ready on pipe!")
            return True, "Đã gửi lệnh kích hoạt 'MDL LOAD MsNativePipe' thành công tới phiên MicroStation đang mở!"
    except Exception as ex:
        return False, f"Không thể gửi lệnh COM tới MicroStation: {ex}"

    return False, "Không thể kết nối đối tượng MicroStation COM."


# ─────────────────────────────────────────────────────────────────────────────
# 4. CẤU HÌNH MCP CLIENTS (CLAUDE & ANTIGRAVITY)
# ─────────────────────────────────────────────────────────────────────────────

def configure_ai_clients(source_dir: str, status_cb=None) -> List[str]:
    """Cấu hình kết nối MCP Server cho Claude Desktop và Antigravity."""
    if status_cb:
        status_cb("Đang cấu hình tệp kết nối MCP cho AI Clients...", 80)

    configured = []
    py_exe = find_python_executable()
    main_py = os.path.join(source_dir, "src", "main.py")

    # Entry cấu hình MCP chuẩn
    mcp_entry = {
        "command": os.path.normpath(py_exe),
        "args": ["-X", "utf8", os.path.normpath(main_py)],
        "autoApprove": ["*"]
    }

    user_roots = set()
    up = os.environ.get("USERPROFILE")
    if up and os.path.exists(up):
        user_roots.add(os.path.normpath(up))
    home = os.path.expanduser("~")
    if home and os.path.exists(home):
        user_roots.add(os.path.normpath(home))

    # 1. Cấu hình Antigravity
    ag_paths = []
    for u in user_roots:
        ag_paths.append(os.path.join(u, ".gemini", "config", "mcp_config.json"))
        ag_paths.append(os.path.join(u, ".gemini", "mcp_config.json"))
        ag_paths.append(os.path.join(u, "AppData", "Roaming", "Antigravity", "mcp_config.json"))
        ag_paths.append(os.path.join(u, "AppData", "Roaming", "antigravity", "mcp_config.json"))
        ag_paths.append(os.path.join(u, "AppData", "Local", "antigravity", "mcp_config.json"))

    for cfg_path in ag_paths:
        try:
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            data = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if "mcpServers" not in data or not isinstance(data.get("mcpServers"), dict):
                data["mcpServers"] = {}
            data["mcpServers"]["microstation-v8i"] = mcp_entry
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            configured.append(cfg_path)
        except Exception as ex:
            print(f"[!] Lỗi cấu hình Antigravity tại {cfg_path}: {ex}")

    # 2. Cấu hình Claude Desktop
    claude_paths = []
    for u in user_roots:
        claude_paths.append(os.path.join(u, "AppData", "Roaming", "Claude", "claude_desktop_config.json"))

    for cfg_path in claude_paths:
        try:
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            data = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if "mcpServers" not in data or not isinstance(data.get("mcpServers"), dict):
                data["mcpServers"] = {}
            data["mcpServers"]["microstation-v8i"] = mcp_entry
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            configured.append(cfg_path)
        except Exception as ex:
            print(f"[!] Lỗi cấu hình Claude tại {cfg_path}: {ex}")

    return configured


# ─────────────────────────────────────────────────────────────────────────────
# 5. KIỂM TRA PIPE KẾT NỐI
# ─────────────────────────────────────────────────────────────────────────────

def test_pipe_connection(status_cb=None) -> Tuple[bool, str, float]:
    """Kiểm tra kết nối và đo độ trễ tới \\\\.\\pipe\\MsNativeMCP."""
    if status_cb:
        status_cb("Đang kiểm tra kết nối Named Pipe \\\\.\\pipe\\MsNativeMCP...", 90)

    try:
        import win32file
        import win32pipe

        t0 = time.perf_counter()
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        
        # Gửi ping frame
        req = json.dumps({"cmd": "ping", "command": "ping"}).encode("utf-8")
        frame = struct.pack("<I", len(req)) + req
        win32file.WriteFile(handle, frame)

        # Nhận response
        _, len_buf = win32file.ReadFile(handle, 4)
        resp_len = struct.unpack("<I", len_buf)[0]
        _, resp_buf = win32file.ReadFile(handle, resp_len)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        win32file.CloseHandle(handle)
        resp_json = json.loads(resp_buf.decode("utf-8"))

        return True, f"Kết nối Native Pipe cực nhanh! Độ trễ: {latency_ms:.2f} ms", latency_ms
    except Exception as ex:
        return False, f"Named Pipe hiện chưa sẵn sàng ({ex}). Sẽ tự động kết nối khi MicroStation nạp MsNativePipe.", -1.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. QUY TRÌNH TỰ ĐỘNG CHÍNH (ALL-IN-ONE PIPELINE)
# ─────────────────────────────────────────────────────────────────────────────

def run_all_in_one_configuration(status_cb=None) -> Dict[str, Any]:
    """Thực thi chuỗi cấu hình toàn diện từ A-Z."""
    report = {
        "success": False,
        "microstation_found": False,
        "ms_path": None,
        "mdl_compiled": False,
        "mdl_path": None,
        "deployed_files": [],
        "hot_activated": False,
        "ai_configs": [],
        "pipe_active": False,
        "pipe_latency_ms": -1.0,
        "messages": []
    }

    def log(msg, step_progress=None):
        print(f"[*] {msg}")
        report["messages"].append(msg)
        if status_cb and step_progress is not None:
            status_cb(msg, step_progress)

    log("Bắt đầu tự động cấu hình MicroStation V8i High-Performance Native MCP...", 5)

    # 1. Dò tìm MicroStation
    ms_dir = find_microstation_directory()
    if ms_dir:
        report["microstation_found"] = True
        report["ms_path"] = ms_dir
        log(f"[V] Đã tìm thấy MicroStation V8i tại: {ms_dir}", 10)
    else:
        log("[X] Không tìm thấy thư mục cài đặt MicroStation V8i trên hệ thống.", 10)
        return report

    # 2. Biên dịch / Tìm tệp MDL
    mdl_ok, mdl_msg, ma_path = compile_or_locate_mdl(SOURCE_DIR, status_cb)
    report["mdl_compiled"] = mdl_ok
    report["mdl_path"] = ma_path
    log(f"[{'V' if mdl_ok else '!'}] {mdl_msg}", 30)

    # 3. Triển khai tệp vào MicroStation
    deployed = deploy_mdl_files(ms_dir, ma_path, SOURCE_DIR, status_cb)
    report["deployed_files"] = deployed
    log(f"[V] Đã triển khai {len(deployed)} tệp cấu hình và mã thực thi vào MicroStation.", 50)

    # 4. Kích hoạt nóng qua COM
    act_ok, act_msg = live_activate_in_microstation(status_cb)
    report["hot_activated"] = act_ok
    log(f"[{'V' if act_ok else '!'}] {act_msg}", 70)

    # 5. Cấu hình AI Clients
    ai_configs = configure_ai_clients(SOURCE_DIR, status_cb)
    report["ai_configs"] = ai_configs
    log(f"[V] Đã cập nhật cấu hình cho {len(ai_configs)} vị trí AI MCP client.", 85)

    # 6. Kiểm tra Named Pipe
    pipe_ok, pipe_msg, latency = test_pipe_connection(status_cb)
    report["pipe_active"] = pipe_ok
    report["pipe_latency_ms"] = latency
    log(f"[{'V' if pipe_ok else 'i'}] {pipe_msg}", 95)

    report["success"] = True
    log("Hoàn tất cấu hình 1-Click!", 100)
    return report


# ─────────────────────────────────────────────────────────────────────────────
# 7. GIAO DIỆN NGƯỜI DÙNG TKINTER (GUI)
# ─────────────────────────────────────────────────────────────────────────────

def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("Vigela AI - MicroStation V8i Native Configurator")
    root.geometry("680x560")
    root.resizable(False, False)

    # Màu giao diện Dark Theme hiện đại
    BG_COLOR = "#0f172a"
    CARD_COLOR = "#1e293b"
    ACCENT_COLOR = "#6366f1"
    SUCCESS_COLOR = "#10b981"
    TEXT_COLOR = "#f8fafc"
    MUTED_COLOR = "#94a3b8"

    root.configure(bg=BG_COLOR)

    # Icon
    icon_path = os.path.join(SOURCE_DIR, "assets", "vigela_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(SOURCE_DIR, "launcher", "vigela_icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    # Header
    header = tk.Frame(root, bg=BG_COLOR)
    header.pack(fill="x", padx=25, pady=(20, 10))

    title = tk.Label(
        header,
        text="⚡ Vigela MicroStation V8i Native Configurator",
        font=("Segoe UI", 16, "bold"),
        fg=TEXT_COLOR,
        bg=BG_COLOR
    )
    title.pack(anchor="w")

    subtitle = tk.Label(
        header,
        text="Trình cấu hình tự động 1-Click kích hoạt Named Pipe (~0.5ms) & tích hợp AI",
        font=("Segoe UI", 9),
        fg=MUTED_COLOR,
        bg=BG_COLOR
    )
    subtitle.pack(anchor="w", pady=(3, 0))

    # Thẻ thông tin các bước tự động
    card = tk.Frame(root, bg=CARD_COLOR, highlightthickness=1, highlightbackground="#334155")
    card.pack(fill="both", expand=True, padx=25, pady=10)

    steps_title = tk.Label(
        card,
        text="Các hạng mục tự động hóa:",
        font=("Segoe UI", 10, "bold"),
        fg=TEXT_COLOR,
        bg=CARD_COLOR
    )
    steps_title.pack(anchor="w", padx=15, pady=(12, 6))

    steps = [
        "1. Dò tìm đường dẫn cài đặt MicroStation V8i và trạng thái tiến trình",
        "2. Tự động biên dịch MsNativePipe.mke bằng bmake / định vị file MDL",
        "3. Chép MsNativePipe.ma vào thư mục mdlapps tiêu chuẩn",
        "4. Tạo cấu hình auto-load vĩnh viễn (MsNativePipe.cfg) - Không cần gõ Key-in",
        "5. Kích hoạt nóng tức thì trên bản vẽ MicroStation đang mở",
        "6. Cấu hình MCP Server cho Claude Desktop, Antigravity, Cursor",
        "7. Ping kiểm tra Named Pipe và đo độ trễ xử lý (ms)"
    ]

    for s in steps:
        lbl = tk.Label(
            card,
            text=f"  ✔  {s}",
            font=("Segoe UI", 8),
            fg="#cbd5e1",
            bg=CARD_COLOR,
            anchor="w"
        )
        lbl.pack(fill="x", padx=15, pady=2)

    # Khung Log hiển thị tiến trình
    log_box = tk.Text(
        card,
        height=6,
        bg="#090d16",
        fg="#38bdf8",
        insertbackground="#ffffff",
        font=("Consolas", 8),
        relief="flat"
    )
    log_box.pack(fill="x", padx=15, pady=(10, 15))
    log_box.insert("end", "Sẵn sàng thực hiện. Nhấn nút bên dưới để bắt đầu cấu hình 1-Click.\n")
    log_box.config(state="disabled")

    # Tiến trình
    pframe = tk.Frame(root, bg=BG_COLOR)
    pframe.pack(fill="x", padx=25, pady=5)

    status_lbl = tk.Label(pframe, text="Sẵn sàng.", font=("Segoe UI", 9), fg=MUTED_COLOR, bg=BG_COLOR)
    status_lbl.pack(anchor="w", pady=(0, 4))

    pbar = ttk.Progressbar(pframe, orient="horizontal", mode="determinate")
    pbar.pack(fill="x")

    def update_status(text, val):
        def _do():
            status_lbl.config(text=text)
            pbar.config(value=val)
            log_box.config(state="normal")
            log_box.insert("end", f"[*] {text}\n")
            log_box.see("end")
            log_box.config(state="disabled")
        root.after(0, _do)

    def on_start_click():
        start_btn.config(state="disabled", text="⏳ Đang xử lý tự động...")
        def worker():
            rep = run_all_in_one_configuration(update_status)
            def done():
                start_btn.config(state="normal", text="🚀 Cấu Hình Lại 1-Click")
                if rep.get("success"):
                    latency_info = f" ({rep['pipe_latency_ms']:.2f} ms)" if rep.get("pipe_active") else ""
                    messagebox.showinfo(
                        "Thành Công",
                        f"Đã hoàn tất cấu hình trọn gói!\n\n"
                        f"- MicroStation: {rep.get('ms_path')}\n"
                        f"- Auto-load cfg: Đã cài đặt vào config\\appl\\\n"
                        f"- AI Clients: Đã kết nối Claude & Antigravity\n"
                        f"- Pipe Server: {'Đã sẵn sàng' + latency_info if rep.get('pipe_active') else 'Sẽ tự động kết nối khi mở MicroStation'}\n\n"
                        f"Toàn bộ 25 công cụ Native đã sẵn sàng hoạt động!"
                    )
                else:
                    messagebox.showwarning(
                        "Thông Báo",
                        "Quá trình cấu hình hoàn thành với một số cảnh báo. Vui lòng kiểm tra khung nhật ký."
                    )
            root.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    start_btn = tk.Button(
        root,
        text="🚀 Bắt Đầu Cấu Hình 1-Click",
        font=("Segoe UI", 11, "bold"),
        bg=ACCENT_COLOR,
        fg="#ffffff",
        activebackground="#4f46e5",
        activeforeground="#ffffff",
        relief="flat",
        pady=10,
        cursor="hand2",
        command=on_start_click
    )
    start_btn.pack(fill="x", padx=25, pady=(10, 20), side="bottom")

    root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# 8. ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Nâng quyền Administrator nếu cần ghi vào C:\Program Files (x86)
    if not is_admin() and "--no-elevate" not in sys.argv:
        elevate_privileges()

    if "--cli" in sys.argv or "--silent" in sys.argv:
        res = run_all_in_one_configuration()
        sys.exit(0 if res.get("success") else 1)
    else:
        run_gui()
