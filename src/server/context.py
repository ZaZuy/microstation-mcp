"""
src/server/context.py
Quản lý trạng thái và cấu hình tổng quát của MicroStation MCP Server.
"""

SERVER_NAME = "microstation-v8i"
SERVER_VERSION = "1.1.0"

SERVER_INSTRUCTIONS = """
MicroStation V8i MCP Server - Hệ thống điều khiển CAD chuyên nghiệp toàn diện cho AI (59 Tools).

Bao gồm 10 nhóm công cụ:
1. HÌNH HỌC (10 tools):
   - draw_line, draw_linestring, draw_shape, draw_rectangle, draw_circle, draw_arc, draw_ellipse, draw_point, draw_bspline_curve, place_cell.
2. ĐO ĐẠC & GHI KÍCH THƯỚC (5 tools):
   - measure_distance, measure_area, dimension_linear, dimension_aligned, dimension_radius.
3. CHỈNH SỬA & BIẾN ĐỔI HÌNH HỌC (7 tools):
   - move_element, copy_element, rotate_element, scale_element, mirror_element, change_element_symbology, drop_element.
4. VĂN BẢN & TÌM KIẾM (4 tools):
   - place_text, place_text_node, find_text, replace_text.
5. KHUNG NHÌN & TRỰC QUAN (7 tools):
   - fit_view, zoom_window, pan_view, zoom_in, zoom_out, get_view_info, capture_view_image.
6. QUẢN LÝ FILE, MODEL & REFERENCE (9 tools):
   - open_design_file, save_design_file, create_new_dgn, get_models, activate_model, create_model, get_references, attach_reference, detach_reference.
7. XỬ LÝ HÀNG LOẠT (3 tools):
   - batch_draw_points, batch_draw_lines, batch_place_texts.
8. CẤU HÌNH BẢN VẼ (6 tools):
   - set_active_level, set_active_color, set_active_weight, set_active_style, create_level, set_level_display.
9. TRUY VẤN & BÓC TÁCH (6 tools):
   - get_drawing_info, get_levels, get_active_settings, scan_elements, get_element_details, delete_element_by_id.
10. LỆNH CAD TRỰC TIẾP (2 tools):
   - send_keyin, run_keyin_script.

RESOURCES:
- ms://drawing/info: Trạng thái và metadata bản vẽ DGN đang mở.
- ms://drawing/levels: Toàn bộ danh sách level/layer.
- ms://drawing/settings: Thuộc tính nét vẽ active hiện tại.

PROMPTS:
- cad_drawing_workflow: Quy trình thiết kế bản vẽ kỹ thuật chuẩn mực.
- element_inspection: Quy trình kiểm toán và phân tích chất lượng bản vẽ.
"""
