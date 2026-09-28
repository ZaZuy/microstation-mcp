"""
src/tools/native_batch.py
Các công cụ MCP chỉ có qua Named Pipe MDL Native - không có COM equivalent.
Bao gồm: batch tạo elements, transaction control, model snapshot, scan elements,
và đọc active settings.

Tất cả tool yêu cầu MDL App 'MsNativePipe.ma' đang được load trong MicroStation.
Nếu pipe không sẵn sàng, tool trả về JSON lỗi có hướng dẫn người dùng.
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional

from src.core.pipe_client import PipeClient, PipeConnectionError, PipeError

logger = logging.getLogger(__name__)

# ───────────────── Hằng số nội bộ ─────────────────
_MDL_NOT_LOADED_MSG = (
    "MDL Native App 'MsNativePipe.ma' chưa được load trong MicroStation. "
    "Vào MicroStation → Utilities → MDL Applications → Load → chọn MsNativePipe.ma. "
    "Sau đó thử lại tool này."
)


def _err(message: str, **extra) -> str:
    """Tạo JSON response lỗi chuẩn."""
    return json.dumps({"success": False, "message": message, **extra}, ensure_ascii=False)


def _ok(**fields) -> str:
    """Tạo JSON response thành công chuẩn."""
    return json.dumps({"success": True, **fields}, ensure_ascii=False)


def _batch_draw_via_com(elements: List[Dict[str, Any]], use_undo_group: bool = True) -> str:
    """
    Tự động fallback vẽ hàng loạt qua COM khi Named Pipe MDL Native không khả dụng.
    Hỗ trợ line, linestring/polyline, shape, circle, ellipse, arc, text, point.
    """
    try:
        from src.core.ms_bridge import bridge
        app = bridge.get_app()
    except Exception as e:
        return _err(f"Không thể kết nối MicroStation qua cả Named Pipe lẫn COM: {e}")

    elem_ids = []
    errors = []

    for i, elem in enumerate(elements):
        try:
            elem_type = elem.get("type", "").lower()
            level = elem.get("level")
            color = elem.get("color")
            weight = elem.get("weight")
            style = elem.get("style")
            fill = elem.get("filled", False)
            fill_color = elem.get("fill_color", color)

            created_elem = None

            if elem_type == "line":
                p1 = bridge.create_point(float(elem.get("x1", 0)), float(elem.get("y1", 0)), float(elem.get("z1", 0)))
                p2 = bridge.create_point(float(elem.get("x2", 0)), float(elem.get("y2", 0)), float(elem.get("z2", 0)))
                created_elem = bridge.unwrap(app.CreateLineElement2(None, p1, p2))

            elif elem_type in ("polyline", "linestring"):
                pts = elem.get("points", [])
                if len(pts) >= 2:
                    pt_objs = [bridge.create_point(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
                    created_elem = bridge.unwrap(app.CreateLineElement1(None, pt_objs))
                else:
                    errors.append(f"Element[{i}] (polyline): Cần ít nhất 2 điểm")
                    continue

            elif elem_type == "shape":
                pts = elem.get("points", [])
                if len(pts) >= 3:
                    pt_objs = [bridge.create_point(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
                    fill_mode = 1 if fill else 0
                    created_elem = bridge.unwrap(app.CreateShapeElement1(None, pt_objs, fill_mode))
                    if fill and fill_color is not None:
                        try:
                            created_elem.FillColor = int(fill_color)
                        except Exception:
                            pass
                else:
                    errors.append(f"Element[{i}] (shape): Cần ít nhất 3 điểm")
                    continue

            elif elem_type == "circle":
                cx = float(elem.get("cx", 0))
                cy = float(elem.get("cy", 0))
                cz = float(elem.get("cz", 0))
                radius = float(elem.get("radius", 0))
                center = bridge.create_point(cx, cy, cz)
                matrix = bridge.create_rotation_matrix(0.0)
                fill_mode = 1 if fill else 0
                created_elem = bridge.unwrap(app.CreateEllipseElement2(None, center, radius, radius, matrix, fill_mode))
                if fill and fill_color is not None:
                    try:
                        created_elem.FillColor = int(fill_color)
                    except Exception:
                        pass

            elif elem_type == "ellipse":
                cx = float(elem.get("cx", 0))
                cy = float(elem.get("cy", 0))
                cz = float(elem.get("cz", 0))
                rx = float(elem.get("primary_radius", elem.get("r1", 0)))
                ry = float(elem.get("secondary_radius", elem.get("r2", 0)))
                rot = float(elem.get("rotation", 0.0))
                center = bridge.create_point(cx, cy, cz)
                matrix = bridge.create_rotation_matrix(rot)
                fill_mode = 1 if fill else 0
                created_elem = bridge.unwrap(app.CreateEllipseElement2(None, center, rx, ry, matrix, fill_mode))

            elif elem_type == "arc":
                cx = float(elem.get("cx", 0))
                cy = float(elem.get("cy", 0))
                cz = float(elem.get("cz", 0))
                radius = float(elem.get("radius", 0))
                start_angle = math.radians(float(elem.get("start_angle", 0.0)))
                sweep_angle = math.radians(float(elem.get("sweep_angle", 360.0)))
                center = bridge.create_point(cx, cy, cz)
                matrix = bridge.create_rotation_matrix(0.0)
                created_elem = bridge.unwrap(app.CreateArcElement1(None, center, radius, radius, matrix, start_angle, sweep_angle))

            elif elem_type == "text":
                tx = float(elem.get("x", 0))
                ty = float(elem.get("y", 0))
                tz = float(elem.get("z", 0))
                content = str(elem.get("text", ""))
                height = float(elem.get("height", 2.5))
                width = float(elem.get("width", height))
                rotation = float(elem.get("rotation", 0.0))
                font_name = elem.get("font_name")
                justification = elem.get("justification")
                
                origin = bridge.create_point(tx, ty, tz)
                matrix = bridge.create_rotation_matrix(rotation)
                clean_content = str(content)
                try:
                    clean_content.encode('ascii')
                except UnicodeEncodeError:
                    import unicodedata
                    clean = unicodedata.normalize('NFD', clean_content)
                    clean = ''.join(c for c in clean if unicodedata.category(c) != 'Mn')
                    clean = clean.replace('đ', 'd').replace('Đ', 'D')
                    clean_content = clean.encode('ascii', 'replace').decode('ascii').replace('?', ' ')

                created_elem = bridge.unwrap(app.CreateTextElement1(None, clean_content, origin, matrix))
                try:
                    created_elem.TextStyle.Height = height
                    created_elem.TextStyle.Width = width
                    if font_name:
                        font_obj = app.ActiveDesignFile.Fonts.Find(font_name)
                        if font_obj:
                            created_elem.TextStyle.Font = font_obj
                    if justification is not None:
                        created_elem.TextStyle.Justification = int(justification)
                except Exception:
                    pass

            elif elem_type == "point":
                px = float(elem.get("x", 0))
                py = float(elem.get("y", 0))
                pz = float(elem.get("z", 0))
                pt_obj = bridge.create_point(px, py, pz)
                try:
                    created_elem = bridge.unwrap(app.CreatePointMarkerElement1(None, pt_obj, 0))
                except Exception:
                    created_elem = bridge.unwrap(app.CreateLineElement2(None, pt_obj, pt_obj))

            if created_elem:
                bridge.apply_symbology(created_elem, level=level, color=color, weight=weight, style=style)
                bridge.add_element(created_elem)
                try:
                    eid = getattr(created_elem, "ID64", getattr(created_elem, "ID", i + 1))
                    elem_ids.append(int(eid))
                except Exception:
                    elem_ids.append(i + 1)
            else:
                errors.append(f"Element[{i}] ({elem_type}): Loại element chưa được hỗ trợ trong COM fallback")

        except Exception as ex:
            errors.append(f"Element[{i}] ({elem.get('type', '?')}): {str(ex)}")

    created = len(elem_ids)
    failed = len(elements) - created

    return json.dumps({
        "success": failed == 0,
        "total": len(elements),
        "created": created,
        "failed": failed,
        "element_ids": elem_ids,
        "errors": errors,
        "executed_via": "com_fallback"
    }, ensure_ascii=False)


def _get_model_snapshot_via_com(max_elements: int = 5000) -> str:
    """
    Fallback lấy snapshot mô hình qua COM khi Named Pipe MDL Native không khả dụng.
    """
    try:
        from src.core.ms_bridge import bridge
        model = bridge.get_active_model()
        cache = model.GraphicalElementCache
        total_count = getattr(cache, "Count", 0)

        ee = model.Scan()
        elements = []
        count = 0
        while ee.MoveNext() and count < max_elements:
            elem = ee.Current
            try:
                elements.append({
                    "id": getattr(elem, "ID64", getattr(elem, "ID", count + 1)),
                    "type": str(getattr(elem, "Type", "Unknown")),
                    "level": getattr(getattr(elem, "Level", None), "Name", "Default"),
                    "color": getattr(elem, "Color", 0),
                    "weight": getattr(elem, "LineWeight", 0),
                    "geometry_summary": f"Type {getattr(elem, 'Type', '?')}"
                })
                count += 1
            except Exception:
                continue

        return json.dumps({
            "success": True,
            "model_name": getattr(model, "Name", "Default"),
            "element_count": total_count,
            "returned": len(elements),
            "elements": elements,
            "executed_via": "com_fallback"
        }, ensure_ascii=False)
    except Exception as e:
        return _err(f"Lỗi khi lấy model snapshot qua COM fallback: {e}")


# ═══════════════════════════════════════════════════════════════════
#  Hàm đăng ký tất cả tools
# ═══════════════════════════════════════════════════════════════════

def register_native_batch_tools(mcp, pipe_client: PipeClient) -> None:
    """
    Đăng ký tất cả native batch tools vào MCP server.

    Args:
        mcp:         MCP server instance (FastMCP hoặc tương thích).
        pipe_client: PipeClient đã khởi tạo, dùng chung cho tất cả tools.
    """

    # ─────────────────────────────────────────────────────────────
    # Tool 1: batch_draw_elements
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def batch_draw_elements(
        elements: List[Dict[str, Any]],
        use_undo_group: bool = True,
    ) -> str:
        """
        **Tool tốc độ cao nhất** - Tạo nhiều element CAD trong một round-trip duy nhất qua Named Pipe.

        Gửi toàn bộ danh sách elements tới MDL Native App trong một lần gửi pipe,
        giúp tốc độ cao hơn ~10-50x so với gọi COM từng element một.

        Yêu cầu MDL App 'MsNativePipe.ma' đang chạy trong MicroStation.

        Args:
            elements: Danh sách các element cần tạo. Mỗi element là dict với:
                - "type": loại element ("line", "circle", "arc", "shape", "text", "polyline")
                - Với "line":    x1, y1, z1, x2, y2, z2 (float)
                - Với "circle":  cx, cy, cz, radius (float)
                - Với "arc":     cx, cy, cz, radius, start_angle, sweep_angle (float, độ)
                - Với "shape":   points (list of [x,y,z]), filled (bool)
                - Với "text":    x, y, z, text (str), height (float), rotation (float, độ)
                - Tất cả hỗ trợ: level (str), color (int 0-255), weight (int 0-31), style (int 0-7)

                Ví dụ:
                [
                    {"type": "line", "x1":0,"y1":0,"z1":0,"x2":100,"y2":0,"z2":0,"level":"Default"},
                    {"type": "circle", "cx":50,"cy":50,"cz":0,"radius":30},
                    {"type": "text", "x":10,"y":10,"z":0,"text":"Hello CAD","height":5}
                ]

            use_undo_group: Nếu True, toàn bộ batch được gói trong một undo group,
                            cho phép Ctrl+Z undo một lần xóa tất cả. Mặc định True.

        Returns:
            JSON string: {
                "success": bool,
                "total": int,
                "created": int,
                "failed": int,
                "element_ids": [int],
                "errors": [str]
            }
        """
        if not elements:
            return _err("Danh sách elements rỗng. Vui lòng truyền ít nhất 1 element.")

        # Validate sơ bộ trước khi gửi pipe
        valid_types = {'line', 'circle', 'arc', 'shape', 'text', 'polyline', 'ellipse'}
        validation_errors: List[str] = []
        for i, elem in enumerate(elements):
            elem_type = elem.get('type', '')
            if elem_type not in valid_types:
                validation_errors.append(
                    f"Element[{i}]: type '{elem_type}' không hợp lệ. "
                    f"Chấp nhận: {sorted(valid_types)}"
                )

        if validation_errors:
            return _err(
                f"Validation thất bại với {len(validation_errors)} lỗi.",
                errors=validation_errors,
                total=len(elements),
                created=0,
                failed=len(elements),
                element_ids=[],
            )

        try:
            response = pipe_client.send_command(
                'batch_create',
                {
                    'elements':       elements,
                    'use_undo_group': use_undo_group,
                },
            )

            results  = response.get('results', [])
            if not response.get('success') or not results:
                return _batch_draw_via_com(elements, use_undo_group)

            elem_ids = [r.get('element_id') for r in results if r.get('success')]
            errors   = [
                f"Element[{i}] ({r.get('type','?')}): {r.get('message','Lỗi không xác định')}"
                for i, r in enumerate(results)
                if not r.get('success')
            ]

            created = len(elem_ids)
            failed  = len(elements) - created

            return json.dumps({
                "success":     failed == 0,
                "total":       len(elements),
                "created":     created,
                "failed":      failed,
                "element_ids": [eid for eid in elem_ids if eid is not None],
                "errors":      errors,
            }, ensure_ascii=False)

        except PipeConnectionError:
            logger.info("Named Pipe chưa sẵn sàng, tự động chuyển sang COM fallback cho batch_draw_elements.")
            return _batch_draw_via_com(elements, use_undo_group)
        except PipeError as exc:
            return _err(
                f"Lỗi pipe khi gửi batch: {exc}",
                total=len(elements), created=0,
                failed=len(elements), element_ids=[], errors=[str(exc)],
            )

    # ─────────────────────────────────────────────────────────────
    # Tool 2: begin_transaction
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def begin_transaction(description: str = 'MCP Transaction') -> str:
        """
        Bắt đầu một undo group (transaction) trong MicroStation.

        Sau khi gọi tool này, tất cả thao tác vẽ tiếp theo sẽ được gom vào một nhóm,
        cho phép người dùng undo toàn bộ chỉ bằng một lần nhấn Ctrl+Z.

        Nên gọi begin_transaction trước khi vẽ nhiều element liên quan,
        và gọi end_transaction khi hoàn thành.

        Args:
            description: Mô tả ngắn cho transaction, hiển thị trong undo history.
                         Mặc định: 'MCP Transaction'.

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        try:
            response = pipe_client.send_command(
                'begin_transaction',
                {'description': description},
            )
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            return (
                _ok(message=response.get('message', 'Transaction đã bắt đầu.')) if ok
                else _err(response.get('message', 'MDL trả về lỗi khi begin_transaction.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 3: end_transaction
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def end_transaction(commit: bool = True) -> str:
        """
        Kết thúc hoặc hủy bỏ transaction hiện tại.

        Gọi sau begin_transaction để đóng undo group.
        Nếu commit=True: xác nhận tất cả thay đổi.
        Nếu commit=False: hủy bỏ và undo tất cả thay đổi kể từ begin_transaction.

        Args:
            commit: True để commit (giữ lại thay đổi), False để rollback (hoàn tác).
                    Mặc định: True.

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        cmd         = 'end_transaction' if commit else 'cancel_transaction'
        action_name = 'commit' if commit else 'cancel/rollback'
        try:
            response    = pipe_client.send_command(cmd, {})
            ok          = (response.get('status') == 'ok') or (response.get('success') is True)
            default_msg = f'Transaction đã {"commit" if commit else "bị hủy"} thành công.'
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', f'MDL trả về lỗi khi {action_name} transaction.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 4: get_model_snapshot
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def get_model_snapshot(max_elements: int = 5000) -> str:
        """
        **QUAN TRỌNG** - Lấy snapshot tức thời của toàn bộ element trong model hiện tại.

        Luôn gọi tool này TRƯỚC KHI VẼ để AI biết trạng thái hiện tại của model,
        tránh vẽ chồng lên element đã có, hoặc đặt text đè lên nhau.

        Trả về danh sách tất cả elements với thông tin cơ bản (không bao gồm geometry đầy đủ).
        Nhanh hơn COM vì MDL serialize toàn bộ trong một lần và gửi qua pipe.

        Args:
            max_elements: Số element tối đa trả về (để tránh quá tải AI context).
                          Mặc định: 5000. Giảm xuống nếu model có nhiều element.

        Returns:
            JSON string: {
                "success": bool,
                "element_count": int,
                "returned": int,
                "elements": [
                    {
                        "id": int,
                        "type": str,
                        "level": str,
                        "color": int,
                        "weight": int,
                        "geometry_summary": str
                    },
                    ...
                ]
            }
        """
        try:
            response = pipe_client.send_command(
                'get_model_snapshot',
                {'max_elements': max_elements},
            )
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            if not ok:
                return _err(response.get('message', 'MDL trả về lỗi khi get_model_snapshot.'))

            result = response.get('result') or response.get('data') or {}
            elements = result.get('elements', []) if isinstance(result, dict) else []
            count = result.get('element_count', len(elements))
            return json.dumps({
                "success":       True,
                "model_name":    result.get('model_name', ''),
                "element_count": count,
                "returned":      len(elements),
                "elements":      elements,
            }, ensure_ascii=False)

        except PipeConnectionError:
            logger.info("Named Pipe chưa sẵn sàng, tự động chuyển sang COM fallback cho get_model_snapshot.")
            return _get_model_snapshot_via_com(max_elements=max_elements)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi lấy model snapshot: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 5: get_pipe_status
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def get_pipe_status() -> str:
        """
        Kiểm tra trạng thái kết nối Named Pipe tới MDL Native App.

        Dùng để xác định xem MDL App 'MsNativePipe.ma' có đang chạy trong MicroStation không.
        Nếu không kết nối được (not_connected), các tool native_ sẽ thất bại và cần dùng
        COM fallback (chậm hơn ~10-50x).

        Không có tham số.

        Returns:
            JSON string: {
                "connected": bool,
                "pipe_name": str,
                "mode": str,        - "native_pipe" | "not_connected"
                "latency_ms": float - Chỉ có khi connected=True
            }
        """
        import time as _time
        pipe_name = getattr(pipe_client, '_pipe_name', r'\\.\pipe\MsNativeMCP')

        if not pipe_client.is_connected():
            try:
                pipe_client._connect()
            except Exception:
                return json.dumps({
                    "connected": False,
                    "pipe_name": pipe_name,
                    "mode":      "not_connected",
                    "message":   _MDL_NOT_LOADED_MSG,
                }, ensure_ascii=False)

        t0         = _time.perf_counter()
        alive      = pipe_client.ping()
        latency_ms = (_time.perf_counter() - t0) * 1000.0

        if alive:
            return json.dumps({
                "connected":  True,
                "pipe_name":  pipe_name,
                "mode":       "native_pipe",
                "latency_ms": round(latency_ms, 2),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "connected": False,
                "pipe_name": pipe_name,
                "mode":      "not_connected",
                "message":   "Pipe handle mở nhưng MDL không phản hồi ping. MDL có thể đang bận.",
            }, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────
    # Tool 6: native_scan_elements
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_scan_elements(
        type_filter:  Optional[str] = None,
        level_filter: Optional[str] = None,
        max_count:    int           = 200,
    ) -> str:
        """
        Quét và liệt kê các element trong model qua Named Pipe (nhanh hơn COM scan).

        Nhanh hơn COM scan_elements vì MDL serialize toàn bộ kết quả trong một lần,
        không phải marshal từng element qua COM boundary.

        Args:
            type_filter:  Lọc theo loại element (không phân biệt hoa thường).
                          Ví dụ: 'line', 'arc', 'text', 'shape', 'cell', 'ellipse'.
                          None = lấy tất cả loại.
            level_filter: Lọc theo tên level (khớp chính xác, phân biệt hoa thường).
                          None = lấy tất cả level.
            max_count:    Số element tối đa trả về. Mặc định: 200.

        Returns:
            JSON string: {
                "success": bool,
                "count": int,
                "elements": [
                    {"id": int, "type": str, "level": str, "color": int, "weight": int, "style": int},
                    ...
                ]
            }
        """
        params: Dict[str, Any] = {'max_count': max_count}
        if type_filter  is not None:
            params['type_filter']  = type_filter.lower()
        if level_filter is not None:
            params['level_filter'] = level_filter

        try:
            response = pipe_client.send_command('scan_elements', params)
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            if not ok:
                return _err(response.get('message', 'MDL lỗi khi scan_elements.'))

            result   = response.get('result') or response.get('data') or {}
            elements = result.get('elements', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
            return json.dumps({
                "success":  True,
                "count":    len(elements),
                "elements": elements,
            }, ensure_ascii=False)

        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi scan elements: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 7: native_get_active_settings
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_get_active_settings() -> str:
        """
        Lấy active settings hiện tại từ MDL Native App.

        Gọi tool này để biết:
        - File DGN nào đang mở (file_path, model_name)
        - Level đang active (active_level)
        - Màu / độ dày / style đang dùng (active_color, active_weight, active_style)
        - Đơn vị vẽ (uors_per_master, master_unit_name)

        **Quan trọng**: AI nên gọi tool này TRƯỚC KHI VẼ để set đúng context,
        tránh vẽ nhầm level hoặc dùng sai đơn vị.

        Không có tham số.

        Returns:
            JSON string: {
                "success": bool,
                "model_name": str,
                "file_path": str,
                "active_level": str,
                "active_color": int,
                "active_weight": int,
                "active_style": int,
                "uors_per_master": float,
                "master_unit_name": str
            }
        """
        try:
            response = pipe_client.send_command('get_active_settings', {})
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            if not ok:
                return _err(response.get('message', 'MDL lỗi khi get_active_settings.'))

            result = response.get('result') or response.get('data') or {}
            return json.dumps({
                "success":          True,
                "model_name":       result.get('model_name',       ''),
                "file_path":        result.get('file_path',        ''),
                "active_level":     result.get('active_level',     ''),
                "active_color":     result.get('active_color',     0),
                "active_weight":    result.get('active_weight',    0),
                "active_style":     result.get('active_style',     0),
                "uors_per_master":  result.get('uors_per_master',  1.0),
                "master_unit_name": result.get('master_unit_name', ''),
            }, ensure_ascii=False)

        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi get_active_settings: {exc}")

    logger.info(
        "native_batch: Đã đăng ký 7 tools: "
        "batch_draw_elements, begin_transaction, end_transaction, "
        "get_model_snapshot, get_pipe_status, native_scan_elements, "
        "native_get_active_settings."
    )
