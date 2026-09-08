# Danh Mục Tính Năng Toàn Diện (62 Tools)

MCP Server cung cấp đầy đủ **62 công cụ CAD chuyên nghiệp**, chia thành 10 nhóm tính năng:

---

## 1. Nhóm Vẽ Hình Học (10 Tools - `src/tools/drawing.py`)
- `draw_line(x1, y1, x2, y2, z1=0.0, z2=0.0, level, color, weight, style)`: Vẽ đoạn thẳng giữa 2 điểm.
- `draw_linestring(points, level, color, weight, style)`: Vẽ đường gấp khúc (polyline) qua mảng đỉnh.
- `draw_shape(points, filled, fill_color, level, color, weight, style)`: Vẽ đa giác khép kín (có tùy chọn tô màu).
- `draw_rectangle(x, y, width, height, rotation_deg, filled, fill_color, level, color, weight, style)`: Vẽ hình chữ nhật.
- `draw_circle(cx, cy, radius, cz=0.0, filled, fill_color, level, color, weight, style)`: Vẽ đường tròn.
- `draw_arc(cx, cy, radius, start_angle_deg, sweep_angle_deg, cz=0.0, level, color, weight, style)`: Vẽ cung tròn.
- `draw_ellipse(cx, cy, primary_radius, secondary_radius, rotation_deg, cz=0.0, filled, fill_color, level, color, weight, style)`: Vẽ hình elip.
- `draw_point(x, y, z=0.0, level, color, weight=5)`: Vẽ điểm mốc / Point Marker.
- `draw_bspline_curve(points, level, color, weight, style)`: Vẽ đường cong trơn (Curve/Spline).
- `place_cell(cell_name, x, y, scale=1.0, rotation_deg=0.0, level)`: Chèn khối block/cell từ thư viện.
- `create_region(method, seed_x, seed_y, element_ids, fill_type, fill_color, outline_color, level, keep_original, auto_enable_view_fill)`: Tạo vùng kín và đổ màu nền toàn diện (Flood, Union, Intersection, Difference).
- `flood_fill_region(seed_x, seed_y, fill_color=4, fill_type='opaque', outline_color, level)`: Tự động đổ màu kín vào diện tích thửa đất từ tọa độ điểm hạt giống (Create Region Flood).

---

## 2. Nhóm Đo Đạc & Kích Thước (5 Tools - `src/tools/dimension.py`)
- `measure_distance(x1, y1, x2, y2, z1=0.0, z2=0.0)`: Đo khoảng cách 2D, 3D, độ dời dX, dY, dZ, góc dốc và góc phương vị giữa 2 điểm.
- `measure_area(points)`: Tính toán diện tích (m2, ha) và chu vi của đa giác từ danh sách đỉnh.
- `dimension_linear(x1, y1, x2, y2, offset=5.0, level, color, text_height=2.0)`: Ghi kích thước thẳng (ngang / dọc / xiên).
- `dimension_aligned(x1, y1, x2, y2, offset=3.0, level, color)`: Ghi kích thước song song với đoạn thẳng.
- `dimension_radius(cx, cy, radius, angle_deg=45.0, level, color)`: Ghi chú kích thước bán kính R=...

---

## 3. Nhóm Chỉnh Sửa & Biến Đổi Hình Học (8 Tools - `src/tools/modify.py`)
- `move_element(element_id, dx, dy, dz=0.0)`: Di chuyển phần tử theo vector.
- `copy_element(element_id, dx, dy, dz=0.0)`: Sao chép (clone) phần tử sang vị trí mới.
- `rotate_element(element_id, origin_x, origin_y, angle_deg)`: Xoay phần tử quanh tâm.
- `scale_element(element_id, origin_x, origin_y, scale_factor)`: Phóng to / thu nhỏ phần tử quanh điểm gốc.
- `mirror_element(element_id, p1_x, p1_y, p2_x, p2_y, copy=False)`: Lấy đối xứng phần tử qua trục 2 điểm.
- `fill_element(element_id, fill_color=4, level=None, keep_original=True)`: Đổ màu trực tiếp cho một thửa đất hoặc đối tượng kín theo ID.
- `change_element_symbology(element_id, level, color, weight, style, filled, fill_color)`: Cập nhật thuộc tính phần tử (kèm màu tô Fill) theo ID.
- `drop_element(element_id)`: Phân rã / phá khối (Drop/Explode) cell hoặc complex element.

---

