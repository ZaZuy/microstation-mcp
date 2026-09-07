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
