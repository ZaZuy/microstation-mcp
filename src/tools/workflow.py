"""
src/tools/workflow.py
Công cụ điều phối cấp cao (CAD Workflow Tool) cho MicroStation V8i.
Tích hợp trọn gói chu trình: Thiết lập môi trường -> Vẽ hàng loạt -> Căn chỉnh khung nhìn (Fit View).
Lấy cảm hứng từ kiến trúc tổng lực của OfficeCLI để giảm thiểu số lượng tool calls.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional
from src.core.ms_bridge import bridge
from src.tools.dimension import _get_polygon_from_element, _calc_centroid_and_area

logger = logging.getLogger(__name__)


def register_workflow_tools(mcp):
    """Đăng ký các tool điều phối quy trình cao cấp vào MCP Server."""

    @mcp.tool
    def cad_draw_workflow(
        elements: List[Dict[str, Any]],
        active_level: Optional[str] = None,
        active_color: Optional[int] = None,
        active_weight: Optional[int] = None,
        active_style: Optional[int] = None,
        fit_view_after: bool = True,
        use_undo_group: bool = True,
    ) -> str:
        """
        **CÔNG CỤ VẼ TRỌN GÓI CAO CẤP NHẤT (ALL-IN-ONE CAD WORKFLOW)**

        Thực thi toàn bộ chu trình vẽ CAD chỉ trong một lệnh gọi duy nhất:
        1. (Tùy chọn) Thiết lập môi trường vẽ (Active Level, Color, Weight, Style).
        2. Tự động chọn kênh tối ưu: Named Pipe MDL Native (nếu sẵn sàng) hoặc COM Fallback.
        3. Vẽ đồng loạt toàn bộ danh sách `elements`.
        4. Tự động căn chỉnh toàn bộ khung nhìn (`fit_view`) để hiển thị ngay sản phẩm cho người dùng.

        Args:
            elements: Danh sách các đối tượng cần vẽ:
                - "type": "line", "polyline", "shape", "circle", "ellipse", "arc", "text", "point"
                - "line": x1, y1, z1, x2, y2, z2
                - "polyline" / "shape": points: [[x, y], [x, y, z], ...], (shape có thêm filled: bool)
                - "circle": cx, cy, cz, radius
                - "ellipse": cx, cy, cz, primary_radius, secondary_radius, rotation
                - "arc": cx, cy, cz, radius, start_angle, sweep_angle
                - "text": x, y, z, text, height, rotation
                - Thuộc tính màu/nét: level, color (0-255), weight (0-31), style (0-7)
            active_level: Tên level active chung nếu muốn đặt trước khi vẽ
            active_color: Màu active chung (0-255)
            active_weight: Độ đậm active chung (0-31)
            active_style: Kiểu nét active chung (0-7)
            fit_view_after: Tự động zoom fit view sau khi vẽ xong (Mặc định: True)
            use_undo_group: Nhóm toàn bộ thay đổi thành 1 bước Undo (Mặc định: True)

        Returns:
            JSON string tổng kết kết quả vẽ và trạng thái khung nhìn.
        """
        if not elements:
            return json.dumps({
                "success": False,
                "message": "Danh sách elements rỗng. Vui lòng truyền ít nhất 1 đối tượng cần vẽ."
            }, ensure_ascii=False)

        # 1. Thiết lập active symbology nếu được chỉ định
        try:
            app = bridge.get_app()
            if active_level is not None:
                bridge.set_active_level(active_level)
            if active_color is not None:
                app.ActiveSettings.Color = int(active_color)
            if active_weight is not None:
                app.ActiveSettings.LineWeight = int(active_weight)
            if active_style is not None:
                app.ActiveSettings.LineStyle = app.ActiveDesignFile.LineStyles.Item(int(active_style))
        except Exception as e:
            logger.warning(f"Không thể thiết lập active settings trước khi vẽ: {e}")

        # 2. Thực thi vẽ hàng loạt
        # Thử gọi qua Named Pipe trước nếu pipe_client khả dụng
        from src.core._pipe_singleton import get_pipe_client
        from src.core.pipe_client import PipeConnectionError, PipeError
        from src.tools.native_batch import _batch_draw_via_com

        pipe_client = get_pipe_client()
        result_json = None

        if pipe_client and getattr(pipe_client, "is_connected", False):
            try:
                response = pipe_client.send_command(
                    "batch_create",
                    {"elements": elements, "use_undo_group": use_undo_group},
                )
                results = response.get("results", [])
                elem_ids = [r.get("element_id") for r in results if r.get("success")]
                errors = [
                    f"Element[{i}] ({r.get('type','?')}): {r.get('message','Lỗi không xác định')}"
                    for i, r in enumerate(results) if not r.get("success")
                ]
                created = len(elem_ids)
                failed = len(elements) - created
                result_json = {
                    "success": failed == 0,
                    "total": len(elements),
                    "created": created,
                    "failed": failed,
                    "element_ids": [eid for eid in elem_ids if eid is not None],
                    "errors": errors,
                    "executed_via": "native_pipe"
                }
            except (PipeConnectionError, PipeError) as ex:
                logger.info(f"Pipe error trong workflow ({ex}), tự động fallback sang COM.")
                raw_com = _batch_draw_via_com(elements, use_undo_group)
                result_json = json.loads(raw_com)
        else:
            raw_com = _batch_draw_via_com(elements, use_undo_group)
            result_json = json.loads(raw_com)

        # 3. Fit View nếu được yêu cầu
        view_fitted = False
        if fit_view_after and result_json.get("created", 0) > 0:
            try:
                app = bridge.get_app()
                view = app.CommandState.ActiveView or app.Views(1)
                view.Fit(True)
                view.Redraw()
                view_fitted = True
            except Exception as e:
                logger.warning(f"Không thể fit view sau khi vẽ: {e}")

        result_json["view_fitted"] = view_fitted
        result_json["message"] = (
            f"Đã vẽ thành công {result_json.get('created', 0)}/{result_json.get('total', 0)} đối tượng "
            f"({'qua Named Pipe MDL' if result_json.get('executed_via') == 'native_pipe' else 'qua COM Fallback'})"
            f"{' và đã căn chỉnh khung nhìn (Fit View).' if view_fitted else '.'}"
        )

        return json.dumps(result_json, ensure_ascii=False)

    @mcp.tool
    def draw_parcel_label(
        x: float,
        y: float,
        so_thua: str,
        dien_tich: str,
        loai_dat: str,
        height: float = 2.0,
        font_name: str = ".VnArial",
    ) -> str:
        """
        Vẽ nhãn thửa địa chính chuẩn Thông tư 26/2024 dạng phân số.
        Gồm: Số thửa (trên), Diện tích (dưới), Đường gạch ngang (giữa), Loại đất (dưới cùng).

        :param x: Tọa độ X tâm nhãn thửa
        :param y: Tọa độ Y tâm nhãn thửa
        :param so_thua: Số thứ tự thửa (vd: '125')
        :param dien_tich: Diện tích (vd: '145.5')
        :param loai_dat: Ký hiệu loại đất (vd: 'ODT')
        :param height: Chiều cao chữ (mặc định 2.0 mét)
        :param font_name: Tên Font (mặc định '.VnArial' cho TCVN3)
        """
        # Tính toán kích thước đường kẻ ngang dựa trên chiều dài text lớn nhất
        max_len = max(len(str(so_thua)), len(str(dien_tich)))
        line_length = max(max_len * height * 0.7, height * 1.5)
        half_len = line_length / 2.0

        gap = height * 0.2 # Khoảng cách giữa chữ và đường kẻ

        elements = [
            # 1. Đường kẻ ngang phân số (Level 13, Màu 4)
            {
                "type": "line",
                "x1": x - half_len,
                "y1": y,
                "z1": 0.0,
                "x2": x + half_len,
                "y2": y,
                "z2": 0.0,
                "level": "13",
                "color": 4,
                "weight": 0
            },
            # 2. Số thứ tự thửa (trên gạch ngang) - Level 13
            {
                "type": "text",
                "text": str(so_thua),
                "x": x,
                "y": y + gap + height/2.0,
                "height": height,
                "level": "13",
                "color": 4,
                "font_name": font_name,
                "justification": 7  # Center-Center
            },
            # 3. Diện tích (dưới gạch ngang) - Level 4
            {
                "type": "text",
                "text": str(dien_tich),
                "x": x,
                "y": y - gap - height/2.0,
                "height": height,
                "level": "4",
                "color": 4,
                "font_name": font_name,
                "justification": 7
            },
            # 4. Loại đất (dưới cùng) - Level 2
            {
                "type": "text",
                "text": str(loai_dat),
                "x": x,
                "y": y - gap * 2 - height * 1.5,
                "height": height,
                "level": "2",
                "color": 4,
                "font_name": font_name,
                "justification": 7
            }
        ]

        return cad_draw_workflow(elements=elements, fit_view_after=False)

    @mcp.tool
    def draw_cadastral_coordinate_table(
        points: List[List[float]],
        origin_x: float,
        origin_y: float,
        title: str = "BẢNG KÊ TỌA ĐỘ GÓC RANH",
        row_height: float = 3.0,
        col_widths: Optional[List[float]] = None,
        font_name: str = ".VnArial",
        text_height: float = 1.4,
    ) -> str:
        """
        Vẽ Bảng kê tọa độ góc ranh thửa đất chuẩn mẫu Trích lục địa chính (TT 26/2024/TT-BTNMT & TT 23/2025/TT-BNNMT).
        Gồm 4 cột tiêu chuẩn:
          1. Số hiệu điểm (Đỉnh ranh 1, 2, 3...)
          2. Tọa độ X (m) (VN-2000)
          3. Tọa độ Y (m) (VN-2000)
          4. Chiều dài cạnh S (m) từ điểm i đến điểm i+1

        :param points: Danh sách tọa độ đỉnh ranh [[x1, y1], [x2, y2], ...]
        :param origin_x: Tọa độ X góc trên bên trái của Bảng kê
        :param origin_y: Tọa độ Y góc trên bên trái của Bảng kê
        :param title: Tiêu đề bảng kê (mặc định: 'BẢNG KÊ TỌA ĐỘ GÓC RANH')
        :param row_height: Chiều cao mỗi dòng (mặc định 3.0m)
        :param col_widths: Danh sách độ rộng 4 cột [W_điểm, W_X, W_Y, W_S] (mặc định: [10.0, 20.0, 20.0, 15.0])
        :param font_name: Tên font chữ (mặc định: '.VnArial')
        :param text_height: Chiều cao chữ trong bảng (mặc định: 1.4m)
        """
        import math

        if not points or len(points) < 2:
            return json.dumps({
                "success": False,
                "message": "Cần ít nhất 2 điểm tọa độ để tạo bảng kê góc ranh."
            }, ensure_ascii=False)

        # Loại bỏ điểm trùng cuối cùng nếu có
        clean_pts = []
        for p in points:
            if not clean_pts:
                clean_pts.append([float(p[0]), float(p[1])])
            else:
                if math.hypot(p[0] - clean_pts[-1][0], p[1] - clean_pts[-1][1]) > 1e-4:
                    clean_pts.append([float(p[0]), float(p[1])])
        if len(clean_pts) > 2 and math.hypot(clean_pts[0][0] - clean_pts[-1][0], clean_pts[0][1] - clean_pts[-1][1]) < 1e-4:
            clean_pts = clean_pts[:-1]

        num_pts = len(clean_pts)
        if col_widths is None or len(col_widths) < 4:
            col_widths = [10.0, 22.0, 22.0, 16.0]  # Điểm, X, Y, Cạnh S

        total_width = sum(col_widths)
        title_height = row_height * 1.5
        header_height = row_height * 1.2
        num_rows = num_pts + 1  # Cộng hàng nối về điểm 1
        table_height = title_height + header_height + (num_rows * row_height)

        elements = []

        # 1. Khung bảng ngoại vi & Khung trong (Level 63 / Level 10, Màu 0, Weight 1)
        # Đường bao ngoài
        elements.append({
            "type": "shape",
            "points": [
                [origin_x, origin_y],
                [origin_x + total_width, origin_y],
                [origin_x + total_width, origin_y - table_height],
                [origin_x, origin_y - table_height],
                [origin_x, origin_y]
            ],
            "level": "63",
            "color": 0,
            "weight": 1
        })

        # Đường ngang phân cách Tiêu đề
        y_title = origin_y - title_height
        elements.append({
            "type": "line",
            "x1": origin_x, "y1": y_title, "z1": 0.0,
            "x2": origin_x + total_width, "y2": y_title, "z2": 0.0,
            "level": "63", "color": 0, "weight": 1
        })

        # Đường ngang phân cách Header
        y_header = y_title - header_height
        elements.append({
            "type": "line",
            "x1": origin_x, "y1": y_header, "z1": 0.0,
            "x2": origin_x + total_width, "y2": y_header, "z2": 0.0,
            "level": "63", "color": 0, "weight": 1
        })

        # Các đường ngang phân cách từng hàng dữ liệu
        for r in range(1, num_rows + 1):
            y_r = y_header - (r * row_height)
            elements.append({
                "type": "line",
                "x1": origin_x, "y1": y_r, "z1": 0.0,
                "x2": origin_x + total_width, "y2": y_r, "z2": 0.0,
                "level": "63", "color": 0, "weight": 0
            })

        # Các đường dọc phân chia cột (từ y_title xuống đáy)
        cur_x = origin_x
        for w in col_widths[:-1]:
            cur_x += w
            elements.append({
                "type": "line",
                "x1": cur_x, "y1": y_title, "z1": 0.0,
                "x2": cur_x, "y2": origin_y - table_height, "z2": 0.0,
                "level": "63", "color": 0, "weight": 0
            })

        # 2. Text Tiêu đề Bảng
        elements.append({
            "type": "text",
            "text": title,
            "x": origin_x + total_width / 2.0,
            "y": origin_y - title_height / 2.0,
            "height": text_height * 1.2,
            "level": "13",
            "color": 0,
            "font_name": font_name,
            "justification": 7  # Center-Center
        })

        # 3. Text Header Cột
        col_headers = ["Điểm", "X (m)", "Y (m)", "Cạnh (m)"]
        col_centers = []
        cur_x = origin_x
        for w in col_widths:
            col_centers.append(cur_x + w / 2.0)
            cur_x += w

        for i, header_text in enumerate(col_headers):
            elements.append({
                "type": "text",
                "text": header_text,
                "x": col_centers[i],
                "y": y_title - header_height / 2.0,
                "height": text_height,
                "level": "13",
                "color": 0,
                "font_name": font_name,
                "justification": 7
            })

        # 4. Text Dữ liệu từng đỉnh ranh và chiều dài cạnh
        for i in range(num_rows):
            pt_idx = i % num_pts
            next_idx = (i + 1) % num_pts
            pt = clean_pts[pt_idx]
            next_pt = clean_pts[next_idx]

            edge_len = math.hypot(next_pt[0] - pt[0], next_pt[1] - pt[1])
            y_row_center = y_header - (i * row_height) - (row_height / 2.0)

            # Điểm số (1, 2, 3... hoặc lặp lại 1 ở hàng cuối)
            elements.append({
                "type": "text",
                "text": str(pt_idx + 1),
                "x": col_centers[0],
                "y": y_row_center,
                "height": text_height,
                "level": "13",
                "color": 4,
                "font_name": font_name,
                "justification": 7
            })

            # Tọa độ X (Làm tròn 2 hoặc 3 chữ số thập phân chuẩn trắc địa)
            elements.append({
                "type": "text",
                "text": f"{pt[0]:.2f}",
                "x": col_centers[1],
                "y": y_row_center,
                "height": text_height,
                "level": "4",
                "color": 0,
                "font_name": font_name,
                "justification": 7
            })

            # Tọa độ Y
            elements.append({
                "type": "text",
                "text": f"{pt[1]:.2f}",
                "x": col_centers[2],
                "y": y_row_center,
                "height": text_height,
                "level": "4",
                "color": 0,
                "font_name": font_name,
                "justification": 7
            })

            # Cạnh (m) từ điểm i -> điểm i+1 (nếu là hàng cuối nối về điểm 1 thì vẫn có khoảng cách)
            if i < num_pts:
                # Ghi ở khoảng giữa 2 dòng hoặc trên dòng
                elements.append({
                    "type": "text",
                    "text": f"{edge_len:.2f}",
                    "x": col_centers[3],
                    "y": y_row_center - (row_height / 2.0) if i < num_pts - 1 else y_row_center,
                    "height": text_height,
                    "level": "4",
                    "color": 4,
                    "font_name": font_name,
                    "justification": 7
                })

        return cad_draw_workflow(elements=elements, fit_view_after=False)

    @mcp.tool
    def draw_parcel_edge_dimensions(
        points: List[List[float]],
        height: float = 1.4,
        offset_dist: float = 0.8,
        font_name: str = ".VnArial",
        level: str = "13",
        color: int = 4,
    ) -> str:
        """
        Tự động tính toán chiều dài và góc xoay, ghi kích thước toàn bộ các cạnh ranh giới thửa đất.
        Text được xoay thuận chiều đọc bản vẽ và lệch ngoài ranh giới thửa đất.

        :param points: Danh sách tọa độ đỉnh ranh thửa [[x1, y1], [x2, y2], ...]
        :param height: Chiều cao chữ kích thước cạnh (mặc định 1.4m)
        :param offset_dist: Khoảng cách offset chữ ra khỏi tim cạnh ranh giới (mặc định 0.8m)
        :param font_name: Tên font chữ (mặc định '.VnArial')
        :param level: Level ghi kích thước (mặc định '13')
        :param color: Mã màu chữ (mặc định 4 - Vàng)
        """
        import math

        if not points or len(points) < 2:
            return json.dumps({
                "success": False,
                "message": "Cần ít nhất 2 điểm để ghi kích thước cạnh."
            }, ensure_ascii=False)

        # Lọc điểm trùng
        clean_pts = []
        for p in points:
            if not clean_pts:
                clean_pts.append([float(p[0]), float(p[1])])
            else:
                if math.hypot(p[0] - clean_pts[-1][0], p[1] - clean_pts[-1][1]) > 1e-4:
                    clean_pts.append([float(p[0]), float(p[1])])
        if len(clean_pts) > 2 and math.hypot(clean_pts[0][0] - clean_pts[-1][0], clean_pts[0][1] - clean_pts[-1][1]) < 1e-4:
            clean_pts = clean_pts[:-1]

        num_pts = len(clean_pts)
        elements = []

        for i in range(num_pts):
            p1 = clean_pts[i]
            p2 = clean_pts[(i + 1) % num_pts]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length < 1e-3:
                continue

            # Góc nghiêng của đoạn thẳng (degrees)
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)

            # Điểm giữa đoạn thẳng
            mx = (p1[0] + p2[0]) / 2.0
            my = (p1[1] + p2[1]) / 2.0

            # Vector pháp tuyến đơn vị (hướng vuông góc sang trái)
            nx = -dy / length
            ny = dx / length

            # Chuẩn hóa góc quay chữ sao cho không bị ngược đầu (đọc từ trái sang phải, dưới lên trên)
            # Nếu góc nằm trong khoảng (90, 270] hoặc (-180, -90), quay thêm 180 độ
            text_angle = angle_deg
            if text_angle > 90:
                text_angle -= 180
            elif text_angle < -90:
                text_angle += 180

            # Tính tọa độ đặt text có offset
            tx = mx + nx * offset_dist
            ty = my + ny * offset_dist

            elements.append({
                "type": "text",
                "text": f"{length:.2f}",
                "x": tx,
                "y": ty,
                "height": height,
                "rotation": text_angle,
                "level": str(level),
                "color": int(color),
                "font_name": font_name,
                "justification": 7  # Center-Center
            })

        return cad_draw_workflow(elements=elements, fit_view_after=False)

    @mcp.tool
    def draw_cadastral_boundary_marks(
        points: List[List[float]],
        mark_radius: float = 0.3,
        text_height: float = 1.4,
        font_name: str = ".VnArial",
    ) -> str:
        """
        Vẽ các mốc/đỉnh góc ranh giới thửa đất (vòng tròn tâm ranh Level 8) và đánh số thứ tự đỉnh 1, 2, 3... (Level 13).

        :param points: Danh sách tọa độ đỉnh ranh [[x1, y1], [x2, y2], ...]
        :param mark_radius: Bán kính vòng tròn mốc ranh (mặc định 0.3m)
        :param text_height: Chiều cao số hiệu đỉnh ranh (mặc định 1.4m)
        :param font_name: Tên font chữ (mặc định '.VnArial')
        """
        import math

        if not points:
            return json.dumps({"success": False, "message": "Danh sách điểm rỗng."}, ensure_ascii=False)

        # Lọc điểm trùng
        clean_pts = []
        for p in points:
            if not clean_pts:
                clean_pts.append([float(p[0]), float(p[1])])
            else:
                if math.hypot(p[0] - clean_pts[-1][0], p[1] - clean_pts[-1][1]) > 1e-4:
                    clean_pts.append([float(p[0]), float(p[1])])
        if len(clean_pts) > 2 and math.hypot(clean_pts[0][0] - clean_pts[-1][0], clean_pts[0][1] - clean_pts[-1][1]) < 1e-4:
            clean_pts = clean_pts[:-1]

        # Tính trọng tâm để hướng số hiệu điểm ra phía ngoài ranh giới
        cx = sum(p[0] for p in clean_pts) / len(clean_pts)
        cy = sum(p[1] for p in clean_pts) / len(clean_pts)

        elements = []
        for i, pt in enumerate(clean_pts):
            # 1. Vòng tròn mốc ranh (Level 8 / Điểm địa chính, Màu 4)
            elements.append({
                "type": "circle",
                "cx": pt[0],
                "cy": pt[1],
                "cz": 0.0,
                "radius": mark_radius,
                "level": "8",
                "color": 4,
                "weight": 1
            })

            # 2. Hướng offset số hiệu điểm ra phía ngoài trọng tâm
            vx = pt[0] - cx
            vy = pt[1] - cy
            v_len = math.hypot(vx, vy)
            if v_len > 1e-4:
                ux = vx / v_len
                uy = vy / v_len
            else:
                ux, uy = 1.0, 1.0

            offset_text = mark_radius + text_height * 0.8
            tx = pt[0] + ux * offset_text
            ty = pt[1] + uy * offset_text

            # 3. Số hiệu đỉnh ranh (1, 2, 3...) - Level 13, Màu 4
            elements.append({
                "type": "text",
                "text": str(i + 1),
                "x": tx,
                "y": ty,
                "height": text_height,
                "level": "13",
                "color": 4,
                "font_name": font_name,
                "justification": 7
            })

        return cad_draw_workflow(elements=elements, fit_view_after=False)

    @mcp.tool
    def check_parcel_closure(
        points: List[List[float]],
        tolerance: float = 0.005,
    ) -> Dict[str, Any]:
        """
        Kiểm tra tính khép kín hình học của ranh giới thửa đất theo quy chuẩn kỹ thuật địa chính.

        :param points: Danh sách tọa độ đỉnh ranh [[x1, y1], [x2, y2], ...]
        :param tolerance: Dung sai cho phép (mặc định 0.005m = 5mm theo quy chuẩn bản đồ tỷ lệ lớn)
        :return: Kết quả kiểm tra khép kín kèm khoảng cách hở và tọa độ đã tự động khép kín.
        """
        import math

        if not points or len(points) < 3:
            return {
                "is_closed": False,
                "error": "Thửa đất phải có tối thiểu 3 đỉnh ranh giới."
            }

        p_first = points[0]
        p_last = points[-1]

        dx = p_last[0] - p_first[0]
        dy = p_last[1] - p_first[1]
        gap_distance = math.hypot(dx, dy)

        is_already_closed = gap_distance <= tolerance

        # Tạo danh sách điểm khép kín hoàn chỉnh
        closed_points = [list(p) for p in points]
        if not is_already_closed:
            closed_points.append([p_first[0], p_first[1]])

        # Tính diện tích Shoelace
        area = 0.0
        n = len(closed_points)
        for i in range(n - 1):
            area += closed_points[i][0] * closed_points[i + 1][1] - closed_points[i + 1][0] * closed_points[i][1]
        area = abs(area) / 2.0

        return {
            "is_closed": is_already_closed,
            "gap_distance_meters": round(gap_distance, 5),
            "tolerance_meters": tolerance,
            "status": "Khép kín hoàn toàn" if is_already_closed else f"Hở ranh {gap_distance * 1000:.1f} mm (đã tạo tọa độ khép kín đề xuất)",
            "vertex_count": len(points),
            "calculated_area_m2": round(area, 2),
            "closed_points": closed_points
        }

def _assemble_lines_into_polygons(line_segments: List[List[List[float]]], tol: float = 0.05) -> List[List[List[float]]]:
    """
    Nối các đoạn thẳng Line rời rạc thành các vòng đa giác khép kín (closed loops).
    line_segments: danh sách các đoạn [[[x1, y1], [x2, y2]], ...]
    """
    if not line_segments or len(line_segments) < 3:
        return []

    remaining = [list(seg) for seg in line_segments]
    polygons = []

    while remaining:
        seg = remaining.pop(0)
        curr_poly = [list(seg[0]), list(seg[1])]

        extended = True
        while extended and remaining:
            extended = False
            last_pt = curr_poly[-1]
            first_pt = curr_poly[0]

            # Kiểm tra xem vòng đã tự khép kín chưa
            if len(curr_poly) >= 4 and math.hypot(last_pt[0] - first_pt[0], last_pt[1] - first_pt[1]) <= tol:
                break

            best_idx = -1
            best_reverse = False
            best_dist = tol + 1e-4

            for i, other in enumerate(remaining):
                d_start = math.hypot(other[0][0] - last_pt[0], other[0][1] - last_pt[1])
                d_end = math.hypot(other[1][0] - last_pt[0], other[1][1] - last_pt[1])
                if d_start <= tol and d_start < best_dist:
                    best_dist = d_start
                    best_idx = i
                    best_reverse = False
                elif d_end <= tol and d_end < best_dist:
                    best_dist = d_end
                    best_idx = i
                    best_reverse = True

            if best_idx >= 0:
                nxt = remaining.pop(best_idx)
                if best_reverse:
                    curr_poly.append(list(nxt[0]))
                else:
                    curr_poly.append(list(nxt[1]))
                extended = True

        # Đóng vòng
        if len(curr_poly) >= 4:
            first_pt = curr_poly[0]
            last_pt = curr_poly[-1]
            if math.hypot(last_pt[0] - first_pt[0], last_pt[1] - first_pt[1]) <= tol:
                curr_poly = curr_poly[:-1]  # Chuẩn hóa bỏ điểm đóng cuối
            if len(curr_poly) >= 3:
                polygons.append(curr_poly)

    return polygons


    @mcp.tool
    def get_cadastral_parcel_table(
        element_id: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trích xuất tức thì Bảng kê tọa độ góc ranh, chiều dài cạnh và thuộc tính thửa đất
        chuẩn Thông tư 26/2024/TT-BTNMT và Thông tư 23/2025/TT-BNNMT.

        - Tự động nhận diện ranh thửa đất (nếu không truyền element_id): ưu tiên Level 10, Level 37, hoặc hình khép kín trong bản vẽ.
        - Tự động kết nối các đoạn thẳng Line rời rạc (Type 3) trên Level 10 thành đa giác ranh thửa khép kín.
        - Trích xuất toàn bộ đỉnh ranh giới chính xác đến milimét.
        - Tự động lọc điểm trùng lặp, tính chiều dài từng cạnh S_i (từ đỉnh i đến i+1).
        - Tính chính xác diện tích (m2, ha) và chu vi (m).
        - Tự động tìm kiếm và liên kết nhãn số thửa, diện tích pháp lý, loại đất (ODT, ONT...) từ Level 13, Level 4, Level 2, Level 38.
        - Tự động gán số hiệu đỉnh ranh (1, 2, 3...) theo nhãn mốc ranh giới trên bản vẽ và sắp xếp theo đúng chiều mốc 1 -> 2 -> ... -> n.

        :param element_id: ID phần tử ranh thửa đất (tùy chọn)
        :param level: Lọc theo Level chứa ranh thửa (tùy chọn, vd 'Level 10', 'Level 37')
        """
        dgn = bridge.get_active_file()
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache

        target_el = None
        target_pts = None
        target_level_name = ""

        # 1. Tìm phần tử theo element_id nếu có
        if element_id:
            target_el = bridge.find_element_by_id(element_id)
            if not target_el:
                return {"success": False, "error": f"Không tìm thấy phần tử có ID '{element_id}' trong bản vẽ!"}
            target_pts = _get_polygon_from_element(target_el)
            target_level_name = target_el.Level.Name if target_el.Level else ""

        # 2. Duyệt qua cache trong 1 LƯỢT DUY NHẤT (Single Pass)
        preferred_levels = []
        if level:
            preferred_levels.append(str(level).strip().lower())
        preferred_levels.extend(["level 10", "10", "level 37", "37", "level 61", "61"])

        candidate_elements = []  # [(score, area, el, pts, lvl_name)]
        lines_by_level = {}      # lvl_name -> (orig_name, [ [[x1,y1], [x2,y2]], ... ])
        collected_texts = []     # [ (txt, origin, lvl_name) ]

        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
                if not el:
                    continue

                lvl_name = (el.Level.Name if el.Level else "").strip()
                lvl_lower = lvl_name.lower()
                el_type = int(el.Type)

                # Thu thập Text / TextNode
                if el_type == 17:  # Text
                    txt_raw = getattr(el, "Text", None)
                    pt_raw = getattr(el, "Origin", None)
                    if txt_raw is None or pt_raw is None:
                        te = getattr(el, "AsTextElement", None)
                        te = te() if callable(te) else te
                        if te:
                            txt_raw = txt_raw if txt_raw is not None else getattr(te, "Text", "")
                            pt_raw = pt_raw if pt_raw is not None else getattr(te, "Origin", None)
                    if txt_raw is not None and pt_raw is not None:
                        txt_val = str(txt_raw).strip()
                        if txt_val:
                            collected_texts.append((txt_val, (float(pt_raw.X), float(pt_raw.Y)), lvl_lower))
                elif el_type == 7:  # TextNode
                    tne = getattr(el, "AsTextNodeElement", None)
                    tne = tne() if callable(tne) else tne
                    if tne:
                        lines = [tne.TextLine(i).strip() for i in range(1, tne.TextLinesCount + 1)]
                        txt_val = "\n".join(lines).strip()
                        if txt_val:
                            pt = tne.Origin
                            collected_texts.append((txt_val, (float(pt.X), float(pt.Y)), lvl_lower))

                # Thu thập ranh thửa nếu chưa có element_id
                if not target_pts:
                    if el_type in (4, 6, 14) or getattr(el, "IsClosedElement", False):
                        pts = _get_polygon_from_element(el)
                        if pts and len(pts) >= 3:
                            area_cand, _, _, _ = _calc_centroid_and_area(pts)
                            if area_cand > 1.0:
                                score = 0
                                for p_idx, pl in enumerate(preferred_levels):
                                    if lvl_lower == pl:
                                        score = 100 - p_idx
                                        break
                                candidate_elements.append((score, area_cand, el, pts, lvl_name))
                    elif el_type == 3:  # Line rời rạc
                        p1 = getattr(el, "StartPoint", None)
                        p2 = getattr(el, "EndPoint", None)
                        if p1 is None or p2 is None:
                            le = getattr(el, "AsLineElement", None)
                            le = le() if callable(le) else le
                            if le:
                                p1 = getattr(le, "StartPoint", None)
                                p2 = getattr(le, "EndPoint", None)
                        if p1 is not None and p2 is not None:
                            seg = [[round(float(p1.X), 4), round(float(p1.Y), 4)],
                                   [round(float(p2.X), 4), round(float(p2.Y), 4)]]
                            if lvl_lower not in lines_by_level:
                                lines_by_level[lvl_lower] = (lvl_name, [])
                            lines_by_level[lvl_lower][1].append(seg)
            except Exception:
                continue

        # Nếu chưa có target_pts từ element_id, kiểm tra các đa giác tạo từ Line rời rạc
        if not target_pts:
            for lvl_lower, (lvl_orig, segs) in lines_by_level.items():
                if len(segs) >= 3:
                    assembled = _assemble_lines_into_polygons(segs, tol=0.02)
                    for poly in assembled:
                        area_cand, _, _, _ = _calc_centroid_and_area(poly)
                        if area_cand > 1.0:
                            score = 10
                            for p_idx, pl in enumerate(preferred_levels):
                                if lvl_lower == pl:
                                    score = 150 - p_idx  # Ưu tiên cao nhất khi đã gom từ ranh hiện trạng Level 10
                                    break
                            candidate_elements.append((score, area_cand, None, poly, lvl_orig))

            if candidate_elements:
                candidate_elements.sort(key=lambda item: (item[0], item[1]), reverse=True)
                best_cand = candidate_elements[0]
                target_el = best_cand[2]
                target_pts = best_cand[3]
                target_level_name = best_cand[4]

        if not target_pts or len(target_pts) < 3:
            return {
                "success": False,
                "error": "Không tìm thấy phần tử ranh thửa đất nào phù hợp trong bản vẽ!"
            }

        # 3. Làm sạch đỉnh tọa độ
        clean_pts = []
        for p in target_pts:
            pt_clean = [round(float(p[0]), 3), round(float(p[1]), 3)]
            if not clean_pts:
                clean_pts.append(pt_clean)
            else:
                if math.hypot(pt_clean[0] - clean_pts[-1][0], pt_clean[1] - clean_pts[-1][1]) > 0.005:
                    clean_pts.append(pt_clean)

        # Loại bỏ điểm đóng cuối cùng nếu trùng với điểm đầu
        if len(clean_pts) > 2 and math.hypot(clean_pts[0][0] - clean_pts[-1][0], clean_pts[0][1] - clean_pts[-1][1]) < 0.005:
            clean_pts = clean_pts[:-1]

        num_pts = len(clean_pts)
        if num_pts < 3:
            return {"success": False, "error": "Thửa đất sau khi lọc điểm trùng chỉ còn ít hơn 3 đỉnh!"}

        # 4. Tính toán Diện tích và Chu vi
        area, perimeter, cx, cy = _calc_centroid_and_area(clean_pts)

        # 5. Phân tích nhãn từ collected_texts
        so_thua = ""
        loai_dat = ""
        dien_tich_nhan = ""
        to_ban_do = ""

        match_bd = re.search(r'(?:hd|dc|bd|to)[\s_-]*(\d+)', dgn.Name, re.IGNORECASE)
        if match_bd:
            to_ban_do = match_bd.group(1)

        point_labels = {}
        for txt, origin, lvl_lower in collected_texts:
            # Nhãn mốc đỉnh ranh (1, 2, 3...)
            if txt.isdigit() and len(txt) <= 3:
                val_num = int(txt)
                if 1 <= val_num <= num_pts + 10:
                    for p_idx, p in enumerate(clean_pts):
                        dist = math.hypot(origin[0] - p[0], origin[1] - p[1])
                        if dist < 3.0:
                            if p_idx not in point_labels or dist < point_labels[p_idx][1]:
                                point_labels[p_idx] = (txt, dist)

            # Nhãn loại đất
            if txt.upper() in ("ODT", "ONT", "LUC", "CLN", "BHK", "RSX", "TMD", "SKC", "TSC", "DGT", "DNL"):
                dist_c = math.hypot(origin[0] - cx, origin[1] - cy)
                if dist_c < math.sqrt(area) + 15.0:
                    loai_dat = txt.upper()

            # Nhãn diện tích
            if re.match(r'^\d+[\.,]\d+$', txt):
                dist_c = math.hypot(origin[0] - cx, origin[1] - cy)
                if dist_c < math.sqrt(area) + 15.0:
                    dien_tich_nhan = txt.replace(',', '.')

            # Nhãn số thửa
            if txt.isdigit() and ("level 13" in lvl_lower or ("level 38" in lvl_lower and 1 <= int(txt) <= 9999)):
                dist_c = math.hypot(origin[0] - cx, origin[1] - cy)
                if dist_c < math.sqrt(area) + 10.0 and not so_thua:
                    so_thua = txt

        # 6. Chuẩn hóa chiều và đỉnh bắt đầu theo Mốc 1
        idx_1 = None
        for p_idx, (lbl, _) in point_labels.items():
            if lbl == "1":
                idx_1 = p_idx
                break

        if idx_1 is not None:
            # Xoay danh sách đỉnh để bắt đầu từ Mốc 1
            clean_pts = clean_pts[idx_1:] + clean_pts[:idx_1]
            new_point_labels = {}
            for old_idx, val in point_labels.items():
                new_idx = (old_idx - idx_1) % num_pts
                new_point_labels[new_idx] = val
            point_labels = new_point_labels

            # Nếu đỉnh cuối cùng có nhãn 2, đổi chiều danh sách đỉnh để thứ tự tăng dần 1 -> 2 -> ... -> n
            if num_pts > 2:
                last_lbl = point_labels.get(num_pts - 1, ("", 0))[0]
                first_after_1_lbl = point_labels.get(1, ("", 0))[0]
                if last_lbl == "2" or (last_lbl.isdigit() and first_after_1_lbl.isdigit() and int(last_lbl) < int(first_after_1_lbl)):
                    clean_pts = [clean_pts[0]] + clean_pts[1:][::-1]
                    rev_point_labels = {0: point_labels.get(0, ("1", 0))}
                    for i in range(1, num_pts):
                        if (num_pts - i) in point_labels:
                            rev_point_labels[i] = point_labels[num_pts - i]
                    point_labels = rev_point_labels

        # 7. Xây dựng Bảng kê chuẩn Thông tư 26/2024
        table_rows = []
        for i in range(num_pts):
            p_curr = clean_pts[i]
            p_next = clean_pts[(i + 1) % num_pts]

            pt_label = point_labels.get(i, (str(i + 1), 0))[0]
            next_label = point_labels.get((i + 1) % num_pts, (str(((i + 1) % num_pts) + 1), 0))[0]

            edge_len = round(math.hypot(p_next[0] - p_curr[0], p_next[1] - p_curr[1]), 2)
            edge_name = f"{pt_label} - {next_label}"

            table_rows.append({
                "stt": i + 1,
                "point_no": pt_label,
                "x_vn2000_northing": round(p_curr[1], 3),
                "y_vn2000_easting": round(p_curr[0], 3),
                "x_cad": round(p_curr[0], 3),
                "y_cad": round(p_curr[1], 3),
                "next_point": next_label,
                "edge_name": edge_name,
                "edge_length_m": edge_len,
            })

        first_row = table_rows[0]
        closing_row = {
            "stt": num_pts + 1,
            "point_no": first_row["point_no"],
            "x_vn2000_northing": first_row["x_vn2000_northing"],
            "y_vn2000_easting": first_row["y_vn2000_easting"],
            "x_cad": first_row["x_cad"],
            "y_cad": first_row["y_cad"],
            "next_point": "",
            "edge_name": "-",
            "edge_length_m": 0.0,
        }

        target_id_str = str(getattr(target_el, "ID64", getattr(target_el, "ID", ""))) if target_el else "Assembled_Line"

        return {
            "success": True,
            "file_name": dgn.Name,
            "element_id": target_id_str,
            "level": target_level_name or "Level 10",
            "so_thua": so_thua or "Chưa rõ",
            "to_ban_do": to_ban_do or "Chưa rõ",
            "loai_dat": loai_dat or "ODT",
            "dien_tich_nhan_m2": dien_tich_nhan or str(round(area, 1)),
            "dien_tich_tinh_toan_m2": round(area, 4),
            "chu_vi_m": round(perimeter, 4),
            "centroid": [round(cx, 3), round(cy, 3)],
            "num_points": num_pts,
            "table": table_rows,
            "closing_point": closing_row,
        }


