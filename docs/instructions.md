# Hướng Dẫn Hệ Thống Cho LLM (Instructions)

Khi kết nối với MicroStation V8i MCP Server, mô hình ngôn ngữ lớn (LLM) cần tuân thủ các chỉ dẫn sau:

1. **Điều Kiện Cần:**
   - Ứng dụng MicroStation V8i phải đang được bật trên máy tính Windows.
   - Một file thiết kế `.dgn` phải được mở trong phiên làm việc. Nếu chưa có file nào mở, server sẽ trả về lỗi yêu cầu người dùng mở file trước.

2. **Quy Tắc Đơn Vị Kỹ Thuật (Master Unit):**
   - MicroStation sử dụng hệ tọa độ thực theo đơn vị đã thiết lập trong file (Master Unit - thường là mét `m` đối với bản đồ địa chính/giao thông, hoặc milimét `mm` đối với cơ khí/kiến trúc).
   - Trước khi thực hiện bất kỳ lệnh vẽ nào, gọi `get_drawing_info` để biết chính xác đơn vị là gì và scale tọa độ phù hợp.

3. **Thuộc Tính Nét Vẽ (Symbology):**
   - Level: Tên lớp (chuỗi).
   - Color: Số nguyên từ 0 đến 255 (bảng màu chuẩn MicroStation).
   - Weight: Số nguyên từ 0 đến 31 (độ đậm nét).
   - Style: Số nguyên từ 0 đến 7 (0: Solid, 1: Dotted, 2: Medium Dash, 3: Long Dash, 4: Dot-Dash, 5: Short Dash, 6: Dash-Dot-Dot, 7: Long-Short Dash).

4. **Trực Quan Hóa (Feedback):**
   - Sau khi kết thúc thao tác vẽ, luôn dùng `send_keyin(command="fit all")` để người dùng thấy ngay kết quả trên cửa sổ MicroStation.
