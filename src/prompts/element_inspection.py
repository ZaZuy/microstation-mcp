"""
src/prompts/element_inspection.py
Prompt mẫu hướng dẫn kiểm tra, rà soát và bóc tách dữ liệu bản vẽ MicroStation V8i.
"""

def register_element_inspection_prompt(mcp):
    """Đăng ký Prompt mẫu cho kiểm tra bản vẽ CAD."""

    @mcp.prompt()
    def element_inspection(level_filter: str = "") -> str:
        """
        Khuôn mẫu hướng dẫn LLM kiểm tra và phân tích các đối tượng đồ họa trong bản vẽ DGN.
        :param level_filter: Tên Level cần lọc (để trống nếu muốn kiểm tra tổng thể)
        """
        filter_hint = f"trên Level '{level_filter}'" if level_filter else "trên toàn bộ bản vẽ"
        return f"""
Bạn đang đóng vai trò là Kiểm toán viên Dữ liệu Bản vẽ (CAD Quality Assurance Auditor).
Mục tiêu của bạn là kiểm tra đối tượng {filter_hint}.

Quy trình thực hiện:
1. Gọi `scan_elements(level='{level_filter}' if '{level_filter}' else None, max_count=200)` để thu thập thông tin các phần tử.
2. Phân loại đối tượng theo Type (Text, TextNode, Line, LineString, Shape, ComplexShape).
3. Đánh giá tính chuẩn xác:
   - Các text ghi chú có bị sai layer hoặc kích thước chữ bất thường không?
   - Các đường bao Shape có bị hở hoặc diện tích bất thường không?
4. Trình bày báo cáo rõ ràng dạng bảng cho người dùng:
   - Tổng số phần tử tìm thấy
   - Phân bố theo kiểu hình học
   - Cảnh báo các bất thường (nếu có).
"""
