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

---

## 2. Bản Đồ 10 Nhóm Công Cụ (62 Tools)

| Nhóm Tính Năng | Số lượng | Danh Sách Tools Tiêu Biểu |
|---|---|---|
| **1. Hình học** | 12 | `draw_line`, `draw_linestring`, `draw_shape`, `draw_rectangle`, `draw_circle`, `draw_arc`, `draw_ellipse`, `draw_point`, `draw_bspline_curve`, `place_cell`, `create_region`, `flood_fill_region` |
| **2. Đo đạc & Kích thước** | 5 | `measure_distance`, `measure_area`, `dimension_linear`, `dimension_aligned`, `dimension_radius` |
| **3. Chỉnh sửa & Biến đổi** | 8 | `move_element`, `copy_element`, `rotate_element`, `scale_element`, `mirror_element`, `fill_element`, `change_element_symbology`, `drop_element` |
| **4. Văn bản & Tìm kiếm** | 4 | `place_text`, `place_text_node`, `find_text`, `replace_text` |
| **5. Khung nhìn (Views)** | 7 | `fit_view`, `zoom_window`, `pan_view`, `zoom_in`, `zoom_out`, `get_view_info`, `capture_view_image` |
| **6. Quản lý File & Model** | 9 | `open_design_file`, `save_design_file`, `create_new_dgn`, `get_models`, `activate_model`, `create_model`, `get_references`, `attach_reference`, `detach_reference` |
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
4. Dùng `measure_area` để tính toán diện tích thửa đất.
5. Dùng `fit_view(1)` để căn vừa màn hình.

### B. Hiệu chỉnh và biên tập bản đồ:
1. Dùng `find_text` tìm các vị trí ghi chú cần sửa.
2. Dùng `replace_text` hoặc `change_element_symbology` để đổi font hoặc màu.
3. Dùng `move_element` hoặc `rotate_element` để định vị lại các đối tượng bị lệch.
4. Dùng `save_design_file` để lưu lại.
