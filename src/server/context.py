"""
src/server/context.py
Quản lý trạng thái và cấu hình tổng quát của MicroStation MCP Server.
"""

SERVER_NAME = "microstation-v8i"
SERVER_VERSION = "2.0.0"

SERVER_INSTRUCTIONS = """
MicroStation V8i MCP Server — Hệ thống điều khiển CAD & Tự động hóa bản vẽ chuyên nghiệp cho AI.
Hỗ trợ kiến trúc Dual-Mode: Named Pipe MDL Native (tốc độ cao ~0.1ms) và COM Fallback (tự động chuyển đổi).

═══════════════════════════════════════════════════════════════════════════════
  QUY TẮC BẮT BUỘC KHI LÀM VIỆC VỚI MICROSTATION (GOLDEN RULES FOR CAD AI)
═══════════════════════════════════════════════════════════════════════════════

1. CHIẾN LƯỢC VẼ TỐC ĐỘ CAO (HIỆU QUẢ GẤP 50 LẦN):
   - TUYỆT ĐỐI KHÔNG gọi lắt nhắt từng tool riêng lẻ (draw_line, draw_circle,...) khi vẽ từ 2 đối tượng trở lên.
   - BẮT BUỘC sử dụng công cụ tổng lực:
     • `cad_draw_workflow`: Công cụ trọn gói tốt nhất (Setup môi trường -> Vẽ hàng loạt -> Tự động Fit View).
     • `batch_draw_elements`: Vẽ hàng chục/hàng trăm đối tượng trong 1 round-trip duy nhất (Tự động chuyển đổi Native Pipe hoặc COM Fallback).

2. BẢNG MÃ MÀU CHUẨN MICROSTATION (COLOR INDEX 0 - 255):
   • 0 = Trắng / Đen (White/Black - tương phản với màu nền)
   • 1 = Xanh dương (Blue)
   • 2 = Xanh lá cây (Green)
   • 3 = Đỏ (Red)
   • 4 = Vàng (Yellow)
   • 5 = Tím (Magenta)
   • 6 = Cam (Orange)
   • 7 = Xanh lơ (Cyan)

3. QUY CHUẨN BẢN ĐỒ ĐỊA CHÍNH VIỆT NAM (THÔNG TƯ 25/2014/TT-BTNMT):
   • Ranh giới thửa đất: Level `RanhDat` (hoặc Level 10), Color `3` (Đỏ), Weight `2`, Style `0` (Solid).
   • Nhãn Số thửa đất: Level `SoThua` (hoặc Level 11), Color `0` (Trắng), Height `2.0 - 2.5m`.
   • Nhãn Diện tích / Loại đất: Level `LoaiDat` (hoặc Level 12), Color `2` (Xanh lá), Height `1.5 - 2.0m`.
   • Tim đường / Chỉ giới quy hoạch: Level `ChiGioi` (hoặc Level 20), Color `4` (Vàng), Style `3` (Gạch chấm).

4. QUẢN LÝ TỌA ĐỘ VÀ KHUNG NHÌN:
   • Luôn gọi `get_model_snapshot()` trước khi vẽ để nắm bắt tọa độ hiện tại của bản vẽ (tránh vẽ ở gốc 0,0 nếu bản vẽ đang ở tọa độ thực địa VN-2000).
   • Sau khi vẽ xong, LUÔN gọi `fit_view()` (hoặc để `fit_view_after=True` trong `cad_draw_workflow`) để người dùng nhìn thấy sản phẩm ngay lập tức.
"""

