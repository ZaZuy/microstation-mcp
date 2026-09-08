"""
ai_launcher.py
Trình khởi chạy thông minh (AI App Launcher) cho MicroStation V8i.
Tích hợp:
- Quét và nhận diện các App AI trên máy tính.
- Tự động đồng bộ cấu hình MCP Server cho Claude Desktop & Antigravity.
- Theo dõi trạng thái tiến trình ĐANG CHẠY theo thời gian thực.
- Nút Tắt Hẳn (Kill Process) cho các tiến trình chạy ngầm.
- Tự động phát hiện Cập Nhật (Auto-Update) từ GitHub và cập nhật 1-click.
"""

import os
import sys
import csv
import io
import json
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox

# Đường dẫn dự án và cài đặt
if getattr(sys, "frozen", False):
    INSTALL_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, "_MEIPASS", INSTALL_DIR)
    LAUNCHER_DIR = os.path.join(INSTALL_DIR, "launcher")
    PROJECT_ROOT = INSTALL_DIR
else:
    LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(LAUNCHER_DIR)
    INSTALL_DIR = PROJECT_ROOT
    BUNDLE_DIR = PROJECT_ROOT


def find_python_executable():
    """Tìm python.exe thực sự của hệ thống trên máy."""
    if not getattr(sys, "frozen", False):
        exe = sys.executable
        if exe.lower().endswith("pythonw.exe"):
            exe = exe[:-5] + ".exe"
        if os.path.exists(exe) and "vigela" not in os.path.basename(exe).lower() and "setup" not in os.path.basename(exe).lower():
            return exe

    try:
        out = subprocess.check_output(["py", "-3", "-c", "import sys; print(sys.executable)"], text=True, timeout=3).strip()
        if os.path.exists(out) and "windowsapps" not in out.lower():
            return out
    except Exception:
        pass

    try:
        import winreg
        for hive in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(hive, r"Software\Python\PythonCore") as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        ver_name = winreg.EnumKey(root_key, i)
                        try:
                            with winreg.OpenKey(root_key, rf"{ver_name}\InstallPath") as p_key:
                                path_val, _ = winreg.QueryValueEx(p_key, "ExecutablePath")
                                if os.path.exists(path_val) and "windowsapps" not in path_val.lower():
                                    return path_val
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    import glob
    user_prof = os.environ.get("USERPROFILE", "")
    candidates = glob.glob(os.path.join(user_prof, "AppData", "Local", "Programs", "Python", "Python*", "python.exe"))
    candidates += glob.glob(r"C:\Program Files\Python*\python.exe")
    candidates += glob.glob(r"C:\Python*\python.exe")
    for c in candidates:
        if os.path.exists(c):
            return c

    try:
        import shutil
        p = shutil.which("python.exe")
        if p and "windowsapps" not in p.lower() and os.path.getsize(p) > 0:
            return p
        out = subprocess.check_output(["where", "python"], text=True).strip().splitlines()
        for item in out:
            if "windowsapps" not in item.lower() and os.path.exists(item) and os.path.getsize(item) > 0:
                return item
    except Exception:
        pass

    return "python.exe"


PYTHON_EXE = find_python_executable()

# Import module updater
sys.path.insert(0, LAUNCHER_DIR)
try:
    from updater import get_local_config, check_for_updates, perform_update
except ImportError:
    get_local_config = lambda: {"version": "1.0.0"}
    check_for_updates = lambda: (False, "1.0.0", "", "none")
    perform_update = lambda: (False, "Không tìm thấy updater")


