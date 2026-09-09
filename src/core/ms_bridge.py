import os
import sys

if sys.platform == "win32":
    try:
        import win32service
        _d = win32service.OpenDesktop("Default", 0, False, 0x01FF)
        _d.SetThreadDesktop()
    except Exception:
        pass

import subprocess
import winreg
from typing import List, Optional, Tuple, Any
import pythoncom
import win32com.client
from pywintypes import com_error


def auto_register_com() -> bool:
    """
    Tự động đăng ký COM MicroStationDGN.Application vào HKCU nếu máy chưa có.
    Không yêu cầu quyền Administrator!
    """
    ustation_path = None
    # 1. Tìm từ tiến trình ustation.exe đang chạy
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='ustation.exe'", "get", "ExecutablePath"],
            text=True,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        for line in out.splitlines():
            line = line.strip()
            if line.lower().endswith("ustation.exe") and os.path.exists(line):
                ustation_path = line
                break
    except Exception:
        pass

    # 2. Tìm các đường dẫn cài đặt thông dụng
    if not ustation_path:
        candidates = [
            r"C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe",
            r"C:\Program Files\Bentley\MicroStation V8i\MicroStation\ustation.exe",
            r"D:\Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe",
            r"D:\Bentley\MicroStation V8i\MicroStation\ustation.exe",
            r"C:\Bentley\MicroStation V8i\MicroStation\ustation.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                ustation_path = c
                break

    if not ustation_path:
        return False

    try:
        clsid = "{6BA41DED-589A-427C-B829-B12F68C651B6}"
        local_server = f'"{ustation_path}" -automation'
        hkcu = winreg.HKEY_CURRENT_USER

        with winreg.CreateKey(hkcu, r"Software\Classes\MicroStationDGN.Application\CLSID") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, clsid)
        with winreg.CreateKey(hkcu, r"Software\Classes\MicroStationDGN.Application\CurVer") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "MicroStationDGN.Application.1")

        with winreg.CreateKey(hkcu, r"Software\Classes\MicroStationDGN.Application.1\CLSID") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, clsid)

        for sub in [rf"Software\Classes\CLSID\{clsid}", rf"Software\Classes\WOW6432Node\CLSID\{clsid}"]:
            try:
                with winreg.CreateKey(hkcu, sub) as k:
                    winreg.SetValue(k, "", winreg.REG_SZ, "Application Class")
                with winreg.CreateKey(hkcu, rf"{sub}\LocalServer32") as k:
                    winreg.SetValue(k, "", winreg.REG_SZ, local_server)
                with winreg.CreateKey(hkcu, rf"{sub}\ProgID") as k:
                    winreg.SetValue(k, "", winreg.REG_SZ, "MicroStationDGN.Application.1")
                with winreg.CreateKey(hkcu, rf"{sub}\VersionIndependentProgID") as k:
                    winreg.SetValue(k, "", winreg.REG_SZ, "MicroStationDGN.Application")
            except Exception:
                pass
        return True
    except Exception:
        return False


