# Hướng Dẫn Dành Cho AI Agent (AGENTS.md)

Tài liệu này cung cấp các nguyên tắc hành vi, quy chuẩn kỹ thuật và chuỗi hành động tối ưu cho các AI Agent (Antigravity, Claude, Cursor, v.v.) khi kết nối và tương tác với MicroStation V8i thông qua MCP Server (62 công cụ).

---

## 1. Nguyên Tắc Cốt Lõi (Prime Directives)

1. **Kiểm Tra Trạng Thái Trước Khi Hành Động:**
   - Luôn luôn gọi `get_drawing_info` (hoặc đọc Resource `ms://drawing/info`) trước tiên để xác định:
     - Tên file bản vẽ đang mở.
     - Hệ đơn vị của bản vẽ (`Master Unit`: mét `m`, milimet `mm`, v.v.).
     - Loại không gian đồ họa (2D hay 3D).
2. **Không Tự Ý Đoán Đơn Vị:**
   - Mọi kích thước hình học truyền vào các tool (`draw_line`, `draw_rectangle`, `draw_circle`, `place_text`) phải theo đơn vị thực của bản vẽ (Master Unit).
   - Ví dụ: Nếu bản vẽ có đơn vị là `m`, khoảng cách 10.5m là `10.5`. Nếu đơn vị là `mm`, khoảng cách đó phải là `10500`.
3. **Phân Lớp Rõ Ràng (Level Separation):**
   - Đặt đối tượng vào đúng Level chuyên trách (ví dụ: `TimDuong`, `RanhGioi`, `GhiChu`, `KhungTen`).
   - Nếu level chưa tồn tại, hãy dùng `create_level` hoặc truyền trực tiếp tên level vào tham số `level` của các hàm vẽ (hệ thống sẽ tự động khởi tạo level nếu chưa có).
4. **Trực Quan Hóa Sau Khi Vẽ (Auto-fit & Capture):**
   - Sau khi hoàn thành một loạt thao tác dựng hình, hãy gọi `fit_view(1)` để cửa sổ MicroStation tự động căn chỉnh và hiển thị toàn bộ đối tượng vừa vẽ lên màn hình cho người dùng kiểm tra.
   - Khi cần xem trực quan hình ảnh bản vẽ, gọi `capture_view_image("D:\\output.png")` để xuất ảnh xem trước.
### 5. Tuyệt Đối Không Chạy Script Can Thiệp COM Ngoài MCP:
   - Toàn bộ giao tiếp với MicroStation V8i PHẢI thông qua 62 công cụ MCP có sẵn.
   - KHÔNG viết/chạy các đoạn mã Python/PowerShell ngoài (`win32com`, `GetActiveObject`, v.v.) vì MCP Server đang giữ quyền kết nối COM độc quyền, việc chạy ngoài sẽ gây lỗi phân quyền và làm chậm tiến trình.

### 6. Quy Trình Tạo Region / Đổ Màu Nhanh (Fast Region & Fill):
Khi nhận yêu cầu tạo Region hoặc đổ màu cho thửa đất/vùng kín:
1. **Lấy điểm Seed nhanh:**
   - KHÔNG quét toàn bộ bản vẽ (`scan_elements` tổng quát).
   - Chỉ gọi `scan_elements(element_type="TextNode")` hoặc `element_type="Text"` để lấy ngay tọa độ của nhãn số thửa đất (nhãn luôn nằm trong lòng thửa) làm `seed_x, seed_y`.
2. **Thực thi ngay:**
   - Gọi thẳng `create_region(method="flood", seed_x=..., seed_y=..., fill_color=...)` hoặc `flood_fill_region(...)`.
3. **Trực quan hóa:**
   - Gọi `fit_view(1)` hoặc `zoom_window` để người dùng thấy kết quả ngay lập tức.

- **Bảng chỉ số màu chuẩn MicroStation V8i (Color Table):**
  + Màu 0: Trắng / Đen (White / Black, RGB: 255, 255, 255)
  + Màu 1: Xanh dương (Blue)
  + Màu 2: Xanh lá cây (Green)
  + Màu 3: Đỏ (Red)
  + Màu 4: **Vàng (Yellow, RGB: 255, 255, 0)**
  + Màu 5: Tím hồng (Magenta)
  + Màu 6: Cam / Nâu (Orange / Brown)
  + Màu 7: Xanh lơ / Cyan (Xanh ngọc / lục lam)
  *(Lưu ý: Khi người dùng yêu cầu "màu vàng", luôn dùng `fill_color=4` chuẩn MicroStation [RGB: 255, 255, 0]).*
---

## 2. Bản Đồ 10 Nhóm Công Cụ (64 Tools)

