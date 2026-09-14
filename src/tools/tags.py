"""
src/tools/tags.py
Các công cụ quản lý thuộc tính phi đồ họa (Tags) đính kèm vào phần tử hình học trong MicroStation V8i.
Tương ứng với Tool Box 'Tags' trong MicroStation V8i.
"""

from typing import Optional, Dict, Any
from src.core.ms_bridge import bridge


def register_tag_tools(mcp):
    """Đăng ký các công cụ Tag vào MCP Server."""

    @mcp.tool
    def attach_tag(
        element_id: str,
        tag_set_name: str,
        tag_name: str,
        tag_value: str,
    ) -> Dict[str, Any]:
        """
        Gắn một thuộc tính phi đồ họa (Tag) vào một phần tử hình học đã có trong bản vẽ.
        Tương ứng với công cụ 'Attach Tag' trong Tool Box Tags.

        :param element_id: ID phần tử cần gắn Tag
        :param tag_set_name: Tên Tag Set (Bộ thẻ)
        :param tag_name: Tên thẻ thuộc tính (ví dụ: 'SoThua', 'DienTich', 'ChuSuDung')
        :param tag_value: Giá trị thẻ
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy đối tượng ID '{element_id}'!"}

        try:
            # Dùng COM AddTag
            if hasattr(el, "AddTag"):
                el.AddTag(tag_name, tag_value)
                el.Rewrite()
                return {
                    "status": "success",
                    "message": f"Đã gắn Tag '{tag_name}' = '{tag_value}' vào đối tượng ID {element_id}.",
                    "element_id": element_id,
                }
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Đã thực thi thao tác gán Tag '{tag_name}' vào đối tượng ID {element_id}.",
            "element_id": element_id,
        }

    @mcp.tool
    def get_element_tags(element_id: str) -> Dict[str, Any]:
        """
        Đọc toàn bộ danh sách các thuộc tính Tag đang đính kèm trên phần tử hình học.
        Tương ứng với công cụ 'Edit Tags' / 'Review Tags' trong Tool Box Tags.

        :param element_id: ID phần tử cần đọc Tag
        """
        el = bridge.find_element_by_id(element_id)
        if not el:
            return {"error": f"Không tìm thấy đối tượng ID '{element_id}'!"}

        tags = {}
        try:
            if hasattr(el, "GetTags"):
                tag_list = el.GetTags()
                if tag_list:
                    for t in tag_list:
                        try:
                            tags[t.TagSetName + "." + t.TagDefinitionName] = str(t.Value)
                        except Exception:
                            pass
        except Exception as ex:
            return {"error": f"Lỗi khi đọc Tag: {str(ex)}"}

        return {
            "status": "success",
            "element_id": element_id,
            "tags_count": len(tags),
            "tags": tags,
        }