## 4. Nhóm Văn Bản & Ghi Chú (4 Tools - `src/tools/text.py`)
- `place_text(text, x, y, height=2.5, width=None, rotation_deg=0.0, level, color, weight)`: Đặt text một dòng.
- `place_text_node(lines, x, y, height=2.5, rotation_deg=0.0, level, color)`: Đặt khối text nhiều dòng.
- `find_text(keyword, case_sensitive=False)`: Tìm kiếm vị trí và ID các phần tử text chứa từ khóa.
- `replace_text(find_str, replace_with, case_sensitive=False)`: Tìm và thay thế chuỗi text trong bản vẽ.

---

## 5. Nhóm Khung Nhìn & Hiển Thị (7 Tools - `src/tools/view.py`)
- `fit_view(view_number=1)`: Căn toàn màn hình (Fit View 1-8).
- `zoom_window(min_x, min_y, max_x, max_y, view_number=1)`: Phóng to vào vùng chữ nhật xác định.
- `pan_view(dx, dy, view_number=1)`: Dời góc nhìn khung nhìn theo khoảng cách dX, dY.
- `zoom_in(factor=2.0, view_number=1)`: Phóng to khung nhìn theo hệ số.
- `zoom_out(factor=2.0, view_number=1)`: Thu nhỏ khung nhìn theo hệ số.
- `get_view_info(view_number=1)`: Đọc thông tin tọa độ gốc, kích thước vùng hiển thị của View.
- `capture_view_image(output_path, view_number=1)`: Chụp ảnh màn hình bản vẽ lưu ra file PNG/JPG.

---

## 6. Nhóm Quản Lý File, Model & Reference (9 Tools - `src/tools/file_model.py`)
- `open_design_file(file_path, read_only=False)`: Mở một file DGN bất kỳ trên đĩa.
- `save_design_file()`: Lưu file DGN đang mở.
- `create_new_dgn(new_file_path, seed_file_path=None)`: Tạo file DGN mới từ seed file.
- `get_models()`: Liệt kê tất cả các Model trong file DGN.
- `activate_model(model_name)`: Chuyển sang Model khác trong cùng file DGN.
- `create_model(model_name, description="", is_3d=False)`: Tạo Model mới (Design/Sheet).
- `get_references()`: Liệt kê danh sách các file Reference (Xref) đính kèm.
- `attach_reference(file_path, model_name="Default", logical_name=None)`: Đính kèm file tham chiếu.
- `detach_reference(logical_name)`: Gỡ bỏ file tham chiếu.

---

## 7. Nhóm Xử Lý Hàng Loạt (3 Tools - `src/tools/batch.py`)
- `batch_draw_points(points, level, color, weight=5)`: Vẽ hàng loạt điểm mốc từ danh sách tọa độ.
- `batch_draw_lines(lines, level, color, weight, style)`: Vẽ hàng loạt đoạn thẳng từ danh sách cặp điểm.
- `batch_place_texts(items, level, color, default_height=2.5)`: Đặt hàng loạt nhãn chữ.

---

## 8. Nhóm Cấu Hình Bản Vẽ (6 Tools - `src/tools/settings.py`)
- `set_active_level(level_name)`: Đổi Level đang hoạt động.
- `set_active_color(color_index)`: Đổi màu hiện hành (0-255).
- `set_active_weight(weight)`: Đổi độ dày nét hiện hành (0-31).
- `set_active_style(style_index)`: Đổi kiểu nét hiện hành (0-7).
- `create_level(level_name)`: Tạo Level mới nếu chưa có.
- `set_level_display(level_name, is_displayed=True, view_number=None)`: Bật/Tắt hiển thị (Layer On/Off).

---

## 9. Nhóm Truy Vấn & Kiểm Tra (6 Tools - `src/tools/query.py`)
- `get_drawing_info()`: Lấy tên file, model, đơn vị Master Unit, số lượng phần tử.
- `get_levels()`: Lấy danh sách toàn bộ Level trong file DGN.
- `get_active_settings()`: Lấy thuộc tính active hiện tại.
- `scan_elements(level=None, element_type=None, max_count=300)`: Quét phần tử có bộ lọc theo layer hoặc loại hình học.
- `get_element_details(element_id)`: Lấy đầy đủ thông số hình học, Bounding Box Range [min_x, min_y, max_x, max_y] và thuộc tính chi tiết theo ID.
- `delete_element_by_id(element_id)`: Xóa một phần tử theo ID.

---

## 10. Nhóm Lệnh CAD Trực Tiếp (2 Tools - `src/tools/keyin.py`)
- `send_keyin(command)`: Gửi câu lệnh Key-in bất kỳ vào MicroStation.
- `run_keyin_script(commands)`: Chạy chuỗi kịch bản gồm nhiều lệnh Key-in tuần tự.

---

## 11. Resources & Prompts
- **Resources:** `ms://drawing/info`, `ms://drawing/levels`, `ms://drawing/settings`.
- **Prompts:** `cad_drawing_workflow`, `element_inspection`.
