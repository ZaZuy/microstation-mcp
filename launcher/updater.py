"""
launcher/updater.py
Module quan ly tu dong kiem tra va thuc hien cap nhat tu GitHub Releases.
Luong:
  1. Doc version.json local de biet phien ban hien tai.
  2. Doc version.json tren GitHub (raw) de lay phien ban moi nhat.
  3. Neu co ban moi: tai Vigela_AI_App.exe tu GitHub Releases ve, roi chay installer moi.
"""

import os
import sys
import json
import shutil
import subprocess
import urllib.request
import urllib.error
import tempfile
from typing import Dict, Any, Tuple

# Khi chay la frozen exe: LAUNCHER_DIR la thu muc chua Vigela_AI_Launcher.exe
if getattr(sys, "frozen", False):
    LAUNCHER_DIR = os.path.dirname(sys.executable)
else:
    LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(LAUNCHER_DIR)
VERSION_FILE = os.path.join(LAUNCHER_DIR, "version.json")


def get_local_config() -> Dict[str, Any]:
    """Doc cau hinh phien ban hien tai tren may."""
    default_cfg = {
        "version": "1.0.0",
        "github_repo": "ZaZuy/microstation-mcp",
        "branch": "main",
        "release_notes": "Ban khoi tao.",
    }
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def is_newer_version(remote_ver: str, local_ver: str) -> bool:
    try:
        def parse_v(v_str):
            v = str(v_str).strip().lstrip("v").split(".")
            return [int(x) for x in v if x.isdigit()]
        return parse_v(remote_ver) > parse_v(local_ver)
    except Exception:
        return str(remote_ver).strip() != str(local_ver).strip()


def check_for_updates() -> Tuple[bool, str, str, str]:
    cfg = get_local_config()
    local_version = cfg.get("version", "1.0.0")
    repo = cfg.get("github_repo", "")
    branch = cfg.get("branch", "main")

    if not repo or "your-username" in repo:
        return False, local_version, "", "none"

    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/launcher/version.json"
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "Vigela-AI-Launcher"})
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                remote_data = json.loads(response.read().decode("utf-8"))
                remote_ver = remote_data.get("version", "")
                notes = remote_data.get("release_notes", "Ban cap nhat tinh nang moi.")
                if is_newer_version(remote_ver, local_version):
                    return True, remote_ver, notes, "github_release"
    except Exception:
        pass

    return False, local_version, "", "none"


def perform_update(update_method: str = "auto") -> Tuple[bool, str]:
    cfg = get_local_config()
    repo = cfg.get("github_repo", "")

    if not repo or "your-username" in repo:
        return False, "Chua cau hinh kho luu tru GitHub hop le trong launcher/version.json."

    release_asset_url = f"https://github.com/{repo}/releases/latest/download/Vigela_AI_App.exe"

    try:
        temp_dir = tempfile.mkdtemp(prefix="vigela_update_")
        installer_path = os.path.join(temp_dir, "Vigela_AI_App_Update.exe")

        req = urllib.request.Request(release_asset_url, headers={"User-Agent": "Vigela-AI-Launcher"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(installer_path, "wb") as out_f:
            while True:
                data = resp.read(65536)
                if not data:
                    break
                out_f.write(data)

        if not os.path.exists(installer_path) or os.path.getsize(installer_path) < 1024:
            return False, "File tai ve bi loi hoac qua nho."

        subprocess.Popen([installer_path], cwd=temp_dir)
        return True, "Dang mo bo cai dat ban moi. Vui long lam theo huong dan de hoan tat cap nhat."

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, (
                f"Khong tim thay ban cai dat moi tren GitHub Releases.\n"
                f"Ban hay den: https://github.com/{repo}/releases de tai thu cong."
            )
        return False, f"Loi HTTP {e.code} khi tai ban cap nhat."
    except Exception as ex:
        return False, f"Loi tai ban cap nhat: {ex}"
