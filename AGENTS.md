# Hướng Dẫn Dành Cho AI Agent (AGENTS.md)

Tài liệu này cung cấp các nguyên tắc hành vi, quy chuẩn kỹ thuật và chuỗi hành động tối ưu cho các AI Agent (Antigravity, Claude, Cursor, v.v.) khi kết nối và tương tác với MicroStation V8i thông qua MCP Server (118 công cụ CAD nguyên thủy tương ứng đầy đủ các Tool Boxes của MicroStation V8i).

---

## 1. Nguyên Tắc Cốt Lõi (Prime Directives)

1. **Phân Định Rõ Ràng: AI Là Bộ Não - MCP Server Là Bàn Tay:**
   - **AI Agent đóng vai trò là BỘ NÃO (Brain):** Đảm nhiệm toàn bộ việc tư duy, tính toán tọa độ, phân tích hình học, ra quyết định và lập kế hoạch vẽ.
   - **MCP Server đóng vai trò là BÀN TAY (Hands):** Cung cấp các API CAD nguyên thủy (Primitives), tương tác 1:1 trực tiếp với MicroStation V8i COM mà không chứa bất kỳ thuật toán tự chế nào bên trong.
2. **Kiểm Tra Trạng Thái Trước Khi Hành Động:**
   - Luôn luôn gọi `get_drawing_info` (hoặc đọc Resource `ms://drawing/info`) trước tiên để xác định:
     - Tên file bản vẽ đang mở.
     - Hệ đơn vị của bản vẽ (`Master Unit`: mét `m`, milimet `mm`, v.v.).
     - Loại không gian đồ họa (2D hay 3D).
3. **Không Tự Ý Đoán Đơn Vị:**
   - Mọi kích thước hình học truyền vào các tool (`draw_line`, `draw_rectangle`, `draw_circle`, `place_text`) phải theo đơn vị thực của bản vẽ (Master Unit).
   - Ví dụ: Nếu bản vẽ có đơn vị là `m`, khoảng cách 10.5m là `10.5`. Nếu đơn vị là `mm`, khoảng cách đó phải là `10500`.
4. **Phân Lớp Rõ Ràng (Level Separation):**
   - Đặt đối tượng vào đúng Level chuyên trách (ví dụ: `TimDuong`, `RanhGioi`, `GhiChu`, `KhungTen`).
   - Nếu level chưa tồn tại, hãy dùng `create_level` hoặc truyền trực tiếp tên level vào tham số `level` của các hàm vẽ (hệ thống sẽ tự động khởi tạo level nếu chưa có).
5. **Trực Quan Hóa Sau Khi Vẽ (Auto-fit & Capture):**
   - Sau khi hoàn thành một loạt thao tác dựng hình, hãy gọi `fit_view(1)` để cửa sổ MicroStation tự động căn chỉnh và hiển thị toàn bộ đối tượng vừa vẽ lên màn hình cho người dùng kiểm tra.
   - Khi cần xem trực quan hình ảnh bản vẽ, gọi `capture_view_image("D:\\output.png")` để xuất ảnh xem trước.
6. **Tuyệt Đối Không Chạy Script Can Thiệp COM Ngoài MCP:**
   - Toàn bộ giao tiếp với MicroStation V8i PHẢI thông qua 118 công cụ MCP nguyên thủy có sẵn.
   - KHÔNG viết/chạy các đoạn mã Python/PowerShell ngoài (`win32com`, `GetActiveObject`, v.v.) vì MCP Server đang giữ quyền kết nối COM độc quyền.
7. **Bảng Chỉ Số Màu Chuẩn MicroStation V8i (Color Table):**
   - Màu 0: Trắng / Đen (White / Black, RGB: 255, 255, 255)
   - Màu 1: Xanh dương (Blue)
   - Màu 2: Xanh lá cây (Green)
   - Màu 3: Đỏ (Red)
   - Màu 4: **Vàng (Yellow, RGB: 255, 255, 0)**
   - Màu 5: Tím hồng (Magenta)
   - Màu 6: Cam / Nâu (Orange / Brown)
   - Màu 7: Xanh lơ / Cyan (Xanh ngọc / lục lam)

---

## 2. Bản Đồ 16 Nhóm Công Cụ CAD Nguyên Thủy (118 Tools - Phủ Kín Tool Boxes MicroStation V8i)