class MicroStationBridge:
    """
    Quản lý kết nối COM và các tiện ích thao tác với MicroStation V8i.
    Đảm bảo an toàn luồng với CoInitialize trên các worker thread của MCP.
    """

    def __init__(self):
        self._app = None

    def get_app(self, require_file: bool = True):
        """
        Lấy đối tượng MicroStationDGN.Application đang chạy.
        :param require_file: Nếu True, kiểm tra xem đã mở file DGN chưa. Nếu False, chỉ lấy đối tượng App.
        """
        if sys.platform == "win32":
            try:
                import win32service
                d = win32service.OpenDesktop("Default", 0, False, 0x01FF)
                d.SetThreadDesktop()
            except Exception:
                pass

        # Bắt buộc phải CoInitialize trên mỗi thread worker của MCP/AnyIO
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

        app = None

        # Cách 1: Thử GetActiveObject (kết nối trực tiếp phiên MicroStation đang mở trên màn hình)
        try:
            candidate = win32com.client.GetActiveObject("MicroStationDGN.Application")
            if candidate:
                try:
                    if candidate.HasActiveDesignFile:
                        self._app = candidate
                        return candidate
                except Exception:
                    pass
                app = candidate
        except Exception:
            pass

        # Cách 2: Thử ApplicationObjectConnector
        if not app or not getattr(app, "HasActiveDesignFile", False):
            try:
                connector = win32com.client.Dispatch("MicroStationDGN.ApplicationObjectConnector")
                candidate = connector.Application
                if candidate:
                    try:
                        if candidate.HasActiveDesignFile:
                            self._app = candidate
                            return candidate
                    except Exception:
                        pass
                    if not app:
                        app = candidate
            except Exception:
                pass


        # Cách 3: Thử Dispatch (kết nối tới instance đang chạy)
        if not app:
            try:
                app = win32com.client.Dispatch("MicroStationDGN.Application")
            except Exception as ex:
                # Tự động sửa lỗi Registry COM và thử lại ngay lập tức
                re_registered = auto_register_com()
                if re_registered:
                    try:
                        app = win32com.client.Dispatch("MicroStationDGN.Application")
                    except Exception as ex_retry:
                        ex = ex_retry

                if not app:
                    # Kiểm tra xem tiến trình ustation.exe có đang chạy trong Task Manager không
                    is_running = False
                    try:
                        out = subprocess.check_output(
                            ["tasklist", "/FI", "IMAGENAME eq ustation.exe", "/NH"],
                            text=True,
                            creationflags=0x08000000 if sys.platform == "win32" else 0
                        )
                        is_running = "ustation.exe" in out.lower()
                    except Exception:
                        pass

                    if is_running:
                        raise RuntimeError(
                            "Phần mềm MicroStation V8i ĐANG CHẠY nhưng không thể kết nối COM!\n\n"
                            "Nguyên nhân và giải pháp:\n"
                            "1. [QUAN TRỌNG NHẤT] Xung đột quyền Administrator (UAC):\n"
                            "   - Nếu MicroStation đang chạy dưới quyền Administrator ('Run as administrator'), "
                            "các app AI (Claude Desktop, Antigravity) chạy ở quyền thường sẽ bị Windows chặn giao tiếp qua COM.\n"
                            "   👉 Khắc phục: Hãy tắt MicroStation và mở lại BÌNH THƯỜNG (không bấm 'Run as administrator'). "
                            "Hoặc mở cả Claude Desktop dưới quyền Administrator.\n\n"
                            "2. Chưa đăng ký COM Server trên máy:\n"
                            "   👉 Khắc phục: Mở Command Prompt (cmd) bằng quyền Admin và gõ lệnh:\n"
                            "      \"C:\\Program Files (x86)\\Bentley\\MicroStation V8i (SELECTseries)\\MicroStation\\ustation.exe\" -regserver\n\n"
                            f"Chi tiết kỹ thuật: {ex}"
                        )
                    else:
                        raise RuntimeError(
                            "Không thể kết nối tới MicroStation V8i! "
                            "Vui lòng đảm bảo phần mềm MicroStation V8i đã được khởi động và mở sẵn một file bản vẽ (.dgn).\n"
                            f"Chi tiết: {ex}"
                        )

        if not app:
            raise RuntimeError("Không tìm thấy tiến trình MicroStation V8i đang hoạt động!")

        self._app = app

        # Kiểm tra xem đã mở file DGN chưa (nếu yêu cầu)
        if require_file:
            try:
                if not app.HasActiveDesignFile:
                    # Kiểm tra xem có nhiều hơn 1 tiến trình ustation.exe chạy cùng lúc không (ghost processes)
                    proc_count = 0
                    try:
                        out = subprocess.check_output(
                            ["tasklist", "/FI", "IMAGENAME eq ustation.exe", "/FO", "CSV", "/NH"],
                            text=True,
                            creationflags=0x08000000 if sys.platform == "win32" else 0
                        )
                        proc_count = sum(1 for line in out.strip().splitlines() if "ustation.exe" in line.lower())
                    except Exception:
                        pass

                    if proc_count > 1:
                        raise RuntimeError(
                            f"Phát hiện có {proc_count} tiến trình MicroStation (ustation.exe) đang chạy ngầm cùng lúc!\n"
                            "Hệ thống đang bị kết nối nhầm vào tiến trình ngầm không có bản vẽ.\n\n"
                            "👉 CÁCH XỬ LÝ TRONG 10 GIÂY:\n"
                            "1. Bấm Ctrl + Shift + Esc để mở Task Manager.\n"
                            "2. Tìm và bấm 'End task' TẤT CẢ các tiến trình 'MicroStation' / 'ustation.exe'.\n"
                            "3. Mở lại MicroStation một lần duy nhất ➜ mở file bản vẽ (.dgn) của bạn.\n"
                            "4. Chat lại với AI để vẽ!"
                        )
                    else:
                        raise RuntimeError(
                            "MicroStation V8i đang mở nhưng bạn CHƯA MỞ FILE BẢN VẼ nào!\n"
                            "👉 Vui lòng mở một file (.dgn) hoặc tạo file mới trong MicroStation V8i trước khi thao tác."
                        )
            except com_error as ce:
                raise RuntimeError(f"Lỗi truy cập file MicroStation: {ce}")

        return app

    def get_active_model(self):
        """Lấy ActiveModelReference của bản vẽ hiện tại."""
        app = self.get_app(require_file=True)
        if not app.HasActiveModelReference:
            raise RuntimeError("Không tìm thấy ActiveModelReference trong file DGN hiện tại!")
        return app.ActiveModelReference

    def get_active_file(self):
        """Lấy ActiveDesignFile hiện tại."""
        app = self.get_app(require_file=True)
        return app.ActiveDesignFile

    def create_point(self, x: float, y: float, z: float = 0.0):
        """Tạo đối tượng Point3d từ tọa độ (X, Y, Z)."""
        app = self.get_app(require_file=False)
        return app.Point3dFromXYZ(float(x), float(y), float(z))

    def create_rotation_matrix(self, angle_degrees: float):
        """Tạo ma trận quay 2D quanh trục Z theo góc độ (degrees)."""
        app = self.get_app(require_file=False)
        if abs(angle_degrees) < 1e-6:
            return app.Matrix3dIdentity()

        angle_radians = math.radians(angle_degrees)
        return app.Matrix3dFromAxisAndRotationAngle(2, angle_radians)

    @staticmethod
    def unwrap(element: Any):
        """Mở gói nếu COM trả về tuple đối tượng."""
        if isinstance(element, (tuple, list)):
            return element[0]
        return element

    def apply_symbology(
        self,
        element: Any,
        level: Optional[str] = None,
        color: Optional[int] = None,
        weight: Optional[int] = None,
        style: Optional[int] = None,
    ):
        """
        Gán thuộc tính Level, Color, Weight, LineStyle cho phần tử trước khi thêm vào Model.
        """
        element = self.unwrap(element)
        dgn_file = self.get_active_file()

        if level:
            try:
                try:
                    lvl_obj = dgn_file.Levels(level)
                except Exception:
                    lvl_obj = dgn_file.Levels.Item(level)
                if lvl_obj:
                    element.Level = lvl_obj
                else:
                    new_lvl = dgn_file.AddNewLevel(level)
                    dgn_file.RewriteLevels()
                    element.Level = new_lvl
            except Exception:
                pass

        if color is not None:
            element.Color = int(color)

        if weight is not None:
            element.LineWeight = int(weight)

        if style is not None:
            try:
                line_style_obj = dgn_file.LineStyles.Item(int(style))
                element.LineStyle = line_style_obj
            except Exception:
                pass

        return element

    def add_element(self, element: Any) -> str:
        """Thêm phần tử vào ActiveModelReference và vẽ lại."""
        element = self.unwrap(element)
        model = self.get_active_model()
        model.AddElement(element)
        try:
            element.Redraw()
        except Exception:
            pass
        return "OK"

    def find_element_by_id(self, element_id: str):
        """Tìm đối tượng Element trong ActiveModelReference theo ID."""
        model = self.get_active_model()
        cache = model.GraphicalElementCache
        target_id = str(element_id).strip()
        for idx in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(idx)
                if not el:
                    continue
                cur_id = str(getattr(el, "ID64", getattr(el, "ID", "")))
                if cur_id == target_id:
                    return el
            except Exception:
                continue
        return None


# Singleton instance dùng chung toàn hệ thống
bridge = MicroStationBridge()
