"""
launcher/updater.py
Module quản lý tự động kiểm tra và thực hiện cập nhật mã nguồn từ GitHub.
Hỗ trợ cả 2 phương thức:
1. Git pull (nếu người dùng cài đặt thông qua Git clone).
2. Tải trực tiếp gói cập nhật từ GitHub Releases / Repository (nếu người dùng cài đặt bằng bộ cài .exe).
"""

import os
import sys
import json
import zipfile
import shutil
import urllib.request
import subprocess
from typing import Dict, Any, Tuple

LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(LAUNCHER_DIR)
VERSION_FILE = os.path.join(LAUNCHER_DIR, "version.json")


def get_local_config() -> Dict[str, Any]:
    """Đọc cấu hình phiên bản hiện tại trên máy."""
    default_cfg = {
        "version": "1.0.0",
        "github_repo": "your-username/microstation-mcp",
        "branch": "main",
        "release_notes": "Bản khởi tạo.",
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
    """So sánh 2 chuỗi version ngữ nghĩa (Semantic Versioning), ví dụ '1.1.0' > '1.0.0'."""
    try:
        def parse_v(v_str):
            v = str(v_str).strip().lstrip("v").split(".")
            return [int(x) for x in v if x.isdigit()]
        return parse_v(remote_ver) > parse_v(local_ver)
    except Exception:
        return str(remote_ver).strip() != str(local_ver).strip()


def check_for_updates() -> Tuple[bool, str, str, str]:
    """
    Kiểm tra xem có bản cập nhật mới trên GitHub hay không.
    Trả về: (has_update, latest_version, release_notes, update_method)
    """
    cfg = get_local_config()
    local_version = cfg.get("version", "1.0.0")
    repo = cfg.get("github_repo", "")
    branch = cfg.get("branch", "main")

    # 1. Kiểm tra qua Git nếu thư mục có .git
    git_dir = os.path.join(PROJECT_ROOT, ".git")
    if os.path.exists(git_dir):
        try:
            # Thử git fetch
            subprocess.run(["git", "fetch", "origin", branch], cwd=PROJECT_ROOT, capture_output=True, timeout=10)
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
            remote_hash = subprocess.check_output(["git", "rev-parse", f"origin/{branch}"], cwd=PROJECT_ROOT, text=True).strip()
            if local_hash != remote_hash:
                return True, "Mới nhất (Git)", "Có commit mới từ nhánh chính của repository.", "git"
        except Exception:
            pass

    # 2. Kiểm tra qua GitHub API / raw version.json
    if repo and "your-username" not in repo:
        raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/launcher/version.json"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "MicroStation-AI-Launcher"})
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    remote_data = json.loads(response.read().decode("utf-8"))
                    remote_ver = remote_data.get("version", "")
                    notes = remote_data.get("release_notes", "Bản cập nhật tính năng mới.")
                    if is_newer_version(remote_ver, local_version):
                        return True, remote_ver, notes, "github_download"
        except Exception:
            pass

    return False, local_version, "", "none"


def perform_update(update_method: str = "auto") -> Tuple[bool, str]:
    """
    Thực hiện tải và cập nhật mã nguồn mới.
    """
    cfg = get_local_config()
    repo = cfg.get("github_repo", "")
    branch = cfg.get("branch", "main")
    git_dir = os.path.join(PROJECT_ROOT, ".git")

    # 1. Cập nhật qua Git pull nếu có .git
    if os.path.exists(git_dir) or update_method == "git":
        try:
            res = subprocess.run(["git", "pull", "--rebase", "origin", branch], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                return True, "Đã cập nhật thành công qua Git pull!"
            else:
                return False, f"Lỗi Git pull: {res.stderr}"
        except Exception as ex:
            return False, f"Ngoại lệ khi chạy Git pull: {ex}"

    # 2. Cập nhật qua tải gói zip từ GitHub
    if repo and "your-username" not in repo:
        zip_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
        temp_zip = os.path.join(PROJECT_ROOT, "temp_update.zip")
        temp_extract = os.path.join(PROJECT_ROOT, "temp_extracted")
        try:
            req = urllib.request.Request(zip_url, headers={"User-Agent": "MicroStation-AI-Launcher"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)

            # Giải nén
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract, ignore_errors=True)
            os.makedirs(temp_extract, exist_ok=True)

            with zipfile.ZipFile(temp_zip, "r") as zf:
                zf.extractall(temp_extract)

            # Thư mục giải nén thường là repo-name-branch
            extracted_subdirs = [os.path.join(temp_extract, d) for d in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, d))]
            source_dir = extracted_subdirs[0] if extracted_subdirs else temp_extract

            # Copy đè mã nguồn src/ và launcher/
            for folder in ["src", "launcher", "docs"]:
                src_path = os.path.join(source_dir, folder)
                dst_path = os.path.join(PROJECT_ROOT, folder)
                if os.path.exists(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

            for single_file in ["README.md", "AGENTS.md", "pyproject.toml", "requirements.txt"]:
                src_file = os.path.join(source_dir, single_file)
                dst_file = os.path.join(PROJECT_ROOT, single_file)
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_file)

            # Dọn dẹp file tạm
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract, ignore_errors=True)

            return True, "Đã tải và áp dụng bản cập nhật mới thành công!"
        except Exception as ex:
            return False, f"Lỗi tải gói cập nhật: {ex}"

    return False, "Chưa cấu hình kho lưu trữ GitHub hợp lệ trong launcher/version.json."
