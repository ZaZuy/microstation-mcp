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

        try:
            try:
                dgn.Levels(level_name)
            except Exception:
                dgn.AddNewLevel(level_name)
                dgn.RewriteLevels()

            app.CadInputQueue.SendKeyin(f'lv="{level_name}"')
            return f"Đã chuyển Active Level sang: '{level_name}'"
        except Exception as ex:
            return f"Lỗi khi đổi Active Level: {ex}"

    @mcp.tool
    def set_active_color(color_index: int) -> str:
        """
        Thay đổi màu vẽ hiện tại (Active Color).

        :param color_index: Chỉ số màu từ 0 đến 255 (bảng màu chuẩn MicroStation: 0=Trắng, 1=Xanh dương, 2=Xanh lá, 3=Đỏ, 4=Vàng [RGB: 255,255,0], 5=Tím, 6=Cam, 7=Xanh lơ/Cyan)
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
        try:
            app.CadInputQueue.SendKeyin(f"lc={int(style_index)}")
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
        try:
            existing = dgn.Levels(level_name)
        except Exception:
            existing = None

        if existing:
            return f"Level '{level_name}' đã tồn tại sẵn trong bản vẽ."

        try:
            dgn.AddNewLevel(level_name)
            dgn.RewriteLevels()
            return f"Đã tạo thành công Level mới: '{level_name}'"
        except Exception as ex:
            return f"Lỗi khi tạo Level mới '{level_name}': {ex}"

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
        try:
            lvl = dgn.Levels(level_name)
        except Exception:
            lvl = None

        if not lvl:
            return f"Lỗi: Không tìm thấy Level '{level_name}' trong bản vẽ!"

        try:
            if view_number and 1 <= view_number <= app.Views.Count:
                try:
                    v = app.Views(view_number)
                    lvl.SetIsDisplayedInView(v, bool(is_displayed))
                    v.Redraw()
                except Exception:
                    action = "on" if is_displayed else "off"
                    app.CadInputQueue.SendKeyin(f'level set display {action} "{level_name}"')
                    app.CadInputQueue.SendKeyin(f"view update {view_number}")
            else:
                try:
                    lvl.IsDisplayed = bool(is_displayed)
                    dgn.RewriteLevels()
                except Exception:
                    pass
                action = "on" if is_displayed else "off"
                app.CadInputQueue.SendKeyin(f'level set display {action} "{level_name}"')
                app.CadInputQueue.SendKeyin("update all")

            state_str = "Bật" if is_displayed else "Tắt"
            view_str = f" trong View {view_number}" if view_number else " trên tất cả View"
            return f"Đã {state_str} hiển thị cho Level '{level_name}'{view_str}."
        except Exception as ex:
            action = "on" if is_displayed else "off"
            app.CadInputQueue.SendKeyin(f'level set display {action} "{level_name}"')
            app.CadInputQueue.SendKeyin("update all")
            return f"Đã gửi lệnh key-in thay đổi hiển thị Level '{level_name}' ({action})."

    @mcp.tool
    def match_element_attributes(element_id: str) -> str:
        """
        Lấy các thuộc tính (Level, Color, Weight, LineStyle) từ một đối tượng có sẵn
        và gán làm thông số vẽ hiện hành (Match Element Attributes / Pipette).
        Tương ứng với công cụ 'Match Element Attributes' trong Tool Box Attributes.

        :param element_id: ID của phần tử mẫu cần lấy thuộc tính
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return f"Lỗi: Không tìm thấy phần tử có ID {element_id}"

        app = bridge.get_app()
        lvl_name = ""
        try:
            if el.Level:
                lvl_name = el.Level.Name
                app.CadInputQueue.SendKeyin(f'lv="{lvl_name}"')
        except Exception:
            pass

        try:
            app.ActiveSettings.Color = el.Color
            app.ActiveSettings.LineWeight = el.LineWeight
            if hasattr(el, "LineStyle") and el.LineStyle:
                try:
                    app.CadInputQueue.SendKeyin(f"lc={el.LineStyle.Name}")
                except Exception:
                    pass
        except Exception:
            pass

        return f"Đã sao chép thuộc tính từ đối tượng ID {element_id} làm Active Settings: Level='{lvl_name}', Color={getattr(el, 'Color', None)}, Weight={getattr(el, 'LineWeight', None)}."

