"""
src/tools/text.py
Các công cụ văn bản, ghi chú, tìm kiếm và thay thế Text trong MicroStation V8i.
"""

from typing import List, Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_text_tools(mcp):
    """Đăng ký các tool văn bản vào MCP Server."""

    @mcp.tool
    def place_text(
        text: str,
        x: float,
        y: float,
        height: float = 2.5,
        width: Optional[float] = None,
        rotation_deg: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> str:
        """
        Đặt một chuỗi văn bản (Text Element) tại tọa độ (x, y).

        :param text: Nội dung chữ cần ghi
        :param x: Tọa độ X đặt chữ
        :param y: Tọa độ Y đặt chữ
        :param height: Chiều cao chữ (theo đơn vị bản vẽ, ví dụ 2.5m hoặc 250mm)
        :param width: Chiều rộng chữ (nếu bỏ trống sẽ lấy bằng chiều cao)
        :param rotation_deg: Góc xoay chữ theo độ (0 là chữ nằm ngang)
        :param level: Tên Level đặt chữ
        :param color: Màu chữ (0-255)
        :param weight: Độ đậm nét chữ
        """
        app = bridge.get_app()
        origin = bridge.create_point(x, y, 0.0)
        matrix = bridge.create_rotation_matrix(rotation_deg)

        text_elem = bridge.unwrap(app.CreateTextElement1(None, str(text), origin, matrix))

        try:
            text_elem.TextStyle.Height = float(height)
            text_elem.TextStyle.Width = float(width if width is not None else height)
        except Exception:
            pass

        bridge.apply_symbology(text_elem, level=level, color=color, weight=weight)
        bridge.add_element(text_elem)

        return f"Đã đặt text '{text}' tại tọa độ ({x}, {y}) với chiều cao {height}"

    @mcp.tool
    def place_text_node(
        lines: List[str],
        x: float,
        y: float,
        height: float = 2.5,
        rotation_deg: float = 0.0,
        level: Optional[str] = None,
        color: Optional[int] = None,
    ) -> str:
        """
        Đặt một khối văn bản nhiều dòng (Text Node) tại tọa độ (x, y).

        :param lines: Danh sách các dòng chữ ['Dòng 1', 'Dòng 2', 'Dòng 3']
        :param x: Tọa độ X
        :param y: Tọa độ Y
        :param height: Chiều cao chữ
        :param rotation_deg: Góc xoay chữ
        :param level: Tên Level
        :param color: Màu chữ
        """
        if not lines:
            return "Lỗi: Danh sách dòng chữ trống!"

        app = bridge.get_app()
        origin = bridge.create_point(x, y, 0.0)
        matrix = bridge.create_rotation_matrix(rotation_deg)

        node_elem = bridge.unwrap(app.CreateTextNodeElement1(None, origin, matrix))

        try:
            node_elem.TextStyle.Height = float(height)
            node_elem.TextStyle.Width = float(height)
        except Exception:
            pass

        for line in lines:
            node_elem.AddTextLine(str(line))

        bridge.apply_symbology(node_elem, level=level, color=color)
        bridge.add_element(node_elem)

        return f"Đã đặt khối text gồm {len(lines)} dòng tại ({x}, {y})"

    @mcp.tool
    def find_text(keyword: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Tìm kiếm tất cả các phần tử Text hoặc TextNode chứa chuỗi từ khóa trong bản vẽ.

        :param keyword: Từ khóa cần tìm kiếm
        :param case_sensitive: Phân biệt chữ hoa/thường (mặc định False)
        """
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        results = []
        target_kw = keyword if case_sensitive else keyword.lower()

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
            except Exception:
                continue
            if not el:
                continue

            el_type = int(el.Type)
            text_val = ""
            origin = [0.0, 0.0]

            if el_type == 17:  # Text
                try:
                    te = el.AsTextElement()
                    text_val = te.Text
                    pt = te.Origin
                    origin = [round(pt.X, 3), round(pt.Y, 3)]
                except Exception:
                    continue
            elif el_type == 7:  # TextNode
                try:
                    tne = el.AsTextNodeElement()
                    lines = [tne.TextLine(i) for i in range(1, tne.TextLinesCount + 1)]
                    text_val = "\n".join(lines)
                    pt = tne.Origin
                    origin = [round(pt.X, 3), round(pt.Y, 3)]
                except Exception:
                    continue
            else:
                continue

            check_val = text_val if case_sensitive else text_val.lower()
            if target_kw in check_val:
                results.append({
                    "id": str(getattr(el, "ID64", getattr(el, "ID", ""))),
                    "type": "Text" if el_type == 17 else "TextNode",
                    "text": text_val,
                    "origin": origin,
                    "level": el.Level.Name if el.Level else "",
                })

        return results

    @mcp.tool
    def replace_text(find_str: str, replace_with: str, case_sensitive: bool = False) -> str:
        """
        Tìm và thay thế một chuỗi ký tự trong tất cả các phần tử Text trong bản vẽ.

        :param find_str: Chuỗi ký tự cần tìm
        :param replace_with: Chuỗi ký tự thay thế
        :param case_sensitive: Phân biệt chữ hoa/thường
        """
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        replaced_count = 0

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
            except Exception:
                continue
            if not el:
                continue

            if int(el.Type) == 17:  # Text
                try:
                    te = el.AsTextElement()
                    cur_text = te.Text
                    if (find_str in cur_text) if case_sensitive else (find_str.lower() in cur_text.lower()):
                        new_text = cur_text.replace(find_str, replace_with)
                        te.Text = new_text
                        te.Rewrite()
                        te.Redraw()
                        replaced_count += 1
                except Exception:
                    continue

        return f"Đã thay thế thành công trong {replaced_count} phần tử text."
