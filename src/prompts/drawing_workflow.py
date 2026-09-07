"""
src/prompts/drawing_workflow.py
Prompt mẫu hướng dẫn quy trình vẽ kỹ thuật trên MicroStation V8i.
"""

def register_drawing_workflow_prompt(mcp):
    """Đăng ký Prompt mẫu cho quy trình vẽ CAD."""

    @mcp.prompt()
    def cad_drawing_workflow(task_description: str) -> str:
        """
        Khuôn mẫu tương tác hướng dẫn LLM thực hiện một tác vụ vẽ kỹ thuật chuẩn mực trong MicroStation.
        :param task_description: Mô tả yêu cầu vẽ (ví dụ: Vẽ khung tên A3, Vẽ tim đường và cọc giải phóng mặt bằng...)
        """
        return f"""
Bạn là chuyên gia CAD MicroStation V8i giàu kinh nghiệm. Bạn đang chuẩn bị thực hiện yêu cầu sau:
"{task_description}"

Hãy tuân thủ quy trình chuẩn 4 bước sau:
1. KIỂM TRA MÔI TRƯỜNG:
   - Gọi tool `get_drawing_info` để xác định Master Unit (m hay mm), kích thước và không gian 2D/3D.
   - Gọi tool `get_levels` để biết các lớp hiện có và quyết định xem cần tạo thêm lớp mới (`create_level`) hay không.

2. CHUẨN BỊ THUỘC TÍNH:
   - Thiết lập Level, Color (0-255), Weight (0-31), Style (0-7) tương ứng với từng đối tượng kỹ thuật.

3. VẼ ĐỐI TƯỢNG (GEOMETRY & TEXT):
   - Sử dụng `draw_line`, `draw_linestring`, `draw_shape`, `draw_rectangle`, `draw_circle`, `draw_arc` để dựng hình học chính xác.
   - Sử dụng `place_text` hoặc `place_text_node` để ghi chú kích thước hoặc nhãn mác.

4. CẬP NHẬT VÀ FIT VIEW:
   - Gọi `send_keyin(command="fit all")` để phóng to toàn màn hình khu vực vừa vẽ cho người dùng quan sát.
   - Báo cáo tóm tắt các đối tượng và tọa độ đã thực hiện.
"""
