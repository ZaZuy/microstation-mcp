"""
src/tools/file_model.py
Các công cụ quản lý File DGN, Model (Không gian vẽ/Trang in) và Reference (File đính kèm tham chiếu Xref).
"""

import os
from typing import List, Dict, Any, Optional
from src.core.ms_bridge import bridge


def register_file_model_tools(mcp):
    """Đăng ký các tool quản lý File, Model và Reference vào MCP Server."""

    @mcp.tool
    def open_design_file(file_path: str, read_only: bool = False) -> str:
        """
        Mở một file bản vẽ DGN trên máy tính vào MicroStation V8i.

        :param file_path: Đường dẫn đầy đủ tới file (.dgn)
        :param read_only: Mở ở chế độ chỉ đọc (mặc định False)
        """
        if not os.path.exists(file_path):
            return f"Lỗi: Không tìm thấy file tại đường dẫn '{file_path}'"

        app = bridge.get_app(require_file=False)
        try:
            app.OpenDesignFile(str(file_path), bool(read_only))
            return f"Đã mở thành công file bản vẽ: '{file_path}'"
        except Exception as ex:
            return f"Lỗi khi mở file '{file_path}': {ex}"

    @mcp.tool
    def save_design_file() -> str:
        """
        Lưu các thay đổi của file bản vẽ DGN đang mở vào ổ đĩa.
        """
        app = bridge.get_app(require_file=True)
        try:
            dgn = bridge.get_active_file()
            dgn.Save()
            return f"Đã lưu thành công file: {dgn.Name}"
        except Exception:
            app.CadInputQueue.SendKeyin("save design")
            return "Đã gửi lệnh lưu bản vẽ (save design)."

    @mcp.tool
    def create_new_dgn(new_file_path: str, seed_file_path: Optional[str] = None) -> str:
        """
        Tạo mới một file bản vẽ DGN từ file mẫu (seed file).

        :param new_file_path: Đường dẫn lưu file DGN mới
        :param seed_file_path: Đường dẫn file mẫu .dgn (nếu None sẽ lấy seed mặc định của MicroStation)
        """
        app = bridge.get_app(require_file=False)
        seed = seed_file_path if seed_file_path and os.path.exists(seed_file_path) else ""

        try:
            if seed:
                app.CreateDesignFile(seed, new_file_path, True)
            else:
                # Dùng key-in new file
                app.CadInputQueue.SendKeyin(f'newfile "{new_file_path}"')
            return f"Đã tạo thành công file DGN mới: '{new_file_path}'"
        except Exception as ex:
            return f"Lỗi khi tạo file mới: {ex}"

    @mcp.tool
    def get_models() -> List[Dict[str, Any]]:
        """
        Liệt kê danh sách tất cả các Models (không gian thiết kế / trang in Sheet) trong file DGN hiện tại.
        """
        dgn = bridge.get_active_file()
        active_model = bridge.get_active_model()
        models_list = []

        try:
            for i in range(1, dgn.Models.Count + 1):
                try:
                    m = dgn.Models.Item(i)
                    models_list.append({
                        "name": m.Name,
                        "description": getattr(m, "Description", ""),
                        "is_3d": bool(m.Is3D),
                        "is_active": (m.Name == active_model.Name),
                    })
                except Exception:
                    continue
        except Exception as ex:
            return [{"error": f"Không thể lấy danh sách Models: {ex}"}]

        return models_list

    @mcp.tool
    def activate_model(model_name: str) -> str:
        """
        Chuyển đổi (kích hoạt) sang một Model khác trong cùng file DGN.

        :param model_name: Tên Model cần chuyển tới
        """
        dgn = bridge.get_active_file()
        try:
            target_model = dgn.Models.Item(model_name)
            if not target_model:
                return f"Lỗi: Không tìm thấy Model có tên '{model_name}'"
            target_model.Activate()
            return f"Đã kích hoạt Model: '{model_name}'"
        except Exception as ex:
            return f"Lỗi khi chuyển Model: {ex}"

    @mcp.tool
    def create_model(
        model_name: str,
        description: str = "",
        is_3d: bool = False,
    ) -> str:
        """
        Tạo mới một Model trong file DGN hiện tại.

        :param model_name: Tên Model mới
        :param description: Mô tả cho Model
        :param is_3d: True nếu là không gian 3D, False nếu là 2D
        """
        dgn = bridge.get_active_file()
        try:
            # Type 0 = MsdModelTypeDesign
            new_m = dgn.Models.Add(0, str(model_name), str(description), bool(is_3d))
            return f"Đã tạo thành công Model '{model_name}' ({'3D' if is_3d else '2D'})"
        except Exception as ex:
            return f"Lỗi khi tạo Model: {ex}"

    @mcp.tool
    def get_references() -> List[Dict[str, Any]]:
        """
        Liệt kê tất cả các file bản vẽ tham chiếu (Reference Files / Xrefs) đang được đính kèm vào Model hiện tại.
        """
        model = bridge.get_active_model()
        refs_list = []

        try:
            attachments = model.Attachments
            for i in range(1, attachments.Count + 1):
                try:
                    att = attachments.Item(i)
                    refs_list.append({
                        "logical_name": getattr(att, "LogicalName", ""),
                        "attach_name": getattr(att, "AttachName", ""),
                        "is_displayed": bool(getattr(att, "IsDisplayed", True)),
                        "scale": round(getattr(att, "ScaleFactor", 1.0), 4),
                    })
                except Exception:
                    continue
        except Exception as ex:
            return [{"error": f"Lỗi khi đọc danh sách references: {ex}"}]

        return refs_list

    @mcp.tool
    def attach_reference(
        file_path: str,
        model_name: str = "Default",
        logical_name: Optional[str] = None,
    ) -> str:
        """
        Đính kèm một file DGN hoặc DWG làm bản vẽ tham chiếu (Reference Xref) vào Model hiện tại.

        :param file_path: Đường dẫn file cần đính kèm
        :param model_name: Tên Model trong file nguồn (mặc định 'Default')
        :param logical_name: Tên gợi nhớ logic
        """
        if not os.path.exists(file_path):
            return f"Lỗi: Không tìm thấy file tham chiếu tại '{file_path}'"

        model = bridge.get_active_model()
        log_name = logical_name if logical_name else os.path.splitext(os.path.basename(file_path))[0]

        try:
            model.Attachments.Add(str(file_path), str(model_name), str(log_name), "", None, None)
            return f"Đã đính kèm file tham chiếu '{file_path}' với tên '{log_name}'"
        except Exception as ex:
            # Fallback dùng Key-in
            app = bridge.get_app()
            app.CadInputQueue.SendKeyin(f'reference attach "{file_path}"')
            return f"Đã gửi lệnh đính kèm reference '{file_path}'."

    @mcp.tool
    def detach_reference(logical_name: str) -> str:
        """
        Gỡ bỏ một file bản vẽ tham chiếu (Reference Detach) theo tên LogicalName hoặc AttachName.

        :param logical_name: Tên file tham chiếu cần gỡ bỏ
        """
        model = bridge.get_active_model()
        try:
            attachments = model.Attachments
            for i in range(1, attachments.Count + 1):
                att = attachments.Item(i)
                if att.LogicalName.lower() == logical_name.lower() or att.AttachName.lower() == logical_name.lower():
                    attachments.Remove(i)
                    return f"Đã gỡ bỏ file tham chiếu '{logical_name}'."
            return f"Không tìm thấy reference có tên '{logical_name}'."
        except Exception as ex:
            return f"Lỗi khi gỡ bỏ reference: {ex}"

    @mcp.tool
    def scan_reference_elements(
        reference_name: Optional[str] = None,
        level: Optional[str] = None,
        element_type: Optional[str] = None,
        max_count: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Quét và lấy danh sách các phần tử hình học, ranh giới, chữ bên trong các file bản vẽ tham chiếu (Reference Files / Xrefs) đang được đính kèm.

        :param reference_name: Tên file tham chiếu hoặc Logical Name (nếu None sẽ quét tất cả file tham chiếu đang đính kèm và hiển thị)
        :param level: Lọc theo tên level (nếu None sẽ lấy tất cả)
        :param element_type: Lọc theo loại ('Line', 'LineString', 'Shape', 'Text', 'TextNode', 'Cell'...)
        :param max_count: Số lượng tối đa phần tử trả về (mặc định 300)
        """
        model = bridge.get_active_model()
        results = []
        count = 0

        type_map = {
            "line": 3,
            "linestring": 4,
            "shape": 6,
            "textnode": 7,
            "complexstring": 12,
            "complexshape": 14,
            "ellipse": 15,
            "arc": 16,
            "text": 17,
            "cell": 2,
        }
        target_type_id = type_map.get(element_type.lower()) if element_type else None

        try:
            attachments = model.Attachments
            for i in range(1, attachments.Count + 1):
                try:
                    att = attachments.Item(i)
                except Exception:
                    continue

                if not att:
                    continue

                attach_name = getattr(att, "AttachName", "")
                logical_name = getattr(att, "LogicalName", "")

                if reference_name:
                    ref_query = str(reference_name).lower()
                    if ref_query not in attach_name.lower() and ref_query not in logical_name.lower():
                        continue

                if not reference_name and not getattr(att, "IsDisplayed", True):
                    continue

                # Quét phần tử qua Scan() hoặc GraphicalElementCache
                ee = None
                try:
                    ee = att.Scan()
                except Exception:
                    pass

                if ee:
                    while ee.MoveNext():
                        try:
                            el = ee.Current
                        except Exception:
                            continue
                        if not el:
                            continue

                        lvl_name = el.Level.Name if el.Level else ""
                        if level and lvl_name.lower() != str(level).lower():
                            continue

                        el_type = int(el.Type)
                        if target_type_id is not None and el_type != target_type_id:
                            continue

                        item = {
                            "reference_file": attach_name,
                            "id": str(getattr(el, "ID64", getattr(el, "ID", ""))),
                            "type": el_type,
                            "level": lvl_name,
                            "color": getattr(el, "Color", None),
                            "weight": getattr(el, "LineWeight", None),
                        }

                        try:
                            rng = el.Range
                            item["bounding_box"] = {
                                "min_x": round(rng.Low.X, 3),
                                "min_y": round(rng.Low.Y, 3),
                                "max_x": round(rng.High.X, 3),
                                "max_y": round(rng.High.Y, 3),
                            }
                        except Exception:
                            pass

                        if el_type == 17:  # Text
                            try:
                                item["type_name"] = "Text"
                                item["text"] = el.AsTextElement().Text
                                pt = el.AsTextElement().Origin
                                item["origin"] = [round(pt.X, 3), round(pt.Y, 3)]
                            except Exception:
                                pass
                        elif el_type == 7:  # TextNode
                            try:
                                item["type_name"] = "TextNode"
                                lines = []
                                tne = el.AsTextNodeElement()
                                for li in range(1, tne.TextLinesCount + 1):
                                    lines.append(tne.TextLine(li))
                                item["text"] = "\n".join(lines)
                                pt = tne.Origin
                                item["origin"] = [round(pt.X, 3), round(pt.Y, 3)]
                            except Exception:
                                pass
                        elif el_type == 3:  # Line
                            try:
                                item["type_name"] = "Line"
                                le = el.AsLineElement()
                                p1 = le.StartPoint
                                p2 = le.EndPoint
                                item["points"] = [[round(p1.X, 3), round(p1.Y, 3)], [round(p2.X, 3), round(p2.Y, 3)]]
                                item["length"] = round(le.Length, 3)
                            except Exception:
                                pass
                        elif el_type == 4:  # LineString
                            try:
                                item["type_name"] = "LineString"
                                lse = el.AsLineStringElement()
                                pts = []
                                try:
                                    cnt = getattr(lse, "VerticesCount", 0)
                                    for vi in range(1, cnt + 1):
                                        v = lse.Vertex(vi)
                                        pts.append([round(v.X, 3), round(v.Y, 3)])
                                except Exception:
                                    pass
                                if not pts:
                                    v_raw = lse.GetVertices()
                                    pts = [[round(p.X, 3), round(p.Y, 3)] for p in v_raw]
                                item["points"] = pts
                                item["length"] = round(lse.Length, 3)
                            except Exception:
                                pass
                        elif el_type == 6:  # Shape
                            try:
                                item["type_name"] = "Shape"
                                se = el.AsShapeElement()
                                pts = []
                                try:
                                    cnt = getattr(se, "VerticesCount", 0)
                                    for vi in range(1, cnt + 1):
                                        v = se.Vertex(vi)
                                        pts.append([round(v.X, 3), round(v.Y, 3)])
                                except Exception:
                                    pass
                                if not pts:
                                    v_raw = se.GetVertices()
                                    pts = [[round(p.X, 3), round(p.Y, 3)] for p in v_raw]
                                item["points"] = pts
                                item["area"] = round(se.Area, 3)
                                item["length"] = round(se.Perimeter, 3)
                            except Exception:
                                pass
                        elif el_type == 14:  # ComplexShape
                            try:
                                item["type_name"] = "ComplexShape"
                                item["area"] = round(el.AsClosedElement().Area, 3)
                            except Exception:
                                pass
                        elif el_type == 12:  # ComplexString
                            try:
                                item["type_name"] = "ComplexString"
                                item["length"] = round(el.AsOpenElement().Length, 3)
                            except Exception:
                                pass
                        elif el_type == 2:  # Cell
                            try:
                                item["type_name"] = "Cell"
                                item["cell_name"] = el.AsCellElement().Name
                            except Exception:
                                pass
                        else:
                            item["type_name"] = f"Type_{el_type}"

                        results.append(item)
                        count += 1
                        if count >= max_count:
                            return results

                elif hasattr(att, "GraphicalElementCache"):
                    cache = att.GraphicalElementCache
                    for idx in range(1, cache.Count + 1):
                        try:
                            el = cache.GetElement(idx)
                        except Exception:
                            continue
                        if not el:
                            continue
                        lvl_name = el.Level.Name if el.Level else ""
                        if level and lvl_name.lower() != str(level).lower():
                            continue
                        el_type = int(el.Type)
                        if target_type_id is not None and el_type != target_type_id:
                            continue
                        item = {
                            "reference_file": attach_name,
                            "id": str(getattr(el, "ID64", getattr(el, "ID", ""))),
                            "type": el_type,
                            "level": lvl_name,
                            "color": getattr(el, "Color", None),
                            "weight": getattr(el, "LineWeight", None),
                        }
                        results.append(item)
                        count += 1
                        if count >= max_count:
                            return results
        except Exception as ex:
            return [{"error": f"Lỗi khi quét phần tử trong reference: {ex}"}]

        return results

    @mcp.tool
    def get_reference_levels(reference_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lấy danh sách các Level (lớp bản vẽ) và trạng thái hiển thị của file bản vẽ tham chiếu (Reference File / Xref).

        :param reference_name: Tên file tham chiếu hoặc Logical Name (nếu None sẽ lấy file tham chiếu đầu tiên)
        """
        model = bridge.get_active_model()
        levels_list = []

        try:
            attachments = model.Attachments
            for i in range(1, attachments.Count + 1):
                att = attachments.Item(i)
                attach_name = getattr(att, "AttachName", "")
                logical_name = getattr(att, "LogicalName", "")

                if reference_name:
                    ref_query = str(reference_name).lower()
                    if ref_query not in attach_name.lower() and ref_query not in logical_name.lower():
                        continue

                try:
                    levels = att.Levels
                    for li in range(1, levels.Count + 1):
                        lvl = levels.Item(li)
                        levels_list.append({
                            "reference_file": attach_name,
                            "name": lvl.Name,
                            "number": getattr(lvl, "Number", li),
                            "is_displayed": getattr(lvl, "IsDisplayed", True),
                        })
                except Exception:
                    pass

                if reference_name or len(levels_list) > 0:
                    break
        except Exception as ex:
            return [{"error": f"Lỗi khi đọc levels của reference: {ex}"}]

        return levels_list

