"""
src/server/context.py
Quản lý trạng thái và cấu hình tổng quát của MicroStation MCP Server.
Chuẩn hóa theo kiến trúc 8 Consolidated Tools (AutoCAD MCP v3.1 pattern).
"""

SERVER_NAME = "microstation-v8i"
SERVER_VERSION = "3.0.0"

SERVER_INSTRUCTIONS = """
MicroStation V8i MCP Server v3.0 — Hệ thống điều khiển CAD & Tự động hóa bản vẽ chuyên nghiệp cho AI.
Hỗ trợ kiến trúc Dual-Mode (Named Pipe MDL Native & COM Fallback) với 8 CÔNG CỤ HỢP NHẤT:
  1. drawing: Quản lý tệp DGN, Model, Reference, Undo/Redo.
  2. entity: Toàn bộ CRUD đối tượng (Line, Linestring, Shape, Circle, Arc, Text, Batch...).
  3. layer: Quản lý lớp bản vẽ (Level).
  4. cell: Quản lý Cell/Block kỹ thuật.
  5. annotation: Ghi chú chữ, kích thước (Dimension), tìm kiếm và thay thế text.
  6. view: Căn khung nhìn (fit_view, zoom_window) và CHỤP ẢNH MÀN HÌNH BẢN VẼ (get_screenshot).
  7. cadastral: CHUYÊN GIA ĐỊA CHÍNH VIỆT NAM (TT 26/2024/TT-BTNMT & TT 23/2025/TT-BNNMT):
     • auto_workflow: Giải quyết trọn gói: phân tách ranh thửa nét liền L10, ranh xin chuyển mục đích (CMD) nét đứt L10,
       ranh lộ giới (LGQH) L50; tính diện tích từng vùng; điền diện tích lộ giới; ghi nhãn tâm "Vị trí xin CMD";
       đánh số thứ tự mốc ranh 1, 2, 3...; ghi kích thước chiều dài từng cạnh; tự động dựng Bảng tọa độ VN-2000.
     • draw_table, draw_parcel_label, analyze...
  8. system: Trạng thái kết nối (status), thực thi lệnh key-in (execute_keyin), và THỰC THI CODE PYTHON NỘI BỘ (execute_python).

═══════════════════════════════════════════════════════════════════════════════
  QUY TẮC BẮT BUỘC DÀNH CHO AI (GOLDEN RULES FOR CAD AI)
═══════════════════════════════════════════════════════════════════════════════

1. TUYỆT ĐỐI KHÔNG MỞ TERMINAL CHẠY LỆNH PYTHON (TRÁNH LỖI VÀ LOOP VÔ TẬN):
   - Môi trường terminal ngoài không có thư viện pywin32, win32com hoặc trỏ sai Python.
   - Khi cần chạy một đoạn code xử lý phức tạp hoặc truy vấn COM tùy biến, BẮT BUỘC gọi tool:
     `system(operation="execute_python", data={"code": "..."})`
     Server MCP sẽ thực thi an toàn ngay bên trong tiến trình (đã có sẵn bridge, app, model, shapely, math...).

2. ƯU TIÊN SỬ DỤNG CÔNG CỤ CẤP CAO:
   - Nghiệp vụ địa chính / thửa đất: Dùng ngay `cadastral(operation="auto_workflow")` để hoàn thành bài toán trong 1 lượt gọi.
   - Vẽ nhiều đối tượng kỹ thuật: Dùng `entity(operation="batch_create", data={"elements": [...]})`.

3. QUY CHUẨN BẢN ĐỒ ĐỊA CHÍNH VIỆT NAM (THÔNG TƯ 26/2024/TT-BTNMT):
   - Ranh giới thửa đất hiện trạng: Level 10, Color 0 (Đen/Trắng), Weight 0-1, Style 0 (Nét liền).
   - Ranh thửa đất pháp lý: Level 61, Color 3 (Đỏ), Weight 1, Style 0.
   - Ranh vị trí chuyển mục đích (CMD): Level 10, Style 2 (Nét đứt).
   - Chỉ giới đường quy hoạch / lộ giới: Level 50, Color 3 (Đỏ), Style 2 (Nét đứt).
   - Nhãn thửa đất (STT, Diện tích, Loại đất): Level 13, Level 4, Level 2, Color 4 (Vàng).
   - Khung bản đồ, bảng tọa độ góc ranh: Level 63 hoặc Level 13, Color 0.

4. PHẢN HỒI TRỰC QUAN (VISUAL AUDIT):
   - Sau khi vẽ xong, luôn gọi `view(operation="fit_view")`.
   - Có thể truyền `include_screenshot=True` trên các tool để nhận ngay ảnh chụp màn hình bản vẽ đối soát.
"""