| Nhóm Tính Năng | Số lượng | Danh Sách Tools Tiêu Biểu |
|---|---|---|
| **1. Hình học** | 13 | `draw_line`, `draw_linestring`, `draw_shape`, `draw_rectangle`, `draw_circle`, `draw_arc`, `draw_ellipse`, `draw_point`, `draw_bspline_curve`, `place_cell`, `create_region`, `flood_fill_region`, `copy_reference_parcel` |
| **2. Đo đạc & Kích thước** | 8 | `measure_distance`, `measure_area`, `compare_parcels`, `analyze_parcel_overlap`, `create_final_parcel`, `dimension_linear`, `dimension_aligned`, `dimension_radius` |
| **3. Chỉnh sửa & Biến đổi** | 8 | `move_element`, `copy_element`, `rotate_element`, `scale_element`, `mirror_element`, `fill_element`, `change_element_symbology`, `drop_element` |
| **4. Văn bản & Tìm kiếm** | 4 | `place_text`, `place_text_node`, `find_text`, `replace_text` |
| **5. Khung nhìn (Views)** | 7 | `fit_view`, `zoom_window`, `pan_view`, `zoom_in`, `zoom_out`, `get_view_info`, `capture_view_image` |
| **6. Quản lý File, Model & Ref** | 11 | `open_design_file`, `save_design_file`, `create_new_dgn`, `get_models`, `activate_model`, `create_model`, `get_references`, `attach_reference`, `detach_reference`, `scan_reference_elements`, `get_reference_levels` |
| **7. Xử lý hàng loạt** | 3 | `batch_draw_points`, `batch_draw_lines`, `batch_place_texts` |
| **8. Cấu hình bản vẽ** | 6 | `set_active_level`, `set_active_color`, `set_active_weight`, `set_active_style`, `create_level`, `set_level_display` |
| **9. Truy vấn & Bóc tách** | 6 | `get_drawing_info`, `get_levels`, `get_active_settings`, `scan_elements`, `get_element_details`, `delete_element_by_id` |
| **10. Lệnh CAD trực tiếp** | 2 | `send_keyin`, `run_keyin_script` |


---

## 3. Các Tác Vụ Mẫu Điển Hình

### A. Vẽ và đo đạc trắc địa từ số liệu khảo sát:
1. Dùng `batch_draw_points` để chấm toàn bộ tọa độ tim mốc.
2. Dùng `batch_place_texts` để đặt tên các mốc tương ứng.
3. Dùng `draw_linestring` hoặc `draw_shape` nối ranh giới.
4. Dùng `measure_area(element_id=...)` để tính toán diện tích thửa đất.
5. Dùng `fit_view(1)` để căn vừa màn hình.

### B. Hiệu chỉnh và biên tập bản đồ:
1. Dùng `find_text` tìm các vị trí ghi chú cần sửa.
2. Dùng `replace_text` hoặc `change_element_symbology` để đổi font hoặc màu.
3. Dùng `move_element` hoặc `rotate_element` để định vị lại các đối tượng bị lệch.
4. Dùng `save_design_file` để lưu lại.

### C. Tạo Region và Đổ màu nhanh (Fast Flood & Fill):
1. Dùng `find_text(keyword="...", search_references=True)` hoặc `scan_elements(element_type="Cell", min_x=..., max_x=...)` để lấy tọa độ hạt giống (Seed Point) trong lòng thửa đất.
2. Dùng `create_region(method="flood", seed_x=..., seed_y=..., fill_color=...)` để đổ màu kín vùng ranh giới.
3. Dùng `zoom_window` hoặc `fit_view(1)` để căn chuẩn màn hình hiển thị cho người dùng.

### D. Trích xuất ranh thửa từ file Reference tại chỗ (Zero-file-switching):
1. Dùng `copy_reference_parcel(seed_x=..., seed_y=..., target_level="Level 11", fill_color=3)` để tự động đọc file tham chiếu trong bộ nhớ nền và khép kín thành Shape khép kín mà không cần chuyển đổi file.

### E. So sánh 2 thửa đất (Hiện trạng vs Trích lục quy hoạch/địa chính):
1. Dùng `compare_parcels(element_id_1="...", element_id_2="...")` để nhận bảng phân tích độ lệch diện tích ($\Delta S$), chu vi ($\Delta P$), độ lệch tâm và sai số ranh giới lớn nhất.

### F. Tự động bóc tách chênh lệch thửa đất với Reference (Fast 1-Click):
Khi nhận yêu cầu: *"Tự động tìm thửa đất trong file reference đang đè trùng với thửa đất trên file hiện tại của tôi. Phần diện tích trùng nhau thì để rỗng không tô màu none, bóc tách các mẩu thừa/thiếu ra 2 màu riêng biệt và đánh số diện tích cho từng mẩu đó"*
1. **GỌI DUY NHẤT:** `analyze_parcel_overlap(fill_mode="outline", auto_label=True)`
2. Tool sẽ tự động xử lý 100% trong bộ nhớ ngầm, không mở đổi file, không chuyển view, vẽ các mẩu Dư (Vàng) và Thiếu (Đỏ), giữ rỗng phần trùng, và ghi nhãn diện tích m² siêu tốc.

### G. Tạo thửa T3 kết quả cuối cùng (Chỉ 1 đường ngoài cùng, xóa sạch line thừa bên trong):
Khi người dùng yêu cầu: *"vẽ thửa t3 là kết quả còn lại của 2 thửa đó. chỉ lấy 1 line ngoài cùng nếu trong line thì xóa hết"*
1. **GỌI DUY NHẤT:** `create_final_parcel(delete_inner_elements=True, auto_label=True)`
2. Tool sẽ tự động hợp nhất ranh giới ngoài cùng thành 1 LineString duy nhất, xóa sạch mọi đường line/text thừa bên trong và ghi nhãn diện tích.


