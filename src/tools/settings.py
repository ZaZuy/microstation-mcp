"""
src/tools/settings.py
Các công cụ cấu hình thuộc tính vẽ (Level, Color, Weight, LineStyle, Hiển thị Layer) trong MicroStation V8i.
"""

from typing import Optional
from src.core.ms_bridge import bridge


def register_settings_tools(mcp):
    """Đăng ký các tool cấu hình vào MCP Server."""

    @mcp.tool
    def set_active_level(level_name: str) -> str:
        """
        Thay đổi Level đang hoạt động (Active Level) trong MicroStation.

        :param level_name: Tên level muốn kích hoạt (ví dụ: 'Defpoints', 'Default', 'DuongTim'...)
        """
        app = bridge.get_app()
        dgn = bridge.get_active_file()

        lvl = dgn.Levels.Find(level_name)
        if not lvl:
            lvl = dgn.AddNewLevel(level_name)
            dgn.RewriteLevels()

        app.ActiveSettings.Level = lvl
        return f"Đã chuyển Active Level sang: '{level_name}'"

    @mcp.tool
    def set_active_color(color_index: int) -> str:
        """
        Thay đổi màu vẽ hiện tại (Active Color).

        :param color_index: Chỉ số màu từ 0 đến 255 (ví dụ 0=trắng, 1=xanh dương, 2=xanh lá, 3=đỏ...)
        """
        if not (0 <= color_index <= 255):
            return "Lỗi: Chỉ số màu phải nằm trong khoảng 0 - 255!"

        app = bridge.get_app()
        app.ActiveSettings.Color = int(color_index)
        return f"Đã đổi Active Color sang: {color_index}"

    @mcp.tool
    def set_active_weight(weight: int) -> str:
        """
        Thay đổi độ dày nét vẽ hiện tại (Active LineWeight).

        :param weight: Độ dày nét từ 0 đến 31 (0 là mảnh nhất)
        """
        if not (0 <= weight <= 31):
            return "Lỗi: Độ dày nét phải nằm trong khoảng 0 - 31!"

        app = bridge.get_app()
        app.ActiveSettings.LineWeight = int(weight)
        return f"Đã đổi Active LineWeight sang: {weight}"

    @mcp.tool
    def set_active_style(style_index: int) -> str:
        """
        Thay đổi kiểu nét vẽ hiện tại (Active LineStyle).

        :param style_index: Kiểu nét từ 0 đến 7 (0=Solid, 1=Dotted, 2=Medium Dash, 3=Long Dash, 4=Dot-Dash...)
        """
        app = bridge.get_app()
        dgn = bridge.get_active_file()
        try:
            style_obj = dgn.LineStyles.Item(int(style_index))
            app.ActiveSettings.LineStyle = style_obj
            return f"Đã đổi Active LineStyle sang kiểu số: {style_index}"
        except Exception as ex:
            return f"Không thể đổi LineStyle: {ex}"

    @mcp.tool
    def create_level(level_name: str) -> str:
        """
        Tạo mới một Level trong file bản vẽ DGN nếu chưa tồn tại.

        :param level_name: Tên level mới cần tạo
        """
        dgn = bridge.get_active_file()
        existing = dgn.Levels.Find(level_name)
        if existing:
            return f"Level '{level_name}' đã tồn tại sẵn trong bản vẽ."

        dgn.AddNewLevel(level_name)
        dgn.RewriteLevels()
        return f"Đã tạo thành công Level mới: '{level_name}'"

    @mcp.tool
    def set_level_display(
        level_name: str,
        is_displayed: bool = True,
        view_number: Optional[int] = None,
    ) -> str:
        """
        Bật hoặc Tắt hiển thị (Layer On/Off) của một Level trong cửa sổ View.

        :param level_name: Tên Level cần bật/tắt
        :param is_displayed: True để bật hiển thị, False để ẩn
        :param view_number: Số hiệu View (1-8, nếu None sẽ áp dụng toàn cục)
        """
        app = bridge.get_app()
        dgn = bridge.get_active_file()
        lvl = dgn.Levels.Find(level_name)
        if not lvl:
            return f"Lỗi: Không tìm thấy Level '{level_name}' trong bản vẽ!"

        try:
            if view_number and 1 <= view_number <= app.Views.Count:
                v = app.Views(view_number)
                lvl.SetIsDisplayedInView(v, bool(is_displayed))
                v.Redraw()
            else:
                lvl.IsDisplayed = bool(is_displayed)
                dgn.RewriteLevels()
                for i in range(1, app.Views.Count + 1):
                    try:
                        app.Views(i).Redraw()
                    except Exception:
                        pass
            state_str = "Bật" if is_displayed else "Tắt"
            view_str = f" trong View {view_number}" if view_number else " trên tất cả View"
            return f"Đã {state_str} hiển thị cho Level '{level_name}'{view_str}."
        except Exception as ex:
            # Fallback dùng Key-in
            cmd = f"{'set levels on' if is_displayed else 'set levels off'} {level_name}"
            app.CadInputQueue.SendKeyin(cmd)
            return f"Đã gửi lệnh key-in thay đổi hiển thị Level '{level_name}'."