| Nhóm Tool Box MicroStation | Số lượng | Danh Sách Tools CAD Nguyên Thủy (1:1 COM & Key-in) |
|---|:---:|---|
| **1. Linear Elements, Polygons, Circles, Curves (Drawing)** | **21** | `draw_line`, `draw_linestring`, `draw_shape`, `draw_rectangle`, `draw_circle`, `draw_arc`, `draw_ellipse`, `draw_point`, `draw_bspline_curve`, `place_cell`, `create_region`, `flood_fill_region`, `draw_smartline`, `draw_multiline`, `draw_orthogonal_shape`, `draw_regular_polygon`, `draw_half_circle`, `construct_angle_bisector`, `construct_min_distance_line`, `draw_points_along_element`, `draw_points_at_intersection` |
| **2. Measure & Dimensioning** | **9** | `measure_distance`, `measure_area`, `measure_length`, `measure_angle_between_lines`, `dimension_linear`, `dimension_aligned`, `dimension_radius`, `dimension_angular`, `dimension_element` |
| **3. Manipulate & Modify** | **21** | `move_element`, `copy_element`, `rotate_element`, `scale_element`, `mirror_element`, `fill_element`, `change_element_symbology`, `drop_element`, `move_parallel`, `construct_circular_fillet`, `construct_chamfer`, `extend_line`, `extend_to_intersection`, `trim_element`, `insert_vertex`, `delete_vertex`, `delete_part_of_element`, `array_rectangular`, `array_polar`, `align_elements`, `drop_complex` |
| **4. Text & Annotations** | **4** | `place_text`, `place_text_node`, `find_text`, `replace_text` |
| **5. View Control** | **8** | `fit_view`, `zoom_window`, `pan_view`, `zoom_in`, `zoom_out`, `get_view_info`, `capture_view_image`, `rotate_view` |
| **6. Files, Models & References (Xrefs)** | **14** | `open_design_file`, `save_design_file`, `create_new_dgn`, `get_models`, `activate_model`, `create_model`, `delete_model`, `get_references`, `attach_reference`, `detach_reference`, `scan_reference_elements`, `get_reference_levels`, `reload_reference`, `clip_reference` |
| **7. Batch Operations** | **3** | `batch_draw_points`, `batch_draw_lines`, `batch_place_texts` |
| **8. Attributes & Settings** | **7** | `set_active_level`, `set_active_color`, `set_active_weight`, `set_active_style`, `create_level`, `set_level_display`, `match_element_attributes` |
| **9. Selection, Query & Inspection** | **6** | `get_drawing_info`, `get_levels`, `get_active_settings`, `scan_elements`, `get_element_details`, `delete_element_by_id` |
| **10. Key-in & Command Engine** | **2** | `send_keyin`, `run_keyin_script` |
| **11. Raster Manager** | **4** | `attach_raster_image`, `detach_raster_image`, `fit_raster`, `set_raster_display` |
| **12. Groups & Complex Entities** | **4** | `create_complex_chain`, `create_complex_shape`, `create_graphic_group`, `ungroup_graphic_group` |
| **13. Patterning (Hatch & Crosshatch)** | **4** | `hatch_area`, `crosshatch_area`, `pattern_area`, `delete_pattern` |
| **14. Fence & Selection Sets** | **5** | `place_fence`, `clear_fence`, `modify_fence_contents`, `select_elements_by_criteria`, `clear_selection` |
| **15. Tags & Non-graphic Attributes** | **2** | `attach_tag`, `get_element_tags` |
| **16. 3D Primitives & Solids** | **4** | `draw_slab`, `draw_cylinder`, `draw_sphere`, `draw_torus` |
| **TỔNG CỘNG** | **118** | **Toàn bộ là các API CAD nguyên thủy của MicroStation V8i** |

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
1. Dùng `find_text` hoặc `scan_elements` để lấy tọa độ hạt giống (Seed Point) trong lòng thửa đất.
2. Dùng `create_region(method="flood", seed_x=..., seed_y=..., fill_color=...)` để đổ màu kín vùng ranh giới.
3. Dùng `zoom_window` hoặc `fit_view(1)` để căn chuẩn màn hình hiển thị cho người dùng.

### D. Quản lý ảnh Raster lót nền (Raster Underlay):
1. Dùng `attach_raster_image(file_path="...")` để gắn ảnh scan bản đồ lót dưới nền CAD.
2. Dùng `fit_raster(view_number=1)` để phóng vừa màn hình khớp trọn tấm ảnh raster.
3. Dùng `set_raster_display(display=False)` để tạm ẩn lớp ảnh khi chỉ muốn xem đường nét vector.
