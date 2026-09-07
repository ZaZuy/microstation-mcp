"""
src/tools/keyin.py
Công cụ thực thi lệnh Key-in trực tiếp trong MicroStation V8i.
"""

from typing import List
from src.core.ms_bridge import bridge


def register_keyin_tools(mcp):
    """Đăng ký các tool Key-in vào MCP Server."""

    @mcp.tool
    def send_keyin(command: str) -> str:
        """
        Gửi một câu lệnh Key-in trực tiếp vào MicroStation V8i.
        Ví dụ:
        - 'fit all' (zoom toàn bộ bản vẽ)
        - 'lv=Defpoints' (đổi level)
        - 'co=3' (đổi màu)
        - 'as=100' (đổi tỉ lệ annotation)
        - 'dialog elementproperties' (mở hộp thoại thuộc tính)

        :param command: Chuỗi lệnh MicroStation key-in
        """
        app = bridge.get_app()
        try:
            app.CadInputQueue.SendKeyin(str(command))
            return f"Đã thực thi lệnh key-in: '{command}'"
        except Exception as ex:
            return f"Lỗi khi gửi lệnh key-in '{command}': {ex}"

    @mcp.tool
    def run_keyin_script(commands: List[str]) -> str:
        """
        Thực thi một chuỗi nhiều lệnh Key-in tuần tự.

        :param commands: Danh sách các lệnh key-in theo thứ tự
        """
        app = bridge.get_app()
        success_count = 0
        errors = []

        for idx, cmd in enumerate(commands):
            cmd_str = str(cmd).strip()
            if not cmd_str:
                continue
            try:
                app.CadInputQueue.SendKeyin(cmd_str)
                success_count += 1
            except Exception as ex:
                errors.append(f"Lệnh #{idx+1} '{cmd_str}': {ex}")

        msg = f"Đã chạy thành công {success_count}/{len(commands)} lệnh key-in."
        if errors:
            msg += "\nCác lỗi xảy ra:\n" + "\n".join(errors)
        return msg
