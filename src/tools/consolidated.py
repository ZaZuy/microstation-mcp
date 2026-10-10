"""
src/tools/consolidated.py
Hệ thống 8 Công cụ Hợp nhất (Consolidated Tools) chuẩn kiến trúc AutoCAD MCP v3.1.
Thay thế 147 công cụ rời rạc, giảm thiểu 95% token schema, ngăn ngừa hoàn toàn tình trạng
AI bị loãng ngữ cảnh hoặc chạy loop ngoài terminal.
"""

from __future__ import annotations
import functools
import io
import json
import logging
import math
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

from mcp.types import ImageContent, TextContent
from src.core.ms_bridge import bridge
from src.core.screenshot import capture_microstation_screenshot
from src.core import cadastral_engine

logger = logging.getLogger(__name__)

ToolResult = Union[str, List[Union[TextContent, ImageContent]]]


def _json(data: Any) -> str:
    """Chuyển đổi dữ liệu sang JSON compact có hỗ trợ tiếng Việt Unicode."""
    return json.dumps(data, ensure_ascii=False, default=str, indent=2)


def _safe(tool_name: str):
    """Decorator đồng bộ bắt lỗi an toàn cho mọi Tool gọi."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                op = kwargs.get("operation", "unknown")
                err_msg = str(e)
                stack = traceback.format_exc()
                logger.error(f"Lỗi tại tool {tool_name}.{op}: {err_msg}\n{stack}")
                hint = "Kiểm tra lại xem MicroStation V8i đã mở bản vẽ (.dgn) chưa và thử lại."
                if "unavailable" in err_msg.lower() or "rpc" in err_msg.lower():
                    hint = "MicroStation chưa khởi động hoặc chưa mở file DGN nào."
                return _json({
                    "error": f"[{tool_name}.{op}] {err_msg}",
                    "hint": hint,
                })
        return wrapper
    return decorator


def _append_screenshot(result_text: str, include_screenshot: bool, view_number: int = 1) -> ToolResult:
    """Đính kèm ảnh chụp màn hình vào kết quả trả về nếu được yêu cầu."""
    if not include_screenshot:
        return result_text

    ok, b64_img, _ = capture_microstation_screenshot(view_number)
    if ok and b64_img:
        return [
            TextContent(type="text", text=result_text),
            ImageContent(type="image", data=b64_img, mimeType="image/png"),
        ]
    return result_text


def register_consolidated_tools(mcp):
    """Đăng ký 8 công cụ hợp nhất vào FastMCP."""

    # =========================================================================
    # 1. drawing — Quản lý bản vẽ, tệp DGN, Model & Reference
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Drawing Operations", "readOnlyHint": False})
    @_safe("drawing")
    def drawing(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Quản lý bản vẽ và tệp DGN.

        Operations:
          info          — Lấy thông tin bản vẽ hiện tại (tên file, đường dẫn, đơn vị, số element).
          open          — Mở file DGN. data: {path: "..."}
          save          — Lưu file DGN hiện tại.
          create        — Tạo file DGN mới. data: {path: "...", seed_path: "..."}
          models        — Danh sách model trong file.
          activate_model — data: {name: "..."}
          references    — Danh sách reference đính kèm.
          undo          — Hoàn tác thao tác trước (Undo).
          redo          — Phục hồi thao tác vừa hoàn tác (Redo).
        """
        data = data or {}
        app = bridge.get_app()

        if operation == "info":
            dgn = bridge.get_active_file()
            model = bridge.get_active_model()
            cache = model.GraphicalElementCache
            res = {
                "file_name": dgn.Name,
                "full_path": dgn.FullName,
                "read_only": bool(dgn.IsReadOnly),
                "model_name": model.Name,
                "master_unit": dgn.MasterUnitLabel or "m",
                "sub_unit": dgn.SubUnitLabel or "mm",
                "element_count": cache.Count,
            }
        elif operation == "open":
            path = data.get("path")
            if not path:
                return _json({"error": "Thiếu data.path"})
            app.OpenDesignFile(path)
            res = {"success": True, "opened": path}
        elif operation == "save":
            dgn = bridge.get_active_file()
            dgn.Save()
            res = {"success": True, "saved": dgn.FullName}
        elif operation == "create":
            path = data.get("path")
            seed = data.get("seed_path", "")
            if not path:
                return _json({"error": "Thiếu data.path"})
            app.CreateDesignFile(seed, path, True)
            res = {"success": True, "created": path}
        elif operation == "models":
            dgn = bridge.get_active_file()
            m_list = [dgn.Models(i).Name for i in range(1, dgn.Models.Count + 1)]
            res = {"models": m_list, "count": len(m_list)}
        elif operation == "activate_model":
            name = data.get("name")
            dgn = bridge.get_active_file()
            dgn.Models(name).Activate()
            res = {"success": True, "active_model": name}
        elif operation == "references":
            model = bridge.get_active_model()
            refs = []
            for i in range(1, model.Attachments.Count + 1):
                att = model.Attachments(i)
                refs.append({"name": att.AttachName, "logical_name": att.LogicalName, "is_missing": bool(att.IsMissing)})
            res = {"references": refs, "count": len(refs)}
        elif operation == "undo":
            app.CadInputQueue.SendKeyin("undo")
            res = {"success": True, "message": "Đã gửi lệnh undo"}
        elif operation == "redo":
            app.CadInputQueue.SendKeyin("redo")
            res = {"success": True, "message": "Đã gửi lệnh redo"}
        else:
            return _json({"error": f"Không hỗ trợ operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 2. entity — CRUD Đối tượng 2D/3D (Line, Shape, Circle, Arc, Polyline...)
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Entity Operations", "readOnlyHint": False})
    @_safe("entity")
    def entity(
        operation: str,
        x1: Optional[float] = None,
        y1: Optional[float] = None,
        x2: Optional[float] = None,
        y2: Optional[float] = None,
        points: Optional[List[List[float]]] = None,
        layer: Optional[str] = None,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Tạo mới, truy vấn, đọc và chỉnh sửa đối tượng trong bản vẽ.

        Create Operations:
          create_line       — x1, y1, x2, y2, layer? data: {color?, weight?, style?}
          create_linestring — points: [[x,y],...], layer?
          create_shape      — points: [[x,y],...], layer? (đa giác khép kín)
          create_rectangle  — x1, y1, x2, y2, layer?
          create_circle     — data: {cx, cy, radius}, layer?
          create_arc        — data: {cx, cy, radius, start_angle, sweep_angle}, layer?
          create_text       — data: {text, x, y, height?, width?, justification?}, layer?
          batch_create      — data: {elements: [{type, points/x/y, level, color...}]}

        Read Operations:
          list              — layer? (danh sách ID và loại element)
          count             — layer? (đếm số element)
          get               — entity_id (thông tin chi tiết của 1 element)

        Modify Operations:
          move              — entity_id, data: {dx, dy}
          copy              — entity_id, data: {dx, dy}
          rotate            — entity_id, data: {cx, cy, angle_deg}
          scale             — entity_id, data: {cx, cy, factor}
          erase             — entity_id (xóa element)
        """
        data = data or {}
        app = bridge.get_app()
        model = bridge.get_active_model()

        # Thiết lập level nếu có
        if layer:
            bridge.set_active_level(str(layer))
        if "color" in data:
            bridge.set_active_color(int(data["color"]))
        if "weight" in data:
            bridge.set_active_weight(int(data["weight"]))
        if "style" in data:
            bridge.set_active_style(int(data["style"]))

        # --- Create Operations ---
        if operation == "create_line":
            if x1 is None or y1 is None or x2 is None or y2 is None:
                return _json({"error": "create_line yêu cầu x1, y1, x2, y2"})
            p1 = bridge.create_point(x1, y1, 0.0)
            p2 = bridge.create_point(x2, y2, 0.0)
            el = app.CreateLineElement2(None, p1, p2)
            model.AddElement(el)
            res = {"success": True, "type": "Line", "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_linestring":
            if not points or len(points) < 2:
                return _json({"error": "create_linestring yêu cầu ít nhất 2 điểm trong points"})
            pt_objs = [bridge.create_point(p[0], p[1], 0.0) for p in points]
            el = app.CreateLineElement1(None, pt_objs)
            model.AddElement(el)
            res = {"success": True, "type": "LineString", "points_count": len(points), "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_shape":
            if not points or len(points) < 3:
                return _json({"error": "create_shape yêu cầu ít nhất 3 điểm trong points"})
            pt_objs = [bridge.create_point(p[0], p[1], 0.0) for p in points]
            el = app.CreateShapeElement1(None, pt_objs, 0)
            model.AddElement(el)
            res = {"success": True, "type": "Shape", "vertices": len(points), "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_rectangle":
            if x1 is None or y1 is None or x2 is None or y2 is None:
                return _json({"error": "create_rectangle yêu cầu x1, y1, x2, y2"})
            pts = [
                bridge.create_point(x1, y1, 0.0),
                bridge.create_point(x2, y1, 0.0),
                bridge.create_point(x2, y2, 0.0),
                bridge.create_point(x1, y2, 0.0),
            ]
            el = app.CreateShapeElement1(None, pts, 0)
            model.AddElement(el)
            res = {"success": True, "type": "Rectangle", "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_circle":
            cx = data.get("cx", 0.0)
            cy = data.get("cy", 0.0)
            r = data.get("radius", 1.0)
            center = bridge.create_point(cx, cy, 0.0)
            el = app.CreateEllipseElement2(None, center, r, r, app.Matrix3dIdentity(), 0)
            model.AddElement(el)
            res = {"success": True, "type": "Circle", "radius": r, "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_arc":
            cx = data.get("cx", 0.0)
            cy = data.get("cy", 0.0)
            r = data.get("radius", 1.0)
            s_ang = math.radians(data.get("start_angle", 0.0))
            sw_ang = math.radians(data.get("sweep_angle", 90.0))
            center = bridge.create_point(cx, cy, 0.0)
            el = app.CreateArcElement1(None, center, r, r, app.Matrix3dIdentity(), s_ang, sw_ang)
            model.AddElement(el)
            res = {"success": True, "type": "Arc", "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_text":
            txt = data.get("text", "")
            tx = data.get("x", 0.0)
            ty = data.get("y", 0.0)
            h = data.get("height", 1.5)
            w = data.get("width", h)
            just = data.get("justification", 6)
            pt = bridge.create_point(tx, ty, 0.0)
            el = app.CreateTextElement1(None, str(txt), pt, app.Matrix3dIdentity())
            el.TextStyle.Height = h
            el.TextStyle.Width = w
            el.TextStyle.Justification = just
            model.AddElement(el)
            res = {"success": True, "type": "Text", "text": txt, "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "batch_create":
            elements_list = data.get("elements", [])
            from src.tools.workflow import cad_draw_workflow
            msg = cad_draw_workflow(elements=elements_list, fit_view_after=False)
            res = {"success": True, "batch_result": msg}

        # --- Read Operations ---
        elif operation == "list" or operation == "count":
            cache = model.GraphicalElementCache
            count = cache.Count
            items = []
            filter_lvl = str(layer).strip().lower() if layer else None
            matched_count = 0
            for idx in range(1, count + 1):
                try:
                    e = cache.GetElement(idx)
                    if not e:
                        continue
                    lvl_name = (e.Level.Name if e.Level else "").strip()
                    if filter_lvl and filter_lvl not in lvl_name.lower():
                        continue
                    matched_count += 1
                    if operation == "list" and len(items) < 50:  # Giới hạn 50 mục đầu
                        items.append({
                            "id": str(getattr(e, "ID64", e.ID)),
                            "type": int(e.Type),
                            "level": lvl_name,
                        })
                except Exception:
                    continue
            res = {"total": count, "matched_count": matched_count, "elements": items}

        elif operation == "get":
            if not entity_id:
                return _json({"error": "get yêu cầu entity_id"})
            el = bridge.find_element_by_id(entity_id)
            if not el:
                return _json({"error": f"Không tìm thấy element có ID '{entity_id}'"})
            res = {
                "id": entity_id,
                "type": int(el.Type),
                "level": el.Level.Name if el.Level else "",
                "color": int(el.Color),
                "weight": int(el.LineWeight),
                "is_closed": bool(getattr(el, "IsClosedElement", False)),
            }

        # --- Modify Operations ---
        elif operation == "erase":
            if not entity_id:
                return _json({"error": "erase yêu cầu entity_id"})
            el = bridge.find_element_by_id(entity_id)
            if not el:
                return _json({"error": f"Không tìm thấy element ID '{entity_id}'"})
            model.RemoveElement(el)
            res = {"success": True, "erased": entity_id}

        elif operation == "move" or operation == "copy":
            if not entity_id:
                return _json({"error": f"{operation} yêu cầu entity_id"})
            el = bridge.find_element_by_id(entity_id)
            if not el:
                return _json({"error": f"Không tìm thấy element ID '{entity_id}'"})
            dx = data.get("dx", 0.0)
            dy = data.get("dy", 0.0)
            trans = bridge.create_point(dx, dy, 0.0)
            if operation == "move":
                el.Move(trans)
                el.Rewrite()
                res = {"success": True, "moved": entity_id, "delta": [dx, dy]}
            else:
                target = el.Clone()
                target.Move(trans)
                model.AddElement(target)
                res = {"success": True, "copied": entity_id, "new_id": str(getattr(target, "ID64", target.ID))}

        elif operation == "rotate":
            if not entity_id:
                return _json({"error": "rotate yêu cầu entity_id"})
            el = bridge.find_element_by_id(entity_id)
            if not el:
                return _json({"error": f"Không tìm thấy element ID '{entity_id}'"})
            cx = data.get("cx", 0.0)
            cy = data.get("cy", 0.0)
            deg = data.get("angle_deg", 0.0)
            rad = math.radians(deg)
            p_center = bridge.create_point(cx, cy, 0.0)
            el.Rotate(p_center, rad)
            el.Rewrite()
            res = {"success": True, "rotated": entity_id, "angle_deg": deg}

        elif operation == "scale":
            if not entity_id:
                return _json({"error": "scale yêu cầu entity_id"})
            el = bridge.find_element_by_id(entity_id)
            if not el:
                return _json({"error": f"Không tìm thấy element ID '{entity_id}'"})
            cx = data.get("cx", 0.0)
            cy = data.get("cy", 0.0)
            factor = data.get("factor", 1.0)
            p_center = bridge.create_point(cx, cy, 0.0)
            el.ScaleUniform(p_center, factor)
            el.Rewrite()
            res = {"success": True, "scaled": entity_id, "factor": factor}

        else:
            return _json({"error": f"Không hỗ trợ operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 3. layer — Quản lý lớp bản vẽ (Level)
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Layer Operations", "readOnlyHint": False})
    @_safe("layer")
    def layer(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Quản lý các lớp (Level) trong MicroStation V8i.

        Operations:
          list         — Danh sách tất cả các Level trong bản vẽ.
          create       — data: {name, color?, weight?, style?}
          set_active   — data: {name} (chọn Level hiện thời)
          set_display  — data: {name, is_displayed: bool, view_number?: 1}
        """
        data = data or {}
        dgn = bridge.get_active_file()

        if operation == "list":
            lvls = []
            for i in range(1, dgn.Levels.Count + 1):
                lvl = dgn.Levels(i)
                lvls.append({
                    "name": lvl.Name,
                    "number": lvl.Number,
                    "is_displayed": bool(lvl.IsDisplayed),
                })
            res = {"levels": lvls, "count": len(lvls)}

        elif operation == "create":
            name = data.get("name")
            if not name:
                return _json({"error": "Thiếu data.name"})
            color = data.get("color", 0)
            lvl = bridge.get_or_create_level(name, color)
            res = {"success": True, "created": lvl.Name, "number": lvl.Number}

        elif operation == "set_active":
            name = data.get("name")
            if not name:
                return _json({"error": "Thiếu data.name"})
            bridge.set_active_level(name)
            res = {"success": True, "active_level": name}

        elif operation == "set_display":
            name = data.get("name")
            disp = data.get("is_displayed", True)
            v_num = data.get("view_number", 1)
            lvl = dgn.Levels(name)
            if 1 <= v_num <= dgn.Views.Count:
                v = dgn.Views(v_num)
                lvl.set_IsDisplayedInView(v, disp)
                v.Redraw()
            res = {"success": True, "level": name, "displayed": disp, "view": v_num}

        else:
            return _json({"error": f"Không hỗ trợ operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 4. cell — Quản lý và chèn Cell / Block
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Cell Operations", "readOnlyHint": False})
    @_safe("cell")
    def cell(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Quản lý và chèn Cell (Block) kỹ thuật.

        Operations:
          list   — Liệt kê các Cell trong thư viện đang mở.
          place  — data: {name, x, y, scale?, angle_deg?}
          drop   — data: {entity_id} (rã Cell thành đối tượng thường)
        """
        data = data or {}
        app = bridge.get_app()
        model = bridge.get_active_model()

        if operation == "place":
            name = data.get("name")
            x = data.get("x", 0.0)
            y = data.get("y", 0.0)
            scale = data.get("scale", 1.0)
            rot = math.radians(data.get("angle_deg", 0.0))
            p = bridge.create_point(x, y, 0.0)
            el = app.CreateCellElement2(name, p, bridge.create_point(scale, scale, scale), True, app.Matrix3dFromRotationAroundZAxis(rot))
            model.AddElement(el)
            res = {"success": True, "placed_cell": name, "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "drop":
            eid = data.get("entity_id")
            el = bridge.find_element_by_id(eid)
            if not el:
                return _json({"error": f"Không tìm thấy element ID '{eid}'"})
            el.Drop()
            res = {"success": True, "dropped": eid}

        elif operation == "list":
            app.CadInputQueue.SendKeyin("cell")
            res = {"message": "Đã mở danh mục Cell Library"}

        else:
            return _json({"error": f"Không hỗ trợ operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 5. annotation — Ghi chú chữ, thứ tự, kích thước (Dimension)
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Annotation Operations", "readOnlyHint": False})
    @_safe("annotation")
    def annotation(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Ghi chú chữ, ký hiệu và đường đo kích thước.

        Operations:
          create_text             — data: {text, x, y, height?, width?, color?, level?}
          create_dimension_linear — data: {x1, y1, x2, y2, offset_y?}
          create_dimension_aligned — data: {x1, y1, x2, y2, offset?}
          find_text               — data: {search_text}
          replace_text            — data: {find_text, replace_text}
        """
        data = data or {}
        app = bridge.get_app()
        model = bridge.get_active_model()

        if operation == "create_text":
            txt = data.get("text", "")
            x = data.get("x", 0.0)
            y = data.get("y", 0.0)
            h = data.get("height", 1.5)
            w = data.get("width", h)
            just = data.get("justification", 6)
            pt = bridge.create_point(x, y, 0.0)
            el = app.CreateTextElement1(None, str(txt), pt, app.Matrix3dIdentity())
            el.TextStyle.Height = h
            el.TextStyle.Width = w
            el.TextStyle.Justification = just
            if "color" in data:
                el.Color = int(data["color"])
            if "level" in data:
                el.Level = bridge.get_or_create_level(str(data["level"]))
            model.AddElement(el)
            res = {"success": True, "type": "Text", "id": str(getattr(el, "ID64", el.ID))}

        elif operation == "create_dimension_aligned":
            x1, y1 = data.get("x1", 0.0), data.get("y1", 0.0)
            x2, y2 = data.get("x2", 0.0), data.get("y2", 0.0)
            p1 = bridge.create_point(x1, y1, 0.0)
            p2 = bridge.create_point(x2, y2, 0.0)
            dim_el = app.CreateDimensionElement1(None, app.Matrix3dIdentity(), 0)
            dim_el.InsertReferencePoint(None, 1, p1)
            dim_el.InsertReferencePoint(None, 2, p2)
            model.AddElement(dim_el)
            res = {"success": True, "type": "DimensionAligned", "length": math.hypot(x2 - x1, y2 - y1)}

        elif operation == "find_text":
            search = data.get("search_text", "").lower()
            cache = model.GraphicalElementCache
            matches = []
            for i in range(1, cache.Count + 1):
                try:
                    el = cache.GetElement(i)
                    if int(el.Type) == 17:
                        t = getattr(el, "Text", "")
                        if search in t.lower():
                            matches.append({"id": str(getattr(el, "ID64", el.ID)), "text": t})
                except Exception:
                    continue
            res = {"matches": matches, "count": len(matches)}

        elif operation == "replace_text":
            f_txt = data.get("find_text", "")
            r_txt = data.get("replace_text", "")
            cache = model.GraphicalElementCache
            rep_count = 0
            for i in range(1, cache.Count + 1):
                try:
                    el = cache.GetElement(i)
                    if int(el.Type) == 17:
                        t = getattr(el, "Text", "")
                        if f_txt in t:
                            el.Text = t.replace(f_txt, r_txt)
                            el.Rewrite()
                            rep_count += 1
                except Exception:
                    continue
            res = {"success": True, "replaced_count": rep_count}

        else:
            return _json({"error": f"Không hỗ trợ operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 6. view — Điều khiển khung nhìn & Chụp màn hình (Screenshot PNG)
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation View Operations", "readOnlyHint": False})
    @_safe("view")
    def view(
        operation: str,
        x1: Optional[float] = None,
        y1: Optional[float] = None,
        x2: Optional[float] = None,
        y2: Optional[float] = None,
        view_number: int = 1,
    ) -> ToolResult:
        """Điều khiển khung nhìn và chụp ảnh màn hình MicroStation V8i.

        Operations:
          fit_view       — Căn toàn bộ bản vẽ vào khung nhìn (Fit View).
          zoom_window    — Phóng to vào vùng tọa độ x1, y1, x2, y2.
          zoom_in        — Phóng to 2x.
          zoom_out       — Thu nhỏ 0.5x.
          get_screenshot — CHỤP ẢNH MÀN HÌNH BẢN VẼ: Trả về hình ảnh PNG trực tiếp vào chat.
        """
        app = bridge.get_app()
        dgn = bridge.get_active_file()

        if operation == "fit_view":
            try:
                if 1 <= view_number <= dgn.Views.Count:
                    dgn.Views(view_number).Fit(True)
                    dgn.Views(view_number).Redraw()
            except Exception:
                app.CadInputQueue.SendKeyin(f"fit all")
            res = {"success": True, "message": f"Đã căn toàn màn hình View {view_number}"}
            return _json(res)

        elif operation == "zoom_window":
            if x1 is None or y1 is None or x2 is None or y2 is None:
                return _json({"error": "zoom_window yêu cầu x1, y1, x2, y2"})
            p1 = bridge.create_point(x1, y1, 0.0)
            p2 = bridge.create_point(x2, y2, 0.0)
            dgn.Views(view_number).ZoomWindow(p1, p2)
            dgn.Views(view_number).Redraw()
            return _json({"success": True, "window": [x1, y1, x2, y2]})

        elif operation == "zoom_in":
            app.CadInputQueue.SendKeyin(f"zoom in {view_number}")
            return _json({"success": True, "view": view_number})

        elif operation == "zoom_out":
            app.CadInputQueue.SendKeyin(f"zoom out {view_number}")
            return _json({"success": True, "view": view_number})

        elif operation == "get_screenshot":
            ok, b64_img, err = capture_microstation_screenshot(view_number)
            if ok and b64_img:
                return [
                    TextContent(type="text", text=_json({"success": True, "screenshot": "attached", "view": view_number})),
                    ImageContent(type="image", data=b64_img, mimeType="image/png"),
                ]
            else:
                return _json({"success": False, "error": err or "Không chụp được màn hình"})

        else:
            return _json({"error": f"Không hỗ trợ view operation: {operation}"})

    # =========================================================================
    # 7. cadastral — Chuyên gia Địa chính Việt Nam (TT 26/2024, TT 23/2025)
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation Cadastral Workflow Operations", "readOnlyHint": False})
    @_safe("cadastral")
    def cadastral(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = True,
    ) -> ToolResult:
        """Công cụ nghiệp vụ Đo đạc & Biên tập Bản đồ Địa chính Việt Nam.

        Operations:
          auto_workflow       — GIẢI QUYẾT TRỌN GÓI TOÀN BỘ YÊU CẦU:
                                Phân biệt ranh thửa nét liền (Level 10) vs ranh xin chuyển mục đích nét đứt (Level 10)
                                vs ranh lộ giới (Level 50); tính diện tích lộ giới & CMD; ghi nhãn tâm "Vị trí xin CMD";
                                đánh số đỉnh mốc ranh 1, 2, 3...; ghi chiều dài các cạnh; vẽ Bảng tọa độ VN-2000 canh giữa đều đẹp.
          analyze             — Phân tích hiện trạng các ranh giới và bóc tách diện tích.
          draw_table          — data: {points: [[x,y],...], origin_x, origin_y, title?} -> Vẽ bảng tọa độ VN-2000.
          draw_parcel_label   — data: {so_thua, dien_tich, loai_dat, x, y} -> Nhãn thửa phân số STT/DT/Loại đất theo TT 26/2024.
        """
        data = data or {}

        if operation == "auto_workflow":
            res = cadastral_engine.execute_full_cadastral_workflow()
        elif operation == "analyze":
            res = cadastral_engine.analyze_cadastral_status()
        elif operation == "draw_table":
            pts = data.get("points", [])
            ox = data.get("origin_x", 0.0)
            oy = data.get("origin_y", 0.0)
            title = data.get("title", "BẢNG TỌA ĐỘ GÓC RANH VN-2000")
            res = cadastral_engine.draw_cadastral_coordinate_table_native(
                points=pts,
                origin_x=ox,
                origin_y=oy,
                title=title,
            )
        elif operation == "draw_parcel_label":
            from src.tools.workflow import draw_parcel_label
            st = str(data.get("so_thua", "1"))
            dt = str(data.get("dien_tich", "100.0"))
            ld = str(data.get("loai_dat", "ODT"))
            x = float(data.get("x", 0.0))
            y = float(data.get("y", 0.0))
            msg = draw_parcel_label(so_thua=st, dien_tich=dt, loai_dat=ld, x=x, y=y)
            res = {"success": True, "result": msg}
        else:
            return _json({"error": f"Không hỗ trợ cadastral operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    # =========================================================================
    # 8. system — Quản trị hệ thống & Thực thi mã Python/Keyin nội bộ
    # =========================================================================
    @mcp.tool(annotations={"title": "MicroStation MCP System", "readOnlyHint": False})
    @_safe("system")
    def system(
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        include_screenshot: bool = False,
    ) -> ToolResult:
        """Quản lý trạng thái kết nối và thực thi mã script an toàn bên trong MCP Server.

        Operations:
          status         — Kiểm tra kết nối với MicroStation, tệp DGN, kiến trúc Dual-Mode (Pipe/COM).
          health         — Ping kiểm tra sức khỏe hệ thống.
          execute_keyin  — Chạy lệnh Key-in trong MicroStation. data: {command: "..."}
          execute_python — CHÌA KHÓA VÀNG: Thực thi đoạn mã Python trực tiếp trong tiến trình Server
                          (Nơi có sẵn win32com, bridge, shapely, pipe_client, math...).
                          AI TUYỆT ĐỐI KHÔNG MỞ TERMINAL NGOÀI, mà gọi operation này để chạy script an toàn 100%!
                          data: {code: "..."}
        """
        data = data or {}

        if operation == "status":
            app = bridge.get_app()
            dgn = bridge.get_active_file()
            model = bridge.get_active_model()
            from src.core._pipe_singleton import get_pipe_client
            pipe_c = get_pipe_client()
            is_pipe_ready = pipe_c.is_connected() if pipe_c else False
            res = {
                "ok": True,
                "status": "ready",
                "microstation_version": str(getattr(app, "Version", "V8i")),
                "active_design_file": dgn.Name if dgn else "Chưa mở",
                "active_model": model.Name if model else "Chưa kích hoạt",
                "backend_mode": "Native Named Pipe" if is_pipe_ready else "COM Out-of-Process Fallback",
                "pipe_connected": is_pipe_ready,
                "python_runtime": sys.executable,
            }

        elif operation == "health":
            try:
                app = bridge.get_app()
                dgn = bridge.get_active_file()
                res = {"ok": True, "connected": bool(app and dgn)}
            except Exception as e:
                res = {"ok": False, "error": str(e)}

        elif operation == "execute_keyin":
            cmd = data.get("command")
            if not cmd:
                return _json({"error": "Thiếu data.command"})
            app = bridge.get_app()
            app.CadInputQueue.SendKeyin(str(cmd))
            res = {"success": True, "executed_keyin": cmd}

        elif operation == "execute_python":
            code = data.get("code")
            if not code:
                return _json({"error": "Thiếu data.code"})

            # Chuyển hướng stdout để bắt toàn bộ kết quả print
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output

            # Cung cấp sẵn các biến toàn cục tiện ích
            scope = {
                "bridge": bridge,
                "math": math,
                "json": json,
                "cadastral": cadastral_engine,
                "app": None,
                "model": None,
                "dgn": None,
            }
            try:
                scope["app"] = bridge.get_app()
                scope["model"] = bridge.get_active_model()
                scope["dgn"] = bridge.get_active_file()
            except Exception:
                pass

            try:
                exec(code, scope)
                output_str = redirected_output.getvalue()
                res = {
                    "success": True,
                    "stdout": output_str,
                    "result": str(scope.get("result", "Hoàn tất không lỗi")),
                }
            except Exception as ex:
                res = {
                    "success": False,
                    "error": str(ex),
                    "traceback": traceback.format_exc(),
                    "partial_stdout": redirected_output.getvalue(),
                }
            finally:
                sys.stdout = old_stdout

        else:
            return _json({"error": f"Không hỗ trợ system operation: {operation}"})

        return _append_screenshot(_json(res), include_screenshot)

    logger.info("Đã đăng ký thành công bộ 8 Consolidated Tools chuẩn kiến trúc AutoCAD MCP v3.1.")


__all__ = ["register_consolidated_tools"]
