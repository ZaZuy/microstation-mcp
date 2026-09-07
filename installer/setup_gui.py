"""
installer/setup_gui.py
Giao diện cài đặt 1-Click (Setup Wizard) cho MicroStation AI CAD Bridge.
"""

import os
import sys
import json
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

DEFAULT_INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs",
    "MicroStation-AI-CAD"
)

# Thư mục gốc chứa source code (hỗ trợ cả PyInstaller một file)
SOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_python_executable():
    """Tìm python.exe thực sự của hệ thống trên máy (tránh trỏ nhầm vào file Setup exe)."""
    # Nếu đang chạy mã nguồn trực tiếp (không phải bị đóng băng bởi PyInstaller)
    if not getattr(sys, "frozen", False):
        exe = sys.executable
        if exe.lower().endswith("pythonw.exe"):
            exe = exe[:-5] + ".exe"
        if os.path.exists(exe) and "setup" not in os.path.basename(exe).lower():
            return exe

    # 1. Thử qua py.exe launcher của Windows
    try:
        out = subprocess.check_output(["py", "-3", "-c", "import sys; print(sys.executable)"], text=True, timeout=3).strip()
        if os.path.exists(out) and "windowsapps" not in out.lower():
            return out
    except Exception:
        pass

    # 2. Quét Registry Windows
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

    # 3. Quét các thư mục cài đặt tiêu chuẩn
    import glob
    user_prof = os.environ.get("USERPROFILE", "")
    candidates = glob.glob(os.path.join(user_prof, "AppData", "Local", "Programs", "Python", "Python*", "python.exe"))
    candidates += glob.glob(r"C:\Program Files\Python*\python.exe")
    candidates += glob.glob(r"C:\Python*\python.exe")
    for c in candidates:
        if os.path.exists(c):
            return c

    # 4. Tìm qua where python / shutil.which
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


class InstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cài Đặt MicroStation V8i - AI CAD Bridge")
        self.root.geometry("640x520")
        self.root.resizable(False, False)

        # Màu sắc hiện đại
        self.bg_color = "#181825"
        self.card_color = "#242438"
        self.accent_color = "#6366f1"
        self.text_color = "#ffffff"
        self.text_muted = "#94a3b8"
        self.success_color = "#10b981"

        self.root.configure(bg=self.bg_color)
        self.install_path_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.shortcut_var = tk.BooleanVar(value=True)
        self.config_claude_var = tk.BooleanVar(value=True)
        self.config_antigravity_var = tk.BooleanVar(value=True)
        self.install_deps_var = tk.BooleanVar(value=True)

        # Ép cửa sổ luôn nổi lên trên cùng màn hình khi mở
        self.force_bring_to_front()
        self.root.after(100, self.force_bring_to_front)
        self.root.after(400, self.force_bring_to_front)

        self.build_ui()

    def force_bring_to_front(self):
        """Bật cửa sổ lên hàng đầu (Foreground) và kích hoạt tiêu điểm ngay khi mở."""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.after(400, lambda: self.root.attributes("-topmost", False))

            if sys.platform == "win32":
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self.bg_color)
        header.pack(fill="x", padx=25, pady=(20, 10))

        title = tk.Label(
            header,
            text="📐 Cài Đặt MicroStation AI CAD Bridge",
            font=("Segoe UI", 16, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="Hệ thống 59 công cụ điều khiển CAD qua AI (Claude Desktop, Antigravity, Cursor...)",
            font=("Segoe UI", 9),
            fg=self.text_muted,
            bg=self.bg_color
        )
        subtitle.pack(anchor="w", pady=(3, 0))

        # Khối chọn thư mục
        folder_card = tk.Frame(self.root, bg=self.card_color, highlightthickness=1, highlightbackground="#374151")
        folder_card.pack(fill="x", padx=25, pady=8)

        f_lbl = tk.Label(folder_card, text="Thư mục cài đặt:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color)
        f_lbl.pack(anchor="w", padx=15, pady=(10, 4))

        f_box = tk.Frame(folder_card, bg=self.card_color)
        f_box.pack(fill="x", padx=15, pady=(0, 12))

        entry = tk.Entry(f_box, textvariable=self.install_path_var, font=("Segoe UI", 9), bg="#1e1e2e", fg="#ffffff", insertbackground="#ffffff", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        browse_btn = tk.Button(f_box, text="Duyệt...", font=("Segoe UI", 8), bg="#334155", fg="#ffffff", relief="flat", padx=10, command=self.browse_folder)
        browse_btn.pack(side="right")

        # Khối tùy chọn
        opts_card = tk.Frame(self.root, bg=self.card_color, highlightthickness=1, highlightbackground="#374151")
        opts_card.pack(fill="x", padx=25, pady=8)

        opt_lbl = tk.Label(opts_card, text="Tùy chọn thiết lập tự động:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color)
        opt_lbl.pack(anchor="w", padx=15, pady=(10, 6))

        c1 = tk.Checkbutton(opts_card, text="Tạo biểu tượng lối tắt (Shortcut) ra màn hình Desktop", variable=self.shortcut_var, font=("Segoe UI", 9), bg=self.card_color, fg=self.text_color, selectcolor="#1e1e2e", activebackground=self.card_color, activeforeground=self.text_color)
        c1.pack(anchor="w", padx=15, pady=2)

        c2 = tk.Checkbutton(opts_card, text="Tự động cấu hình MCP Server cho Claude Desktop", variable=self.config_claude_var, font=("Segoe UI", 9), bg=self.card_color, fg=self.text_color, selectcolor="#1e1e2e", activebackground=self.card_color, activeforeground=self.text_color)
        c2.pack(anchor="w", padx=15, pady=2)

        c3 = tk.Checkbutton(opts_card, text="Tự động cấu hình MCP Server cho Google Antigravity", variable=self.config_antigravity_var, font=("Segoe UI", 9), bg=self.card_color, fg=self.text_color, selectcolor="#1e1e2e", activebackground=self.card_color, activeforeground=self.text_color)
        c3.pack(anchor="w", padx=15, pady=2)

        c4 = tk.Checkbutton(opts_card, text="Cài đặt/Kiểm tra các thư viện Python phụ thuộc (fastmcp, pywin32)", variable=self.install_deps_var, font=("Segoe UI", 9), bg=self.card_color, fg=self.text_color, selectcolor="#1e1e2e", activebackground=self.card_color, activeforeground=self.text_color)
        c4.pack(anchor="w", padx=15, pady=(2, 12))

        # Thanh tiến trình
        self.progress_frame = tk.Frame(self.root, bg=self.bg_color)
        self.progress_frame.pack(fill="x", padx=25, pady=5)

        self.status_lbl = tk.Label(self.progress_frame, text="Sẵn sàng bắt đầu cài đặt.", font=("Segoe UI", 8), fg=self.text_muted, bg=self.bg_color)
        self.status_lbl.pack(anchor="w", pady=(0, 4))

        self.pbar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.pbar.pack(fill="x")

        # Nút Cài đặt
        self.install_btn = tk.Button(
            self.root,
            text="🚀 Bắt Đầu Cài Đặt",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_color,
            fg="#ffffff",
            activebackground="#4f46e5",
            activeforeground="#ffffff",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=self.start_installation
        )
        self.install_btn.pack(fill="x", padx=25, pady=(15, 20), side="bottom")

    def browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.install_path_var.get())
        if d:
            self.install_path_var.set(os.path.join(d, "MicroStation-AI-CAD"))

    def start_installation(self):
        self.install_btn.config(state="disabled", text="⏳ Đang cài đặt, vui lòng chờ...")
        threading.Thread(target=self.run_install_process, daemon=True).start()

    def update_status(self, text, progress):
        self.root.after(0, lambda: (self.status_lbl.config(text=text), self.pbar.config(value=progress)))

    def run_install_process(self):
        target_dir = os.path.abspath(self.install_path_var.get())
        py_exe = find_python_executable()

        try:
            # Bước 1: Tạo thư mục đích
            self.update_status("1/5. Đang khởi tạo thư mục cài đặt...", 15)
            os.makedirs(target_dir, exist_ok=True)

            # Bước 2: Sao chép mã nguồn
            self.update_status("2/5. Đang sao chép các tệp chương trình...", 35)
            for item in ["src", "launcher", "docs"]:
                s = os.path.join(SOURCE_DIR, item)
                d = os.path.join(target_dir, item)
                if os.path.exists(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)

            for item in ["README.md", "AGENTS.md", "pyproject.toml", "requirements.txt", "server.py", "ms_bridge.py"]:
                s = os.path.join(SOURCE_DIR, item)
                d = os.path.join(target_dir, item)
                if os.path.exists(s):
                    shutil.copy2(s, d)

            # Bước 3: Cài đặt dependencies
            if self.install_deps_var.get():
                self.update_status("3/5. Đang cài đặt thư viện Python (fastmcp, pywin32)...", 60)
                req_path = os.path.join(target_dir, "requirements.txt")
                if os.path.exists(req_path):
                    subprocess.run(
                        [py_exe, "-m", "pip", "install", "-r", req_path, "--quiet"],
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

            # Bước 4: Đồng bộ cấu hình MCP
            self.update_status("4/5. Đang cấu hình kết nối MCP cho các ứng dụng AI...", 80)
            main_py = os.path.join(target_dir, "src", "main.py")
            mcp_entry = {
                "command": py_exe,
                "args": ["-X", "utf8", main_py],
            }

            if self.config_antigravity_var.get():
                gemini_dir = os.path.expanduser(r"~/.gemini/config")
                gemini_cfg = os.path.join(gemini_dir, "mcp_config.json")
                try:
                    os.makedirs(gemini_dir, exist_ok=True)
                    d = {}
                    if os.path.exists(gemini_cfg):
                        with open(gemini_cfg, "r", encoding="utf-8") as f:
                            d = json.load(f)
                    if "mcpServers" not in d:
                        d["mcpServers"] = {}
                    d["mcpServers"]["microstation-v8i"] = mcp_entry
                    with open(gemini_cfg, "w", encoding="utf-8") as f:
                        json.dump(d, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            if self.config_claude_var.get():
                claude_dir = os.path.expandvars(r"%APPDATA%\Claude")
                claude_cfg = os.path.join(claude_dir, "claude_desktop_config.json")
                try:
                    os.makedirs(claude_dir, exist_ok=True)
                    d = {}
                    if os.path.exists(claude_cfg):
                        with open(claude_cfg, "r", encoding="utf-8") as f:
                            d = json.load(f)
                    if "mcpServers" not in d:
                        d["mcpServers"] = {}
                    d["mcpServers"]["microstation-v8i"] = mcp_entry
                    with open(claude_cfg, "w", encoding="utf-8") as f:
                        json.dump(d, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            # Bước 5: Tạo Shortcut Desktop
            if self.shortcut_var.get():
                self.update_status("5/5. Đang tạo biểu tượng Desktop...", 95)
                try:
                    import win32com.client
                    wsh = win32com.client.Dispatch("WScript.Shell")
                    desktop = wsh.SpecialFolders("Desktop")
                    lnk_path = os.path.join(desktop, "MicroStation AI Launcher.lnk")

                    pyw_exe = py_exe.replace("python.exe", "pythonw.exe")
                    exec_bin = pyw_exe if os.path.exists(pyw_exe) else py_exe
                    launcher_script = os.path.join(target_dir, "launcher", "ai_launcher.py")

                    sc = wsh.CreateShortcut(lnk_path)
                    sc.TargetPath = exec_bin
                    sc.Arguments = f'"{launcher_script}"'
                    sc.WorkingDirectory = target_dir
                    sc.Description = "MicroStation V8i AI CAD Launcher"
                    mstn_exe = r"C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe"
                    if os.path.exists(mstn_exe):
                        sc.IconLocation = f"{mstn_exe}, 0"
                    sc.Save()
                except Exception:
                    pass

            self.update_status("✓ Cài đặt hoàn tất thành công 100%!", 100)
            self.root.after(0, lambda: self.finish_success(target_dir))

        except Exception as ex:
            self.update_status(f"Lỗi: {ex}", 0)
            self.root.after(0, lambda: messagebox.showerror("Lỗi Cài Đặt", f"Đã xảy ra lỗi:\n{ex}"))
            self.root.after(0, lambda: self.install_btn.config(state="normal", text="🚀 Thử Lại"))

    def finish_success(self, target_dir):
        if messagebox.askyesno(
            "Cài Đặt Thành Công",
            "Đã cài đặt hoàn tất MicroStation AI CAD Bridge!\n\n"
            "- Đã tạo Shortcut 'MicroStation AI Launcher' ra Desktop.\n"
            "- Đã cấu hình kết nối vào Claude Desktop & Antigravity.\n\n"
            "Bạn có muốn mở ngay AI Launcher không?"
        ):
            launcher_py = os.path.join(target_dir, "launcher", "ai_launcher.py")
            py_exe = find_python_executable()
            pyw_exe = py_exe.replace("python.exe", "pythonw.exe")
            exec_bin = pyw_exe if os.path.exists(pyw_exe) else py_exe
            subprocess.Popen([exec_bin, launcher_py], cwd=target_dir)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = InstallerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
