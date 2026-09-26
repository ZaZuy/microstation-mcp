"""
src/tools/drawing_native.py
Phiên bản native (Named Pipe) của các công cụ vẽ quan trọng trong MicroStation V8i.

Các tool này giao tiếp trực tiếp với MDL Native App qua Named Pipe,
cho tốc độ cao hơn ~10-50x so với COM out-of-process (đặc biệt rõ khi vẽ nhiều element).

Quy ước đặt tên:
    - Prefix 'native_' phân biệt với COM version trong drawing.py
    - Cùng tên tham số với COM version để AI dễ chuyển đổi

Yêu cầu: MDL App 'MsNativePipe.ma' phải đang chạy trong MicroStation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.core.pipe_client import PipeClient, PipeConnectionError, PipeError

logger = logging.getLogger(__name__)

# ─────────────────────────── Hằng số ───────────────────────────
_MDL_NOT_LOADED_MSG = (
    "MDL Native App 'MsNativePipe.ma' chưa được load trong MicroStation. "
    "Vào MicroStation → Utilities → MDL Applications → Load → chọn MsNativePipe.ma. "
    "Sau đó thử lại tool này."
)

# Giới hạn validation
_COLOR_MIN, _COLOR_MAX   = 0, 255
_WEIGHT_MIN, _WEIGHT_MAX = 0, 31
_STYLE_MIN, _STYLE_MAX   = 0, 7


# ─────────────────────────── Helpers ───────────────────────────

def _err(message: str, **extra) -> str:
    """Tạo JSON response lỗi chuẩn."""
    return json.dumps({"success": False, "message": message, **extra}, ensure_ascii=False)


def _ok(**fields) -> str:
    """Tạo JSON response thành công chuẩn."""
    return json.dumps({"success": True, **fields}, ensure_ascii=False)


def _build_symbology(
    level:  Optional[str] = None,
    color:  Optional[int] = None,
    weight: Optional[int] = None,
    style:  Optional[int] = None,
) -> Dict[str, Any]:
    """
    Tạo dict symbology từ các tham số tùy chọn.
    Chỉ thêm key nếu tham số không None - để MDL dùng active settings cho phần còn lại.
    """
    sym: Dict[str, Any] = {}
    if level  is not None: sym['level']  = level
    if color  is not None: sym['color']  = color
    if weight is not None: sym['weight'] = weight
    if style  is not None: sym['style']  = style
    return sym


def _validate_symbology(
    color:  Optional[int],
    weight: Optional[int],
    style:  Optional[int],
) -> Optional[str]:
    """
    Kiểm tra giá trị symbology nằm trong khoảng hợp lệ.

    Returns:
        Thông báo lỗi (str) nếu có lỗi, None nếu hợp lệ.
    """
    if color  is not None and not (_COLOR_MIN  <= color  <= _COLOR_MAX):
        return f"color phải trong khoảng {_COLOR_MIN}-{_COLOR_MAX}, nhận: {color}"
    if weight is not None and not (_WEIGHT_MIN <= weight <= _WEIGHT_MAX):
        return f"weight phải trong khoảng {_WEIGHT_MIN}-{_WEIGHT_MAX}, nhận: {weight}"
    if style  is not None and not (_STYLE_MIN  <= style  <= _STYLE_MAX):
        return f"style phải trong khoảng {_STYLE_MIN}-{_STYLE_MAX}, nhận: {style}"
    return None


def _pipe_draw(
    pipe_client: PipeClient,
    cmd:         str,
    params:      Dict[str, Any],
) -> str:
    """
    Helper chung: gửi lệnh vẽ qua pipe, xử lý lỗi, trả về JSON string.

    Args:
        pipe_client: PipeClient đã kết nối.
        cmd:         Tên lệnh MDL.
        params:      Tham số lệnh.

    Returns:
        JSON string kết quả.
    """
    try:
        response = pipe_client.send_command(cmd, params)
        ok = (response.get('status') == 'ok') or (response.get('success') is True)
        if ok:
            result = response.get('result') or response.get('data') or {}
            element_id = result.get('element_id') or response.get('element_id')
            return json.dumps({
                "success":    True,
                "element_id": element_id,
                "type":       result.get('type', cmd.replace('draw_', '').replace('native_', '')),
                "level":      result.get('level', params.get('level', '')),
                "message":    result.get('message', 'Element đã được tạo thành công.'),
            }, ensure_ascii=False)
        else:
            return _err(response.get('message', f'MDL trả về lỗi khi thực thi {cmd}.'))
    except PipeConnectionError:
        return _err(_MDL_NOT_LOADED_MSG)
    except PipeError as exc:
        return _err(f"Lỗi pipe khi thực thi {cmd}: {exc}")


# ═══════════════════════════════════════════════════════════════════
#  Hàm đăng ký tất cả drawing native tools
# ═══════════════════════════════════════════════════════════════════

def register_drawing_native_tools(mcp, pipe_client: PipeClient) -> None:
    """
    Đăng ký tất cả drawing native tools vào MCP server.

    Args:
        mcp:         MCP server instance.
        pipe_client: PipeClient dùng chung.
    """

    # ─────────────────────────────────────────────────────────────
    # Tool 1: native_draw_line
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_line(
        x1:     float,
        y1:     float,
        x2:     float,
        y2:     float,
        z1:     float          = 0.0,
        z2:     float          = 0.0,
        level:  Optional[str] = None,
        color:  Optional[int] = None,
        weight: Optional[int] = None,
        style:  Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ một đường thẳng (LineElement) qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Tạo line element từ điểm (x1, y1, z1) đến điểm (x2, y2, z2).
        Đơn vị: Master Unit của file DGN đang mở (xem native_get_active_settings).

        Args:
            x1, y1, z1: Tọa độ điểm đầu (z mặc định 0).
            x2, y2, z2: Tọa độ điểm cuối (z mặc định 0).
            level:      Tên level (None = dùng active level).
            color:      Màu (0-255, None = dùng active color).
            weight:     Độ dày nét (0-31, None = dùng active weight).
            style:      Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "line", "level": str, "message": str}
        """
        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        return _pipe_draw(pipe_client, 'draw_line', {
            'x1': x1, 'y1': y1, 'z1': z1,
            'x2': x2, 'y2': y2, 'z2': z2,
            **_build_symbology(level, color, weight, style),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool: native_draw_linestring
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_linestring(
        points: List[List[float]],
        level:  Optional[str] = None,
        color:  Optional[int] = None,
        weight: Optional[int] = None,
        style:  Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ chuỗi đoạn thẳng liên tiếp (LineString / Polyline) qua Named Pipe.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            points: Danh sách các điểm [[x1, y1, z1], [x2, y2, z2], ...]. Tối thiểu 2 điểm.
            level:  Tên level (None = dùng active level).
            color:  Màu (0-255, None = dùng active color).
            weight: Độ dày nét (0-31, None = dùng active weight).
            style:  Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "linestring", "level": str, "message": str}
        """
        if len(points) < 2:
            return _err(f"Cần ít nhất 2 điểm để tạo linestring, nhận: {len(points)} điểm.")
        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        normalized: List[List[float]] = []
        for i, pt in enumerate(points):
            if len(pt) < 2:
                return _err(f"Điểm [{i}] thiếu tọa độ: cần ít nhất [x, y]")
            normalized.append([float(pt[0]), float(pt[1]), float(pt[2]) if len(pt) > 2 else 0.0])

        return _pipe_draw(pipe_client, 'draw_linestring', {
            'points': normalized,
            **_build_symbology(level, color, weight, style),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool 2: native_draw_circle
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_circle(
        cx:     float,
        cy:     float,
        radius: float,
        cz:     float          = 0.0,
        level:  Optional[str] = None,
        color:  Optional[int] = None,
        weight: Optional[int] = None,
        style:  Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ hình tròn (EllipseElement) qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Tạo circle element với tâm (cx, cy, cz) và bán kính radius.

        Args:
            cx, cy, cz: Tọa độ tâm hình tròn (cz mặc định 0).
            radius:     Bán kính (phải > 0).
            level:      Tên level (None = dùng active level).
            color:      Màu (0-255, None = dùng active color).
            weight:     Độ dày nét (0-31, None = dùng active weight).
            style:      Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "circle", "level": str, "message": str}
        """
        if radius <= 0:
            return _err(f"radius phải > 0, nhận: {radius}")
        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        return _pipe_draw(pipe_client, 'draw_circle', {
            'cx': cx, 'cy': cy, 'cz': cz,
            'radius': radius,
            **_build_symbology(level, color, weight, style),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool 3: native_draw_arc
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_arc(
        cx:          float,
        cy:          float,
        radius:      float,
        start_angle: float,
        sweep_angle: float,
        cz:          float          = 0.0,
        level:       Optional[str] = None,
        color:       Optional[int] = None,
        weight:      Optional[int] = None,
        style:       Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ cung tròn (ArcElement) qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            cx, cy, cz:  Tọa độ tâm cung tròn (cz mặc định 0).
            radius:      Bán kính (phải > 0).
            start_angle: Góc bắt đầu tính từ trục X dương, đơn vị độ (0-360).
            sweep_angle: Góc quét (độ). Dương = ngược chiều kim đồng hồ, âm = thuận chiều.
            level:       Tên level (None = dùng active level).
            color:       Màu (0-255, None = dùng active color).
            weight:      Độ dày nét (0-31, None = dùng active weight).
            style:       Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "arc", "level": str, "message": str}
        """
        if radius <= 0:
            return _err(f"radius phải > 0, nhận: {radius}")
        if sweep_angle == 0:
            return _err("sweep_angle không được bằng 0.")
        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        return _pipe_draw(pipe_client, 'draw_arc', {
            'cx': cx, 'cy': cy, 'cz': cz,
            'radius':      radius,
            'start_angle': start_angle,
            'sweep_angle': sweep_angle,
            **_build_symbology(level, color, weight, style),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool: native_draw_ellipse
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_ellipse(
        cx:          float,
        cy:          float,
        primary_r:   float,
        secondary_r: float,
        rotation:    float         = 0.0,
        cz:          float         = 0.0,
        level:       Optional[str] = None,
        color:       Optional[int] = None,
        weight:      Optional[int] = None,
        style:       Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ hình elip qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            cx, cy, cz:  Tâm elip (cz mặc định 0).
            primary_r:   Bán kính trục chính (phải > 0).
            secondary_r: Bán kính trục phụ (phải > 0).
            rotation:    Góc xoay trục chính (độ, ngược chiều kim đồng hồ). Mặc định 0.
            level:       Tên level (None = dùng active level).
            color:       Màu (0-255, None = dùng active color).
            weight:      Độ dày nét (0-31, None = dùng active weight).
            style:       Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "ellipse", "level": str, "message": str}
        """
        if primary_r <= 0 or secondary_r <= 0:
            return _err("primary_r và secondary_r phải > 0")
        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        import math
        rot_rad = math.radians(rotation)

        return _pipe_draw(pipe_client, 'draw_ellipse', {
            'cx': cx, 'cy': cy, 'cz': cz,
            'primary_r':   primary_r,
            'secondary_r': secondary_r,
            'rotation':    rot_rad,
            **_build_symbology(level, color, weight, style),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool 4: native_draw_shape
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_shape(
        points:     List[List[float]],
        filled:     bool           = False,
        fill_color: Optional[int] = None,
        level:      Optional[str] = None,
        color:      Optional[int] = None,
        weight:     Optional[int] = None,
        style:      Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ hình đa giác (ShapeElement) qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Tạo shape element từ danh sách điểm. Shape tự động khép kín (điểm đầu = điểm cuối).

        Args:
            points:     Danh sách điểm [[x, y, z], ...] hoặc [[x, y], ...].
                        Cần ít nhất 3 điểm. z mặc định 0 nếu không truyền.
                        Ví dụ: [[0,0], [100,0], [100,50], [0,50]]
            filled:     True = tô màu bên trong shape. Mặc định False.
            fill_color: Màu tô (0-255). Chỉ dùng khi filled=True. None = dùng active color.
            level:      Tên level (None = dùng active level).
            color:      Màu đường viền (0-255, None = dùng active color).
            weight:     Độ dày nét viền (0-31, None = dùng active weight).
            style:      Line style (0-7, None = dùng active style).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "shape", "level": str, "message": str}
        """
        if len(points) < 3:
            return _err(f"Cần ít nhất 3 điểm để tạo shape, nhận: {len(points)} điểm.")

        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")
        if fill_color is not None and not (_COLOR_MIN <= fill_color <= _COLOR_MAX):
            return _err(f"fill_color phải trong khoảng 0-255, nhận: {fill_color}")

        # Chuẩn hóa điểm: đảm bảo mỗi điểm có đủ 3 tọa độ
        normalized: List[List[float]] = []
        for i, pt in enumerate(points):
            if len(pt) < 2:
                return _err(f"Điểm [{i}] thiếu tọa độ: cần ít nhất [x, y]")
            normalized.append([float(pt[0]), float(pt[1]), float(pt[2]) if len(pt) > 2 else 0.0])

        params: Dict[str, Any] = {
            'points': normalized,
            'filled': filled,
            **_build_symbology(level, color, weight, style),
        }
        if filled and fill_color is not None:
            params['fill_color'] = fill_color

        return _pipe_draw(pipe_client, 'draw_shape', params)

    # ─────────────────────────────────────────────────────────────
    # Tool 5: native_place_text
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_place_text(
        x:        float,
        y:        float,
        text:     str,
        height:   float         = 2.5,
        rotation: float         = 0.0,
        z:        float         = 0.0,
        level:    Optional[str] = None,
        color:    Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Đặt text (TextElement) vào model qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Tạo TextElement với nội dung và vị trí chỉ định. Sử dụng active text style
        của MicroStation (font, spacing) trừ khi được override.

        Args:
            x, y, z:  Tọa độ điểm chèn text (origin, góc dưới trái). z mặc định 0.
            text:     Nội dung text. Hỗ trợ Unicode tiếng Việt.
            height:   Chiều cao ký tự (Master Unit). Mặc định 2.5.
            rotation: Góc xoay text (độ, ngược chiều kim đồng hồ). Mặc định 0.
            level:    Tên level (None = dùng active level).
            color:    Màu text (0-255, None = dùng active color).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "text", "level": str, "message": str}
        """
        if not text or not text.strip():
            return _err("Nội dung text không được rỗng.")
        if height <= 0:
            return _err(f"height phải > 0, nhận: {height}")
        if color is not None and not (_COLOR_MIN <= color <= _COLOR_MAX):
            return _err(f"color phải trong khoảng 0-255, nhận: {color}")

        return _pipe_draw(pipe_client, 'place_text', {
            'x': x, 'y': y, 'z': z,
            'text':     text,
            'height':   height,
            'rotation': rotation,
            **_build_symbology(level, color),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool: native_draw_point
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_draw_point(
        x:      float,
        y:      float,
        z:      float         = 0.0,
        level:  Optional[str] = None,
        color:  Optional[int] = None,
        weight: Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Vẽ điểm (PointElement) qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            x, y, z: Tọa độ điểm (z mặc định 0).
            level:   Tên level (None = dùng active level).
            color:   Màu (0-255, None = dùng active color).
            weight:  Kích thước hiển thị điểm (0-31, None = dùng active weight).

        Returns:
            JSON string: {"success": bool, "element_id": int, "type": "point", "level": str, "message": str}
        """
        err = _validate_symbology(color, weight, None)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        return _pipe_draw(pipe_client, 'draw_point', {
            'x': x, 'y': y, 'z': z,
            **_build_symbology(level, color, weight),
        })

    # ─────────────────────────────────────────────────────────────
    # Tool 6: native_move_element
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_move_element(
        element_id: int,
        dx:         float,
        dy:         float,
        dz:         float = 0.0,
    ) -> str:
        """
        **Tool native tốc độ cao** - Di chuyển một element qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Dịch chuyển element theo vector (dx, dy, dz) so với vị trí hiện tại.
        Không thay đổi hướng, kích thước hay symbology của element.

        Args:
            element_id: ID của element cần di chuyển (lấy từ kết quả draw hoặc scan).
            dx:         Khoảng dịch chuyển theo trục X (Master Unit).
            dy:         Khoảng dịch chuyển theo trục Y (Master Unit).
            dz:         Khoảng dịch chuyển theo trục Z (Master Unit). Mặc định 0.

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        try:
            response = pipe_client.send_command(
                'move_element',
                {'element_id': element_id, 'dx': dx, 'dy': dy, 'dz': dz},
            )
            ok          = response.get('status') == 'ok'
            default_msg = f"Element {element_id} đã được di chuyển ({dx}, {dy}, {dz})."
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', 'MDL lỗi khi move_element.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi di chuyển element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool: native_copy_element
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_copy_element(
        element_id: int,
        dx:         float,
        dy:         float,
        dz:         float = 0.0,
    ) -> str:
        """
        **Tool native tốc độ cao** - Nhân bản element và di chuyển bản sao theo vector (dx, dy, dz).
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            element_id: ID element gốc cần copy.
            dx, dy, dz: Khoảng dịch chuyển của bản sao mới.

        Returns:
            JSON string: {"success": bool, "new_element_id": int, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        try:
            response = pipe_client.send_command('copy_element', {
                'element_id': element_id, 'dx': dx, 'dy': dy, 'dz': dz
            })
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            data = response.get('data') or response.get('result') or {}
            new_id = data.get('new_element_id') or response.get('new_element_id')
            if ok:
                return json.dumps({
                    "success": True,
                    "new_element_id": new_id,
                    "message": f"Element {element_id} đã được sao chép thành công thành element {new_id}."
                }, ensure_ascii=False)
            else:
                return _err(response.get('message', 'MDL lỗi khi copy_element.'))
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi copy element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool: native_rotate_element
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_rotate_element(
        element_id: int,
        cx:         float,
        cy:         float,
        angle_deg:  float,
        cz:         float = 0.0,
    ) -> str:
        """
        **Tool native tốc độ cao** - Xoay element quanh tâm (cx, cy, cz) một góc angle_deg.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            element_id: ID của element cần xoay.
            cx, cy, cz: Tâm xoay.
            angle_deg:  Góc xoay theo độ (dương = ngược chiều kim đồng hồ).

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        try:
            response = pipe_client.send_command('rotate_element', {
                'element_id': element_id, 'cx': cx, 'cy': cy, 'cz': cz,
                'angle_degrees': angle_deg, 'angle_deg': angle_deg
            })
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            default_msg = f"Element {element_id} đã được xoay {angle_deg} độ quanh ({cx}, {cy})."
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', 'MDL lỗi khi rotate_element.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi xoay element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool: native_scale_element
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_scale_element(
        element_id:   int,
        cx:           float,
        cy:           float,
        scale_factor: float,
        cz:           float = 0.0,
    ) -> str:
        """
        **Tool native tốc độ cao** - Phóng to/thu nhỏ element quanh tâm (cx, cy, cz) theo tỷ lệ scale_factor.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            element_id:   ID của element cần scale.
            cx, cy, cz:   Tâm scale.
            scale_factor: Hệ số tỷ lệ (ví dụ: 2.0 = phóng to gấp đôi, 0.5 = thu nhỏ một nửa).

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")
        if scale_factor == 0.0:
            return _err("scale_factor không được bằng 0.")

        try:
            response = pipe_client.send_command('scale_element', {
                'element_id': element_id, 'cx': cx, 'cy': cy, 'cz': cz,
                'scale_x': scale_factor, 'scale_y': scale_factor, 'scale_z': scale_factor,
                'sx': scale_factor, 'sy': scale_factor, 'sz': scale_factor
            })
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            default_msg = f"Element {element_id} đã được scale theo tỷ lệ {scale_factor} quanh ({cx}, {cy})."
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', 'MDL lỗi khi scale_element.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi scale element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 7: native_delete_element
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_delete_element(element_id: int) -> str:
        """
        **Tool native tốc độ cao** - Xóa một element khỏi model qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Xóa element có ID chỉ định. Thao tác này có thể undo bằng Ctrl+Z nếu không
        nằm trong transaction. Dùng begin_transaction/end_transaction để gom nhiều xóa.

        Args:
            element_id: ID của element cần xóa (lấy từ kết quả draw hoặc native_scan_elements).

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        try:
            response    = pipe_client.send_command('delete_element', {'element_id': element_id})
            ok          = response.get('status') == 'ok'
            default_msg = f"Element {element_id} đã bị xóa thành công."
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', 'MDL lỗi khi delete_element.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi xóa element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool 8: native_change_symbology
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_change_symbology(
        element_id: int,
        level:      Optional[str] = None,
        color:      Optional[int] = None,
        weight:     Optional[int] = None,
        style:      Optional[int] = None,
    ) -> str:
        """
        **Tool native tốc độ cao** - Thay đổi symbology của element qua Named Pipe thay COM.
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Cập nhật một hoặc nhiều thuộc tính đồ họa của element. Chỉ truyền các
        thuộc tính muốn thay đổi, thuộc tính không truyền giữ nguyên giá trị cũ.

        Args:
            element_id: ID của element cần thay đổi symbology.
            level:      Tên level mới (None = giữ nguyên).
            color:      Màu mới (0-255, None = giữ nguyên).
            weight:     Độ dày nét mới (0-31, None = giữ nguyên).
            style:      Line style mới (0-7, None = giữ nguyên).

        Returns:
            JSON string: {"success": bool, "message": str}
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        if all(v is None for v in (level, color, weight, style)):
            return _err(
                "Phải truyền ít nhất 1 thuộc tính cần thay đổi "
                "(level, color, weight, hoặc style)."
            )

        err = _validate_symbology(color, weight, style)
        if err:
            return _err(f"Tham số không hợp lệ: {err}")

        sym = _build_symbology(level, color, weight, style)
        try:
            response    = pipe_client.send_command('change_symbology', {'element_id': element_id, **sym})
            ok          = response.get('status') == 'ok'
            changed     = ', '.join(f"{k}={v}" for k, v in sym.items())
            default_msg = f"Element {element_id}: symbology đã cập nhật ({changed})."
            return (
                _ok(message=response.get('message', default_msg)) if ok
                else _err(response.get('message', 'MDL lỗi khi change_symbology.'))
            )
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi change_symbology cho element {element_id}: {exc}")

    # ─────────────────────────────────────────────────────────────
    # Tool: native_get_element_details
    # ─────────────────────────────────────────────────────────────
    @mcp.tool()
    def native_get_element_details(element_id: int) -> str:
        """
        **Tool native tốc độ cao** - Lấy thông tin chi tiết một element (loại, symbology, tọa độ, bounding box).
        Yêu cầu MDL app MsNativePipe.ma đang chạy trong MicroStation.

        Args:
            element_id: ID của element cần tra cứu.

        Returns:
            JSON string chứa thông tin chi tiết của element.
        """
        if element_id <= 0:
            return _err(f"element_id không hợp lệ: {element_id}. Phải là số nguyên dương.")

        try:
            response = pipe_client.send_command('get_element_details', {'element_id': element_id})
            ok = (response.get('status') == 'ok') or (response.get('success') is True)
            if ok:
                data = response.get('data') or response.get('result') or {}
                return json.dumps({"success": True, "element_id": element_id, "details": data}, ensure_ascii=False)
            else:
                return _err(response.get('message', f'Không tìm thấy element ID={element_id}.'))
        except PipeConnectionError:
            return _err(_MDL_NOT_LOADED_MSG)
        except PipeError as exc:
            return _err(f"Lỗi pipe khi lấy chi tiết element {element_id}: {exc}")

    logger.info(
        "drawing_native: Đã đăng ký 15 native tools: "
        "native_draw_line, native_draw_linestring, native_draw_circle, native_draw_arc, "
        "native_draw_ellipse, native_draw_shape, native_draw_point, native_place_text, "
        "native_move_element, native_copy_element, native_rotate_element, native_scale_element, "
        "native_delete_element, native_change_symbology, native_get_element_details."
    )