def get_mcp_server_entry():
    """Xác định command và args chính xác cho MCP server, không bao giờ dùng thư mục Temp."""
    # 1. Tìm file Vigela_MCP_Server.exe
    mcp_exe_candidates = [
        os.path.join(INSTALL_DIR, "Vigela_MCP_Server.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MicroStation-AI-CAD\Vigela_MCP_Server.exe"),
        os.path.join(PROJECT_ROOT, "dist", "Vigela_MCP_Server.exe"),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "Vigela_MCP_Server.exe"),
    ]
    for cand in mcp_exe_candidates:
        if os.path.exists(cand):
            return {
                "command": cand,
                "args": [],
            }

    # 2. Fallback: dùng python + src/main.py trong INSTALL_DIR hoặc PROJECT_ROOT
    main_py_candidates = [
        os.path.join(INSTALL_DIR, "src", "main.py"),
        os.path.join(PROJECT_ROOT, "src", "main.py"),
    ]
    main_py = None
    for cand in main_py_candidates:
        if os.path.exists(cand):
            main_py = cand
            break
    if not main_py:
        main_py = main_py_candidates[0]

    return {
        "command": PYTHON_EXE,
        "args": ["-X", "utf8", main_py],
    }


def ensure_mcp_configs():
    """Tự động đồng bộ cấu hình MCP MicroStation cho các App AI."""
    mcp_entry = get_mcp_server_entry()

    # 1. Antigravity config
    gemini_config_dir = os.path.expanduser(r"~/.gemini/config")
    gemini_config_file = os.path.join(gemini_config_dir, "mcp_config.json")
    try:
        os.makedirs(gemini_config_dir, exist_ok=True)
        data = {}
        if os.path.exists(gemini_config_file):
            with open(gemini_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"]["microstation-v8i"] = mcp_entry
        with open(gemini_config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi cấu hình Antigravity: {e}", file=sys.stderr)

    # 2. Claude Desktop config
    claude_config_dir = os.path.expandvars(r"%APPDATA%\Claude")
    claude_config_file = os.path.join(claude_config_dir, "claude_desktop_config.json")
    try:
        os.makedirs(claude_config_dir, exist_ok=True)
        data = {}
        if os.path.exists(claude_config_file):
            with open(claude_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"]["microstation-v8i"] = mcp_entry
        with open(claude_config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi cấu hình Claude Desktop: {e}", file=sys.stderr)


def get_running_process_names():
    """Lấy danh sách tên tất cả các tiến trình đang chạy trên Windows."""
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        reader = csv.reader(io.StringIO(out))
        return {row[0].lower() for row in reader if row}
    except Exception:
        return set()


def kill_app_process(process_name):
    """Tắt hoàn toàn các tiến trình chạy ngầm của ứng dụng."""
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            ["taskkill", "/F", "/IM", process_name],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            check=False
        )
    except Exception:
        pass


def detect_installed_apps():
    """Quét và nhận diện các ứng dụng AI cũng như MicroStation trên máy."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    apps = [
        {
            "id": "claude",
            "name": "Claude Desktop",
            "desc": "Ứng dụng máy tính chính thức của Anthropic (Claude 3.5 Sonnet)",
            "icon": "🤖",
            "process_name": "claude.exe",
            "paths": [
                os.path.join(local_app, "Programs", "Claude", "Claude.exe"),
                os.path.join(local_app, "Claude", "Claude.exe"),
            ],
            "appx_pkg": "Claude_pzs8sxrjxfjjc",
            "appx_id": "Claude_pzs8sxrjxfjjc!Claude",
            "download_url": "https://claude.ai/download",
        },
        {
            "id": "antigravity",
            "name": "Google Antigravity IDE",
            "desc": "Môi trường phát triển AI chuyên sâu (Gemini 2.0 / Pro)",
            "icon": "⚡",
            "process_name": "antigravity.exe",
            "paths": [
                os.path.join(local_app, "Programs", "antigravity", "Antigravity.exe"),
            ],
            "download_url": "https://antigravity.google/",
        },
        {
            "id": "vscode",
            "name": "Visual Studio Code (Cline / Roo Code)",
            "desc": "VS Code với các extension AI điều khiển MCP",
            "icon": "💻",
            "process_name": "code.exe",
            "paths": [
                os.path.join(local_app, "Programs", "Microsoft VS Code", "Code.exe"),
                os.path.join(prog_files, "Microsoft VS Code", "Code.exe"),
            ],
            "download_url": "https://code.visualstudio.com/",
        },
        {
            "id": "cursor",
            "name": "Cursor AI IDE",
            "desc": "Trình soạn thảo mã tích hợp AI hỗ trợ chuẩn MCP",
            "icon": "✨",
            "process_name": "cursor.exe",
            "paths": [
                os.path.join(local_app, "Programs", "cursor", "Cursor.exe"),
            ],
            "download_url": "https://cursor.com/",
        },
        {
            "id": "chatgpt",
            "name": "ChatGPT Desktop",
            "desc": "Ứng dụng máy tính chính thức của OpenAI (GPT-4o)",
            "icon": "🧠",
            "process_name": "chatgpt.exe",
            "paths": [
                os.path.join(local_app, "Programs", "ChatGPT", "ChatGPT.exe"),
            ],
            "download_url": "https://openai.com/chatgpt/desktop/",
        },
        {
            "id": "ustation",
            "name": "Bentley MicroStation V8i",
            "desc": "Phần mềm CAD hạt nhân (SELECTseries)",
            "icon": "📐",
            "process_name": "ustation.exe",
            "paths": [
                os.path.join(prog_files_x86, "Bentley", "MicroStation V8i (SELECTseries)", "MicroStation", "ustation.exe"),
                os.path.join(prog_files, "Bentley", "MicroStation V8i", "MicroStation", "ustation.exe"),
            ],
            "download_url": "https://www.bentley.com/",
        }
    ]

    running_procs = get_running_process_names()

    for app in apps:
        app["installed"] = False
        app["exe_path"] = None
        app["launch_type"] = "exe"
        app["launch_target"] = None
        app["is_running"] = app.get("process_name", "").lower() in running_procs

        # 1. Kiểm tra theo đường dẫn exe truyền thống
        for p in app.get("paths", []):
            if os.path.exists(p):
                app["installed"] = True
                app["exe_path"] = p
                app["launch_target"] = p
                break

        # 2. Kiểm tra WindowsApps / Appx Package
        if not app["installed"] and app.get("appx_pkg"):
            pkg_path = os.path.join(local_app, "Packages", app["appx_pkg"])
            if os.path.exists(pkg_path):
                app["installed"] = True
                app["launch_type"] = "appx"
                app["launch_target"] = app.get("appx_id", "")

        # 3. Nếu đang có tiến trình chạy thì chắc chắn đã cài đặt
        if app["is_running"]:
            app["installed"] = True

    return apps


def launch_app(app_info):
    """Khởi chạy hoặc chuyển tới ứng dụng."""
    if not app_info or not app_info.get("installed"):
        return False
    try:
        launch_type = app_info.get("launch_type", "exe")
        target = app_info.get("launch_target")

        if launch_type == "appx" and target:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{target}"], shell=False)
            return True
        elif target and os.path.exists(target):
            subprocess.Popen([target], shell=False)
            return True
        elif app_info.get("id") == "claude":
            subprocess.Popen(["explorer.exe", "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude"], shell=False)
            return True
        return False
    except Exception as e:
        messagebox.showerror("Lỗi khởi chạy", f"Không thể mở ứng dụng:\n{e}")
        return False


class LauncherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vigela AI App")
        self.root.geometry("700x720")
        self.root.resizable(False, False)

        # Gán icon Vigela cho cửa sổ
        icon_ico = os.path.join(LAUNCHER_DIR, "vigela_icon.ico")
        if not os.path.exists(icon_ico):
            icon_ico = os.path.join(PROJECT_ROOT, "assets", "vigela_icon.ico")
        if os.path.exists(icon_ico):
            try:
                self.root.iconbitmap(icon_ico)
            except Exception:
                pass

        icon_png = os.path.join(LAUNCHER_DIR, "vigela_icon.png")
        if not os.path.exists(icon_png):
            icon_png = os.path.join(PROJECT_ROOT, "assets", "vigela_logo.png")
        if os.path.exists(icon_png):
            try:
                self.app_icon = tk.PhotoImage(file=icon_png)
                self.root.iconphoto(False, self.app_icon)
            except Exception:
                pass

        # Bảng màu Dark Mode hiện đại
        self.bg_color = "#181825"
        self.card_color = "#242438"
        self.accent_color = "#6366f1"
        self.text_color = "#ffffff"
        self.text_muted = "#94a3b8"
        self.success_color = "#10b981"
        self.running_color = "#22c55e"
        self.warning_color = "#f59e0b"
        self.danger_color = "#ef4444"

        self.root.configure(bg=self.bg_color)

        # Ép cửa sổ luôn bật lên hàng đầu (Foreground) khi mở thay vì bị ẩn dưới taskbar
        self.force_bring_to_front()
        self.root.after(100, self.force_bring_to_front)
        self.root.after(400, self.force_bring_to_front)

        # Đọc cấu hình phiên bản
        self.version_cfg = get_local_config()
        self.current_version = self.version_cfg.get("version", "1.0.0")

        # Tự động đồng bộ MCP config
        ensure_mcp_configs()
        self.apps = detect_installed_apps()

        # Lưu trữ các widget
        self.app_widgets = {}
        self.update_banner = None
        self.update_info = None

        self.build_ui()

        # Giám sát tiến trình thời gian thực
        self.root.after(1000, self.periodic_check)

        # Chạy kiểm tra cập nhật trong luồng nền
        threading.Thread(target=self.bg_check_updates, daemon=True).start()

    def force_bring_to_front(self):
        """Bật cửa sổ lên trên cùng (Foreground) và kích hoạt tiêu điểm ngay khi mở."""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            # Nhả thuộc tính topmost sau 400ms để người dùng vẫn thao tác app khác bình thường
            self.root.after(400, lambda: self.root.attributes("-topmost", False))

            if sys.platform == "win32":
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def build_ui(self):
        # Header Frame
        header = tk.Frame(self.root, bg=self.bg_color)
        header.pack(fill="x", padx=25, pady=(16, 6))

        # Tiêu đề + Phiên bản
        title_box = tk.Frame(header, bg=self.bg_color)
        title_box.pack(side="left", fill="both", expand=True)

        title_row = tk.Frame(title_box, bg=self.bg_color)
        title_row.pack(anchor="w")

        # Logo Vigela trên Header
        logo_png = os.path.join(LAUNCHER_DIR, "vigela_icon.png")
        if not os.path.exists(logo_png):
            logo_png = os.path.join(PROJECT_ROOT, "assets", "vigela_logo.png")
        if os.path.exists(logo_png):
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_png).resize((32, 32), Image.Resampling.LANCZOS)
                self.header_logo = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(title_row, image=self.header_logo, bg=self.bg_color)
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title = tk.Label(
            title_row,
            text="Vigela AI App",
            font=("Segoe UI", 18, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        title.pack(side="left")

        ver_lbl = tk.Label(
            title_row,
            text=f"v{self.current_version}",
            font=("Segoe UI", 9, "bold"),
            fg="#818cf8",
            bg="#312e81",
            padx=8,
            pady=2
        )
        ver_lbl.pack(side="left", padx=(10, 0))

        subtitle = tk.Label(
            title_box,
            text="Bộ điều khiển thông minh kết nối AI & MicroStation V8i CAD",
            font=("Segoe UI", 9),
            fg=self.text_muted,
            bg=self.bg_color
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # Nút kiểm tra cập nhật thủ công
        self.check_btn = tk.Button(
            header,
            text="🔄 Kiểm Tra Cập Nhật",
            font=("Segoe UI", 8, "bold"),
            bg="#2e2e48",
            fg="#c7d2fe",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.manual_check_update
        )
        self.check_btn.pack(side="right", pady=5)

        # Banner Cập Nhật (ẩn mặc định, hiện khi có bản mới)
        self.update_banner = tk.Frame(self.root, bg="#1e1b4b", highlightthickness=1, highlightbackground="#6366f1")

        # Khối MicroStation
        mstn = next((a for a in self.apps if a["id"] == "ustation"), None)
        mstn_card = tk.Frame(self.root, bg=self.card_color, highlightthickness=1, highlightbackground="#374151")
        mstn_card.pack(fill="x", padx=25, pady=(4, 10))

        m_icon = tk.Label(mstn_card, text="📐", font=("Segoe UI Emoji", 18), bg=self.card_color)
        m_icon.pack(side="left", padx=(15, 10), pady=10)

        m_info = tk.Frame(mstn_card, bg=self.card_color)
        m_info.pack(side="left", fill="both", expand=True, pady=10)

        m_title = tk.Label(m_info, text="Bentley MicroStation V8i (CAD Engine)", font=("Segoe UI", 11, "bold"), fg=self.text_color, bg=self.card_color)
        m_title.pack(anchor="w")

        self.mstn_status_lbl = tk.Label(m_info, text="", font=("Segoe UI", 9, "bold"), bg=self.card_color)
        self.mstn_status_lbl.pack(anchor="w")

        m_btn_container = tk.Frame(mstn_card, bg=self.card_color)
        m_btn_container.pack(side="right", padx=12, pady=8)

        self.mstn_btn = tk.Button(
            m_btn_container,
            text="Mở MicroStation",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: launch_app(mstn)
        )
        self.mstn_btn.pack(side="left", padx=2)

        self.mstn_kill_btn = tk.Button(
            m_btn_container,
            text="✖ Tắt",
            font=("Segoe UI", 8, "bold"),
            bg="#3f1d24",
            fg="#f87171",
            activebackground="#7f1d1d",
            activeforeground="#ffffff",
            relief="flat",
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda: self.kill_and_refresh("ustation.exe")
        )

        # Label danh sách
        list_lbl = tk.Label(self.root, text="CÁC ỨNG DỤNG AI ĐIỀU KHIỂN CAD:", font=("Segoe UI", 9, "bold"), fg=self.text_muted, bg=self.bg_color)
        list_lbl.pack(anchor="w", padx=25, pady=(2, 4))

        # Danh sách AI apps
        for app in self.apps:
            if app["id"] == "ustation":
                continue
            self.create_app_card(app)

        # Footer Button
        self.footer = tk.Frame(self.root, bg=self.bg_color)
        self.footer.pack(fill="x", padx=25, pady=(8, 14), side="bottom")

        self.main_action_btn = tk.Button(
            self.footer,
            text="✨ Khởi Chạy Ứng Dụng AI",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_color,
            fg="#ffffff",
            activebackground="#4f46e5",
            activeforeground="#ffffff",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=self.on_main_action
        )
        self.main_action_btn.pack(fill="x")

        self.update_ui_state()

    def create_app_card(self, app):
        card = tk.Frame(self.root, bg=self.card_color, highlightthickness=1, highlightbackground="#2e2e48")
        card.pack(fill="x", padx=25, pady=3)

        icon_lbl = tk.Label(card, text=app["icon"], font=("Segoe UI Emoji", 16), bg=self.card_color)
        icon_lbl.pack(side="left", padx=(15, 10), pady=8)

        info_frame = tk.Frame(card, bg=self.card_color)
        info_frame.pack(side="left", fill="both", expand=True, pady=6)

        name_lbl = tk.Label(info_frame, text=app["name"], font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.card_color)
        name_lbl.pack(anchor="w")

        status_lbl = tk.Label(info_frame, text="", font=("Segoe UI", 8, "bold"), bg=self.card_color)
        status_lbl.pack(anchor="w")

        btn_container = tk.Frame(card, bg=self.card_color)
        btn_container.pack(side="right", padx=12, pady=5)

        btn = tk.Button(
            btn_container,
            text="",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2"
        )
        btn.pack(side="left", padx=2)

        kill_btn = tk.Button(
            btn_container,
            text="✖ Tắt",
            font=("Segoe UI", 8, "bold"),
            bg="#3f1d24",
            fg="#f87171",
            activebackground="#7f1d1d",
            activeforeground="#ffffff",
            relief="flat",
            padx=8,
            pady=5,
            cursor="hand2",
            command=lambda p=app.get("process_name"): self.kill_and_refresh(p)
        )

        self.app_widgets[app["id"]] = {
            "status_lbl": status_lbl,
            "btn": btn,
            "kill_btn": kill_btn,
            "card": card,
        }

    def kill_and_refresh(self, process_name):
        if process_name:
            kill_app_process(process_name)
            self.root.after(300, self.update_ui_state)

    def update_ui_state(self):
        running_procs = get_running_process_names()

        for app in self.apps:
            is_running = app.get("process_name", "").lower() in running_procs
            app["is_running"] = is_running

            if app["id"] == "ustation":
                if is_running:
                    self.mstn_status_lbl.config(
                        text="🟢 ĐANG CHẠY (Sẵn sàng nhận lệnh CAD)",
                        fg=self.running_color
                    )
                    self.mstn_btn.config(
                        text="Đang Mở",
                        bg="#065f46",
                        fg="#6ee7b7"
                    )
                    self.mstn_kill_btn.pack(side="left", padx=3)
                elif app["installed"]:
                    self.mstn_status_lbl.config(
                        text="⚪ Đã cài đặt (Chưa mở phần mềm)",
                        fg=self.text_muted
                    )
                    self.mstn_btn.config(
                        text="Mở MicroStation",
                        bg="#334155",
                        fg="#ffffff"
                    )
                    self.mstn_kill_btn.pack_forget()
                else:
                    self.mstn_status_lbl.config(
                        text="⚠ Chưa tìm thấy file cài đặt",
                        fg=self.warning_color
                    )
                    self.mstn_kill_btn.pack_forget()
                continue

            widgets = self.app_widgets.get(app["id"])
            if not widgets:
                continue

            st_lbl = widgets["status_lbl"]
            btn = widgets["btn"]
            kill_btn = widgets["kill_btn"]
            card = widgets["card"]

            if is_running:
                st_lbl.config(
                    text="🟢 ĐANG CHẠY (Đã kết nối 59 Tools)",
                    fg=self.running_color
                )
                btn.config(
                    text="Mở Lại Cửa Sổ",
                    bg="#065f46",
                    fg="#6ee7b7",
                    command=lambda a=app: launch_app(a)
                )
                kill_btn.pack(side="left", padx=3)
                card.config(highlightbackground="#059669")
            elif app["installed"]:
                st_lbl.config(
                    text="⚪ Đã cài đặt (Chưa mở - Sẵn sàng 59 Tools)",
                    fg=self.text_muted
                )
                btn.config(
                    text="Mở Ứng Dụng",
                    bg=self.accent_color,
                    fg="#ffffff",
                    command=lambda a=app: launch_app(a)
                )
                kill_btn.pack_forget()
                card.config(highlightbackground="#2e2e48")
            else:
                st_lbl.config(
                    text="○ Chưa cài đặt trên máy này",
                    fg="#64748b"
                )
                btn.config(
                    text="Tải Về",
                    bg="#334155",
                    fg="#94a3b8",
                    command=lambda url=app["download_url"]: webbrowser.open(url)
                )
                kill_btn.pack_forget()
                card.config(highlightbackground="#2e2e48")

        # Nút hành động chính
        running_ai = next((a for a in self.apps if a["is_running"] and a["id"] != "ustation"), None)
        installed_ai = next((a for a in self.apps if a["installed"] and a["id"] != "ustation"), None)

        if running_ai:
            self.main_action_btn.config(
                text=f"🟢 {running_ai['name']} Đang Hoạt Động (Click để mở)",
                bg="#059669",
                command=lambda: launch_app(running_ai)
            )
        elif installed_ai:
            self.main_action_btn.config(
                text=f"✨ Khởi Chạy {installed_ai['name']} Ngay",
                bg=self.accent_color,
                command=lambda: launch_app(installed_ai)
            )

    def on_main_action(self):
        running_ai = next((a for a in self.apps if a["is_running"] and a["id"] != "ustation"), None)
        target = running_ai if running_ai else next((a for a in self.apps if a["installed"] and a["id"] != "ustation"), None)
        if target:
            launch_app(target)

    def periodic_check(self):
        try:
            self.update_ui_state()
        except Exception:
            pass
        self.root.after(1000, self.periodic_check)

    def bg_check_updates(self):
        """Kiểm tra cập nhật ngầm khi khởi động."""
        has_update, new_ver, notes, method = check_for_updates()
        if has_update:
            self.root.after(0, lambda: self.show_update_banner(new_ver, notes, method))

    def manual_check_update(self):
        """Người dùng bấm nút kiểm tra cập nhật thủ công."""
        self.check_btn.config(text="⏳ Đang kiểm tra...", state="disabled")

        def task():
            has_update, new_ver, notes, method = check_for_updates()
            def done():
                self.check_btn.config(text="🔄 Kiểm Tra Cập Nhật", state="normal")
                if has_update:
                    self.show_update_banner(new_ver, notes, method)
                else:
                    messagebox.showinfo("Cập Nhật", f"Bạn đang sử dụng phiên bản mới nhất (v{self.current_version})!")
            self.root.after(0, done)

        threading.Thread(target=task, daemon=True).start()

    def show_update_banner(self, new_ver, notes, method):
        """Hiển thị banner thông báo bản cập nhật mới."""
        self.update_info = {"version": new_ver, "method": method}

        for w in self.update_banner.winfo_children():
            w.destroy()

        self.update_banner.pack(fill="x", padx=25, pady=(0, 8), before=self.root.winfo_children()[1])

        b_icon = tk.Label(self.update_banner, text="🎉", font=("Segoe UI Emoji", 14), bg="#1e1b4b")
        b_icon.pack(side="left", padx=(12, 6), pady=8)

        text_frame = tk.Frame(self.update_banner, bg="#1e1b4b")
        text_frame.pack(side="left", fill="both", expand=True, pady=6)

        t_lbl = tk.Label(text_frame, text=f"Có bản cập nhật mới (v{new_ver}) trên GitHub!", font=("Segoe UI", 9, "bold"), fg="#a5b4fc", bg="#1e1b4b")
        t_lbl.pack(anchor="w")

        d_lbl = tk.Label(text_frame, text=notes or "Bản cập nhật nâng cấp tính năng và sửa lỗi.", font=("Segoe UI", 8), fg="#c7d2fe", bg="#1e1b4b")
        d_lbl.pack(anchor="w")

        up_btn = tk.Button(
            self.update_banner,
            text="⬇ Cập Nhật Ngay",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.trigger_update
        )
        up_btn.pack(side="right", padx=12)

    def trigger_update(self):
        """Thực hiện cập nhật 1-click."""
        if not self.update_info:
            return

        method = self.update_info.get("method", "auto")
        if not messagebox.askyesno("Xác nhận cập nhật", "Bạn có muốn tải và áp dụng bản cập nhật mới nhất từ GitHub không?"):
            return

        # Vô hiệu hóa nút và hiện trạng thái đang tải
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Đang cập nhật...")
        prog_win.geometry("380x140")
        prog_win.configure(bg=self.bg_color)
        prog_win.transient(self.root)
        prog_win.grab_set()

        lbl = tk.Label(prog_win, text="⏳ Đang tải bản cập nhật từ GitHub...", font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.bg_color)
        lbl.pack(expand=True)

        def run_update_thread():
            success, msg = perform_update(method)

            def finish():
                prog_win.destroy()
                if success:
                    messagebox.showinfo("Hoàn Tất", f"{msg}\nLauncher sẽ khởi động lại với phiên bản mới!")
                    # Khởi động lại launcher
                    if getattr(sys, "frozen", False):
                        subprocess.Popen([sys.executable])
                    else:
                        subprocess.Popen([sys.executable, os.path.join(LAUNCHER_DIR, "ai_launcher.py")])
                    self.root.destroy()
                else:
                    messagebox.showerror("Lỗi Cập Nhật", f"Không thể hoàn tất cập nhật:\n{msg}")

            self.root.after(0, finish)

        threading.Thread(target=run_update_thread, daemon=True).start()


def main():
    ensure_mcp_configs()

    if "--launch-best" in sys.argv:
        apps = detect_installed_apps()
        best_app = next((a for a in apps if a["is_running"] and a["id"] != "ustation"), None)
        if not best_app:
            best_app = next((a for a in apps if a["installed"] and a["id"] != "ustation"), None)
        if best_app:
            launch_app(best_app)
            sys.exit(0)

    root = tk.Tk()
    app = LauncherGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
