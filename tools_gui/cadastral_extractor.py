"""
cadastral_extractor.py
Công cụ GUI chuyên dụng trích xuất Bảng tọa độ đỉnh và Chiều dài cạnh thửa đất
từ các file bản vẽ MicroStation V8i (.dgn).

Tính năng:
- Tự động phát hiện và khởi động MicroStation V8i (nếu chưa chạy).
- Cho phép duyệt và mở các file DGN khác nhau trực tiếp từ giao diện.
- Tự động nhận diện ranh thửa (Level 10 theo TT 26/2024 & TT 23/2025 hoặc Level tùy chọn).
- Hỗ trợ Shape, LineString, ComplexShape và tự động ghép nối các đoạn thẳng Line rời rạc.
- Tính toán: Tọa độ Trắc địa VN-2000 (X Northing, Y Easting), Chiều dài cạnh, Chu vi, Diện tích, Tâm thửa.
- Xuất dữ liệu: Sao chép Clipboard (dán ngay Excel/Word), Xuất file Excel (.xlsx), CSV, Zoom Fit trên CAD.
"""

import os
import sys
import math
import time
import threading
import subprocess
from typing import List, Tuple, Dict, Any, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Thiết lập thư mục gốc
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TOOLS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Thử import pywin32 và openpyxl
try:
    import pythoncom
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ==============================================================================
# 1. BỘ QUẢN LÝ KẾT NỐI VÀ ĐIỀU KHIỂN MICROSTATION V8i
# ==============================================================================

class MicroStationManager:
    """Quản lý kết nối COM, khởi chạy và tương tác với Bentley MicroStation V8i."""

    def __init__(self):
        self._app = None
        self._ustation_path = self.find_ustation_exe()

    @staticmethod
    def find_ustation_exe() -> Optional[str]:
        """Tìm đường dẫn ustation.exe trên hệ thống."""
        candidates = [
            r"C:\Program Files (x86)\Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe",
            r"C:\Program Files\Bentley\MicroStation V8i\MicroStation\ustation.exe",
            r"D:\Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe",
            r"D:\Bentley\MicroStation V8i\MicroStation\ustation.exe",
            r"C:\Bentley\MicroStation V8i\MicroStation\ustation.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def connect(self, auto_launch: bool = True, dgn_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Kết nối tới MicroStation V8i. Nếu chưa chạy và auto_launch=True, tự động khởi chạy.
        :return: (thành công, thông báo)
        """
        if not HAS_PYWIN32:
            return False, "Thiếu thư viện pywin32! Vui lòng cài đặt: pip install pywin32"

        pythoncom.CoInitialize()

        # Bước 1: Thử kết nối tới instance đang chạy qua ApplicationObjectConnector
        app = None
        try:
            connector = win32com.client.Dispatch("MicroStationDGN.ApplicationObjectConnector")
            candidate = connector.Application
            if candidate:
                app = candidate
        except Exception:
            pass

        # Bước 2: Thử GetActiveObject
        if not app:
            try:
                candidate = win32com.client.GetActiveObject("MicroStationDGN.Application")
                if candidate:
                    app = candidate
            except Exception:
                pass

        # Bước 3: Nếu chưa chạy và cho phép tự mở -> Khởi động MicroStation
        if not app and auto_launch:
            try:
                # Dùng Dispatch để COM tự kích hoạt MicroStationDGN.Application
                app = win32com.client.Dispatch("MicroStationDGN.Application")
                try:
                    app.Visible = True
                except Exception:
                    pass
            except Exception as e:
                # Fallback thử chạy exe trực tiếp nếu có
                if self._ustation_path and os.path.exists(self._ustation_path):
                    try:
                        args = [self._ustation_path]
                        if dgn_path and os.path.exists(dgn_path):
                            args.append(dgn_path)
                        subprocess.Popen(args, cwd=os.path.dirname(self._ustation_path))
                        time.sleep(4)
                        # Thử kết nối lại
                        connector = win32com.client.Dispatch("MicroStationDGN.ApplicationObjectConnector")
                        app = connector.Application
                        if app:
                            app.Visible = True
                    except Exception as ex2:
                        return False, f"Không thể khởi động MicroStation V8i: {ex2}"
                else:
                    return False, f"Không thể kết nối MicroStation V8i: {e}"

        if not app:
            return False, "Không thể kết nối tới MicroStation V8i!"

        self._app = app
        try:
            self._app.Visible = True
        except Exception:
            pass

        # Nếu truyền dgn_path thì mở file đó
        if dgn_path and os.path.exists(dgn_path):
            try:
                self._app.OpenDesignFile(os.path.abspath(dgn_path), False)
            except Exception as e:
                return False, f"Lỗi khi mở file DGN: {e}"

        return True, "Kết nối MicroStation V8i thành công!"

    def get_active_file_info(self) -> Dict[str, Any]:
        """Lấy thông tin file DGN đang mở."""
        if not self._app:
            return {"connected": False, "has_file": False}

        pythoncom.CoInitialize()
        try:
            has_file = getattr(self._app, "HasActiveDesignFile", False)
            if not has_file:
                return {"connected": True, "has_file": False}

            dgn = self._app.ActiveDesignFile
            model = self._app.ActiveModelReference

            return {
                "connected": True,
                "has_file": True,
                "file_name": os.path.basename(dgn.FullName),
                "full_path": dgn.FullName,
                "model_name": model.Name if model else "Default",
                "master_unit": model.MasterUnit.Name if hasattr(model, "MasterUnit") else "m",
            }
        except Exception as e:
            return {"connected": False, "has_file": False, "error": str(e)}

    def open_design_file(self, file_path: str) -> Tuple[bool, str]:
        """Yêu cầu MicroStation mở file DGN chỉ định."""
        if not os.path.exists(file_path):
            return False, f"File không tồn tại: {file_path}"

        pythoncom.CoInitialize()
        if not self._app:
            ok, msg = self.connect(auto_launch=True, dgn_path=file_path)
            if not ok:
                return False, msg
            return True, f"Đã mở file: {os.path.basename(file_path)}"

        try:
            self._app.Visible = True
            self._app.OpenDesignFile(os.path.abspath(file_path), False)
            return True, f"Đã mở file: {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Lỗi khi mở file: {e}"

    def get_levels_list(self) -> List[str]:
        """Lấy danh sách các Level có trong file hiện tại."""
        if not self._app or not getattr(self._app, "HasActiveDesignFile", False):
            return []
        pythoncom.CoInitialize()
        levels = set()
        try:
            model = self._app.ActiveModelReference
            cache = model.GraphicalElementCache
            for i in range(1, min(cache.Count + 1, 500)):
                el = cache.GetElement(i)
                if el and el.Level:
                    lvl_name = el.Level.Name
                    if lvl_name:
                        levels.add(lvl_name)
        except Exception:
            pass

        result = sorted(list(levels), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
        # Luôn ưu tiên level 10 lên đầu
        if "10" in result:
            result.remove("10")
            result.insert(0, "10")
        elif not result:
            result = ["10", "61", "1", "2", "3", "4", "20"]
        return result

    def fit_view(self, points: Optional[List[Tuple[float, float]]] = None):
        """Căn khung nhìn (Fit View) vào thửa đất hoặc toàn bộ bản vẽ."""
        if not self._app or not getattr(self._app, "HasActiveDesignFile", False):
            return
        pythoncom.CoInitialize()
        try:
            # Gửi lệnh key-in fit view
            self._app.CadInputQueue.SendCommand("FIT VIEW 1")
            self._app.CadInputQueue.SendCommand("REDRAW ALL")
        except Exception:
            pass


# ==============================================================================
# 2. BỘ XỬ LÝ HÌNH HỌC VÀ GHÉP NỐI RANH THỬA ĐẤT (GEOMETRY PROCESSOR)
# ==============================================================================

class ParcelGeometryProcessor:
    """Xử lý hình học đa giác thửa đất, ghép nối đoạn thẳng rời và tính toán số liệu."""

    @staticmethod
    def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Tính khoảng cách Euclid giữa 2 điểm (m)."""
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    @staticmethod
    def calculate_polygon_area_and_perimeter(points: List[Tuple[float, float]]) -> Tuple[float, float, Tuple[float, float]]:
        """
        Tính diện tích (công thức Gauss/Shoelace), chu vi và trọng tâm của đa giác.
        :return: (Diện tích m2, Chu vi m, (Tâm X, Tâm Y))
        """
        n = len(points)
        if n < 3:
            return 0.0, 0.0, (0.0, 0.0)

        area2 = 0.0
        perimeter = 0.0
        cx = 0.0
        cy = 0.0

        for i in range(n):
            j = (i + 1) % n
            xi, yi = points[i]
            xj, yj = points[j]
            cross = (xi * yj) - (xj * yi)
            area2 += cross
            cx += (xi + xj) * cross
            cy += (yi + yj) * cross
            perimeter += math.hypot(xj - xi, yj - yi)

        area = abs(area2) / 2.0
        if abs(area2) > 1e-7:
            cx = cx / (3.0 * area2)
            cy = cy / (3.0 * area2)
        else:
            cx = sum(p[0] for p in points) / n
            cy = sum(p[1] for p in points) / n

        return area, perimeter, (round(cx, 3), round(cy, 3))

    @staticmethod
    def orient_clockwise(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Đảm bảo đa giác được sắp xếp theo chiều kim đồng hồ."""
        n = len(points)
        if n < 3:
            return points
        area2 = sum((points[i][0] * points[(i + 1) % n][1]) - (points[(i + 1) % n][0] * points[i][1]) for i in range(n))
        # Trong hệ tọa độ chuẩn CAD: diện tích Gauss âm tương ứng theo chiều kim đồng hồ
        if area2 > 0:
            return list(reversed(points))
        return points

    @staticmethod
    def rotate_to_northwest_start(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Xoay mảng đỉnh sao cho Đỉnh 1 bắt đầu từ góc Tây-Bắc (Bắc cao nhất, Tây nhỏ nhất)."""
        if len(points) < 3:
            return points
        # Trong CAD: Y là hướng Bắc, X là hướng Đông
        best_idx = 0
        best_val = (-points[0][1], points[0][0])
        for idx, pt in enumerate(points):
            val = (-pt[1], pt[0])
            if val < best_val:
                best_val = val
                best_idx = idx

        return points[best_idx:] + points[:best_idx]

    @classmethod
    def stitch_lines_into_polygons(cls, lines: List[Tuple[Tuple[float, float], Tuple[float, float]]], tol: float = 0.05) -> List[List[Tuple[float, float]]]:
        """
        Ghép nối tập hợp các đoạn thẳng Line rời rạc thành một hoặc nhiều đa giác khép kín.
        :param lines: Danh sách các đoạn thẳng [((x1, y1), (x2, y2)), ...]
        :param tol: Sai số bắt điểm (mặc định 0.05m = 5cm)
        """
        if not lines:
            return []

        def pt_key(p):
            return (round(p[0] / tol) * tol, round(p[1] / tol) * tol)

        adj: Dict[Tuple[float, float], List[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]]] = {}
        for p1, p2 in lines:
            k1 = pt_key(p1)
            k2 = pt_key(p2)
            if k1 == k2:
                continue
            adj.setdefault(k1, []).append((k2, p2, p1))
            adj.setdefault(k2, []).append((k1, p1, p2))

        visited_edges = set()
        polygons = []

        nodes = sorted(list(adj.keys()), key=lambda k: (-k[1], k[0]))
        for start_node in nodes:
            for next_k, p_end, p_start in adj[start_node]:
                edge = tuple(sorted([start_node, next_k]))
                if edge in visited_edges:
                    continue

                path = [p_start, p_end]
                path_keys = [start_node, next_k]
                cur_edge = edge
                visited_edges.add(cur_edge)

                cur_k = next_k
                prev_k = start_node
                is_closed = False

                for _ in range(len(lines) + 5):
                    neighbors = [item for item in adj.get(cur_k, []) if item[0] != prev_k]
                    if not neighbors:
                        break
                    next_item = neighbors[0]
                    n_k, n_end, n_start = next_item
                    e = tuple(sorted([cur_k, n_k]))
                    visited_edges.add(e)
                    if n_k == start_node:
                        is_closed = True
                        break
                    if n_k in path_keys:
                        break
                    path.append(n_end)
                    path_keys.append(n_k)
                    prev_k = cur_k
                    cur_k = n_k

                if is_closed and len(path) >= 3:
                    area, _, _ = cls.calculate_polygon_area_and_perimeter(path)
                    if area > 1.0:  # Loại bỏ vòng lặp rác diện tích cực nhỏ
                        oriented = cls.orient_clockwise(path)
                        normalized = cls.rotate_to_northwest_start(oriented)
                        polygons.append(normalized)

        return polygons

    @classmethod
    def extract_parcels_from_model(cls, app: Any, target_level: str = "10") -> List[Dict[str, Any]]:
        """
        Quét và trích xuất tất cả các thửa đất từ Model MicroStation trên Level chỉ định.
        :return: Danh sách các thửa đất, mỗi thửa có: id, vertices, edges, area, perimeter, centroid
        """
        pythoncom.CoInitialize()
        if not app or not getattr(app, "HasActiveDesignFile", False):
            return []

        model = app.ActiveModelReference
        cache = model.GraphicalElementCache
        raw_lines = []
        direct_polygons = []

        for i in range(1, cache.Count + 1):
            try:
                el = cache.GetElement(i)
                if not el:
                    continue
                lvl_name = el.Level.Name if el.Level else ""
                if lvl_name.lower() != str(target_level).lower():
                    continue

                el_type = int(el.Type)

                # Type 3: Line
                if el_type == 3:
                    le = el.AsLineElement if hasattr(el, 'AsLineElement') and not callable(el.AsLineElement) else el.AsLineElement()
                    p1 = (round(float(le.StartPoint.X), 3), round(float(le.StartPoint.Y), 3))
                    p2 = (round(float(le.EndPoint.X), 3), round(float(le.EndPoint.Y), 3))
                    raw_lines.append((p1, p2))

                # Type 6: Shape, Type 4: LineString
                elif el_type in (4, 6):
                    elem = el.AsLineStringElement if hasattr(el, 'AsLineStringElement') and not callable(el.AsLineStringElement) else el.AsLineStringElement()
                    cnt = getattr(elem, "VerticesCount", 0)
                    pts = []
                    if cnt > 0:
                        for v_idx in range(1, cnt + 1):
                            v = elem.Vertex(v_idx)
                            pts.append((round(float(v.X), 3), round(float(v.Y), 3)))
                    else:
                        v_raw = elem.GetVertices()
                        pts = [(round(float(p.X), 3), round(float(p.Y), 3)) for p in v_raw]

                    # Bỏ điểm lặp cuối nếu có (khép kín)
                    if len(pts) >= 4 and pts[0] == pts[-1]:
                        pts = pts[:-1]

                    if len(pts) >= 3:
                        area, _, _ = cls.calculate_polygon_area_and_perimeter(pts)
                        if area > 1.0:
                            oriented = cls.orient_clockwise(pts)
                            normalized = cls.rotate_to_northwest_start(oriented)
                            direct_polygons.append(normalized)

                # Type 14: ComplexShape
                elif el_type == 14:
                    try:
                        sub_lines = []
                        enumerator = el.GetSubElements()
                        while enumerator.MoveNext():
                            sub = enumerator.Current
                            if sub.Type == 3:
                                le = sub.AsLineElement if hasattr(sub, 'AsLineElement') and not callable(sub.AsLineElement) else sub.AsLineElement()
                                sub_lines.append(((round(le.StartPoint.X, 3), round(le.StartPoint.Y, 3)), (round(le.EndPoint.X, 3), round(le.EndPoint.Y, 3))))
                        if sub_lines:
                            stitched = cls.stitch_lines_into_polygons(sub_lines)
                            direct_polygons.extend(stitched)
                    except Exception:
                        pass
            except Exception:
                continue

        # Ghép các line rời rạc nếu có
        if raw_lines:
            stitched = cls.stitch_lines_into_polygons(raw_lines)
            direct_polygons.extend(stitched)

        # Đóng gói kết quả
        results = []
        for idx, vertices in enumerate(direct_polygons, 1):
            area, perimeter, centroid = cls.calculate_polygon_area_and_perimeter(vertices)

            # Xây dựng danh sách cạnh
            edges = []
            n = len(vertices)
            for i in range(n):
                next_i = (i + 1) % n
                p_cur = vertices[i]
                p_next = vertices[next_i]
                edge_len = cls.calculate_distance(p_cur, p_next)
                edges.append({
                    "from_idx": i + 1,
                    "to_idx": next_i + 1,
                    "name": f"{i + 1} – {next_i + 1}",
                    "length": round(edge_len, 2),
                    "length_exact": round(edge_len, 4),
                    "start_pt": p_cur,
                    "end_pt": p_next,
                })

            results.append({
                "parcel_index": idx,
                "name": f"Thửa đất #{idx}",
                "level": target_level,
                "vertices_count": n,
                "vertices": vertices,
                "edges": edges,
                "area_m2": round(area, 2),
                "area_m2_1dec": round(area, 1),
                "area_ha": round(area / 10000.0, 4),
                "perimeter_m": round(perimeter, 2),
                "centroid": centroid,
            })

        # Sắp xếp theo diện tích giảm dần
        results.sort(key=lambda x: x["area_m2"], reverse=True)
        return results


# ==============================================================================
# 3. GIAO DIỆN NGƯỜI DÙNG HIỆN ĐẠI (TKINTER GUI)
# ==============================================================================

class CadastralExtractorGUI:
    """Giao diện đồ họa chuyên nghiệp cho công cụ trích xuất tọa độ thửa đất."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vigela Cadastral Extractor - Trích Xuất Tọa Độ & Cạnh Thửa Đất (MicroStation V8i)")
        self.root.geometry("1050x720")
        self.root.minsize(850, 600)

        # Màu sắc chủ đạo (Modern Slate/Indigo Theme)
        self.bg_color = "#0f172a"          # Nền chính (Slate 900)
        self.card_bg = "#1e293b"           # Nền Card (Slate 800)
        self.card_border = "#334155"       # Viền Card (Slate 700)
        self.text_primary = "#f8fafc"      # Chữ trắng sáng
        self.text_secondary = "#94a3b8"    # Chữ mờ xám
        self.accent_color = "#6366f1"      # Tím Indigo nhấn
        self.accent_hover = "#4f46e5"      # Tím đậm
        self.success_color = "#10b981"     # Xanh lá Emerald
        self.danger_color = "#ef4444"      # Đỏ Rose
        self.warning_color = "#f59e0b"     # Vàng Amber

        self.root.configure(bg=self.bg_color)

        # Cài đặt icon nếu có
        icon_path = os.path.join(PROJECT_ROOT, "launcher", "vigela_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Quản lý MicroStation
        self.ms = MicroStationManager()
        self.parcels_data: List[Dict[str, Any]] = []
        self.current_parcel: Optional[Dict[str, Any]] = None

        # Thiết lập phong cách ttk
        self.setup_ttk_styles()

        # Dựng các thành phần UI
        self.build_ui()

        # Tự động kết nối MicroStation khi mở tool
        self.root.after(300, self.auto_start_and_connect)

    def setup_ttk_styles(self):
        """Thiết lập Style cho ttk widgets."""
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview Bảng số liệu
        style.configure(
            "Treeview",
            background="#1e293b",
            foreground="#f8fafc",
            fieldbackground="#1e293b",
            rowheight=28,
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#334155",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=4
        )
        style.map(
            "Treeview",
            background=[("selected", "#4f46e5")],
            foreground=[("selected", "#ffffff")]
        )

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground="#1e293b",
            background="#334155",
            foreground="#ffffff",
            arrowcolor="#ffffff",
            bordercolor="#334155",
            relief="flat"
        )

    def build_ui(self):
        """Xây dựng bố cục giao diện hoàn chỉnh."""

        # ---------------- 1. HEADER BANNER ----------------
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_box = tk.Frame(header_frame, bg=self.bg_color)
        title_box.pack(side="left", fill="both", expand=True)

        title_lbl = tk.Label(
            title_box,
            text="📐 TRÍCH XUẤT TỌA ĐỘ & CHIỀU DÀI CẠNH THỬA ĐẤT",
            font=("Segoe UI", 15, "bold"),
            fg=self.text_primary,
            bg=self.bg_color
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            title_box,
            text="Hỗ trợ MicroStation V8i • Chuẩn Thông tư 26/2024/TT-BTNMT & Thông tư 23/2025/TT-BNNMT",
            font=("Segoe UI", 9),
            fg=self.text_secondary,
            bg=self.bg_color
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Trạng thái kết nối MicroStation
        self.status_badge = tk.Label(
            header_frame,
            text="⚪ Đang kiểm tra MicroStation...",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#1e293b",
            padx=12,
            pady=6,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155"
        )
        self.status_badge.pack(side="right", padx=5)

        # ---------------- 2. THANH ĐIỀU KHIỂN & CHỌN FILE ----------------
        ctrl_card = tk.Frame(self.root, bg=self.card_bg, highlightthickness=1, highlightbackground=self.card_border)
        ctrl_card.pack(fill="x", padx=20, pady=(0, 10))

        # Dòng 1: File DGN
        file_row = tk.Frame(ctrl_card, bg=self.card_bg)
        file_row.pack(fill="x", padx=15, pady=(10, 6))

        tk.Label(
            file_row,
            text="File DGN:",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_primary,
            bg=self.card_bg,
            width=10,
            anchor="w"
        ).pack(side="left")

        self.file_entry = tk.Entry(
            file_row,
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#38bdf8",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155"
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)

        btn_browse = tk.Button(
            file_row,
            text="📂 Duyệt File...",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.browse_dgn_file
        )
        btn_browse.pack(side="left", padx=2)

        self.btn_open_cad = tk.Button(
            file_row,
            text="🚀 Mở vào CAD",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_color,
            fg="#ffffff",
            activebackground=self.accent_hover,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.open_in_microstation
        )
        self.btn_open_cad.pack(side="left", padx=2)

        # Dòng 2: Bộ chọn Level & Thửa đất
        filter_row = tk.Frame(ctrl_card, bg=self.card_bg)
        filter_row.pack(fill="x", padx=15, pady=(4, 12))

        tk.Label(
            filter_row,
            text="Level ranh:",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_primary,
            bg=self.card_bg,
            width=10,
            anchor="w"
        ).pack(side="left")

        self.level_combo = ttk.Combobox(filter_row, width=12, font=("Segoe UI", 9), state="readonly")
        self.level_combo["values"] = ["10", "61", "1", "2", "3", "4", "20"]
        self.level_combo.set("10")
        self.level_combo.pack(side="left", padx=(0, 15))
        self.level_combo.bind("<<ComboboxSelected>>", lambda e: self.extract_parcels())

        tk.Label(
            filter_row,
            text="Chọn thửa:",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_primary,
            bg=self.card_bg,
            width=10,
            anchor="w"
        ).pack(side="left")

        self.parcel_combo = ttk.Combobox(filter_row, width=28, font=("Segoe UI", 9), state="readonly")
        self.parcel_combo.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.parcel_combo.bind("<<ComboboxSelected>>", self.on_parcel_selected)

        btn_reload = tk.Button(
            filter_row,
            text="🔄 Quét lại",
            font=("Segoe UI", 9, "bold"),
            bg="#0f766e",
            fg="#ccfbf1",
            activebackground="#115e59",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.extract_parcels
        )
        btn_reload.pack(side="right")

        # ---------------- 3. KHỐI THỐNG KÊ NHANH (KPI CARDS) ----------------
        stats_frame = tk.Frame(self.root, bg=self.bg_color)
        stats_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.kpi_area = self.create_kpi_card(stats_frame, "📐 DIỆN TÍCH (S)", "0.0 m²", "#38bdf8")
        self.kpi_area.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.kpi_perim = self.create_kpi_card(stats_frame, "📏 CHU VI (P)", "0.0 m", "#f59e0b")
        self.kpi_perim.pack(side="left", fill="both", expand=True, padx=5)

        self.kpi_verts = self.create_kpi_card(stats_frame, "🏷️ SỐ ĐỈNH RÁNH", "0 đỉnh", "#a855f7")
        self.kpi_verts.pack(side="left", fill="both", expand=True, padx=5)

        self.kpi_center = self.create_kpi_card(stats_frame, "📍 TÂM HÌNH HỌC (CENTROID)", "X: - | Y: -", "#10b981")
        self.kpi_center.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # ---------------- 4. BẢNG DỮ LIỆU TỌA ĐỘ VÀ CẠNH (TREEVIEW) ----------------
        table_card = tk.Frame(self.root, bg=self.card_bg, highlightthickness=1, highlightbackground=self.card_border)
        table_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        columns = ("stt", "vertex", "x_vn2000", "y_vn2000", "edge", "length", "x_cad", "y_cad")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("stt", text="STT")
        self.tree.heading("vertex", text="Đỉnh mốc")
        self.tree.heading("x_vn2000", text="Tọa độ X (m) [Bắc]")
        self.tree.heading("y_vn2000", text="Tọa độ Y (m) [Đông]")
        self.tree.heading("edge", text="Tên cạnh")
        self.tree.heading("length", text="Chiều dài (m)")
        self.tree.heading("x_cad", text="X (CAD)")
        self.tree.heading("y_cad", text="Y (CAD)")

        self.tree.column("stt", width=45, anchor="center")
        self.tree.column("vertex", width=75, anchor="center")
        self.tree.column("x_vn2000", width=140, anchor="e")
        self.tree.column("y_vn2000", width=140, anchor="e")
        self.tree.column("edge", width=90, anchor="center")
        self.tree.column("length", width=100, anchor="e")
        self.tree.column("x_cad", width=130, anchor="e")
        self.tree.column("y_cad", width=130, anchor="e")

        scrollbar_y = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        scrollbar_y.pack(side="right", fill="y", pady=5)

        # ---------------- 5. THANH NÚT THAO TÁC XUẤT DỮ LIỆU ----------------
        bottom_bar = tk.Frame(self.root, bg=self.bg_color)
        bottom_bar.pack(fill="x", padx=20, pady=(0, 15))

        btn_copy = tk.Button(
            bottom_bar,
            text="📋 Sao Chép (Dán Excel/Word)",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self.copy_to_clipboard
        )
        btn_copy.pack(side="left", padx=(0, 6))

        btn_excel = tk.Button(
            bottom_bar,
            text="📊 Xuất File Excel (.xlsx)",
            font=("Segoe UI", 9, "bold"),
            bg="#15803d",
            fg="#ffffff",
            activebackground="#166534",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self.export_to_excel
        )
        btn_excel.pack(side="left", padx=6)

        btn_csv = tk.Button(
            bottom_bar,
            text="📄 Xuất File CSV",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
            command=self.export_to_csv
        )
        btn_csv.pack(side="left", padx=6)

        btn_fit = tk.Button(
            bottom_bar,
            text="🎯 Zoom Fit trên CAD",
            font=("Segoe UI", 9, "bold"),
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self.zoom_fit_cad
        )
        btn_fit.pack(side="left", padx=6)

        self.lbl_msg = tk.Label(
            bottom_bar,
            text="",
            font=("Segoe UI", 9, "italic"),
            fg="#38bdf8",
            bg=self.bg_color
        )
        self.lbl_msg.pack(side="right", padx=10)

    def create_kpi_card(self, parent, title: str, initial_value: str, color: str) -> tk.Frame:
        """Tạo thẻ thống kê KPI."""
        card = tk.Frame(parent, bg=self.card_bg, highlightthickness=1, highlightbackground=self.card_border)
        t_lbl = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg=self.text_secondary, bg=self.card_bg)
        t_lbl.pack(anchor="w", padx=12, pady=(8, 2))

        val_lbl = tk.Label(card, text=initial_value, font=("Segoe UI", 13, "bold"), fg=color, bg=self.card_bg)
        val_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        card.val_lbl = val_lbl
        return card

    # ==========================================================================
    # LOGIC KẾT NỐI & TƯƠNG TÁC MICROSTATION
    # ==========================================================================

    def auto_start_and_connect(self):
        """Khởi chạy MicroStation nếu chưa mở và kết nối."""
        self.status_badge.config(text="🟡 Đang kết nối MicroStation...", fg="#fbbf24")

        def task():
            ok, msg = self.ms.connect(auto_launch=True)
            self.root.after(0, lambda: self.on_connect_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()

    def on_connect_done(self, ok: bool, msg: str):
        """Callback khi kết nối MicroStation hoàn thành."""
        if ok:
            info = self.ms.get_active_file_info()
            if info.get("has_file"):
                file_name = info.get("file_name", "")
                self.status_badge.config(
                    text=f"🟢 Đã kết nối: {file_name}",
                    fg="#6ee7b7",
                    bg="#064e3b"
                )
                self.file_entry.delete(0, tk.END)
                self.file_entry.insert(0, info.get("full_path", ""))
                # Tải danh sách Level
                levels = self.ms.get_levels_list()
                if levels:
                    self.level_combo["values"] = levels
                    if "10" in levels:
                        self.level_combo.set("10")
                # Quét thửa đất
                self.extract_parcels()
            else:
                self.status_badge.config(
                    text="🟡 MicroStation mở (Chưa mở file DGN)",
                    fg="#fde68a",
                    bg="#78350f"
                )
                self.show_toast("MicroStation đang mở nhưng chưa có file bản vẽ nào. Vui lòng chọn file!")
        else:
            self.status_badge.config(
                text="🔴 Không thể kết nối MicroStation",
                fg="#fca5a5",
                bg="#7f1d1d"
            )
            self.show_toast(msg, is_error=True)

    def browse_dgn_file(self):
        """Mở hộp thoại chọn file DGN."""
        initial_dir = os.path.dirname(self.file_entry.get()) if self.file_entry.get() else os.getcwd()
        f_path = filedialog.askopenfilename(
            title="Chọn file bản vẽ MicroStation (.dgn)",
            initialdir=initial_dir,
            filetypes=[("MicroStation Design Files", "*.dgn"), ("All Files", "*.*")]
        )
        if f_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, f_path)
            # Tự động mở vào CAD và trích xuất
            self.open_in_microstation()

    def open_in_microstation(self):
        """Mở file đã chọn vào MicroStation và trích xuất dữ liệu."""
        f_path = self.file_entry.get().strip()
        if not f_path or not os.path.exists(f_path):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file DGN hợp lệ!")
            return

        self.status_badge.config(text="🟡 Đang mở file vào CAD...", fg="#fbbf24")
        self.btn_open_cad.config(state="disabled")

        def task():
            ok, msg = self.ms.open_design_file(f_path)
            self.root.after(0, lambda: self.on_open_file_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()

    def on_open_file_done(self, ok: bool, msg: str):
        self.btn_open_cad.config(state="normal")
        if ok:
            info = self.ms.get_active_file_info()
            file_name = info.get("file_name", os.path.basename(self.file_entry.get()))
            self.status_badge.config(
                text=f"🟢 Đang mở: {file_name}",
                fg="#6ee7b7",
                bg="#064e3b"
            )
            # Cập nhật danh sách Level
            levels = self.ms.get_levels_list()
            if levels:
                self.level_combo["values"] = levels
                if "10" in levels:
                    self.level_combo.set("10")
            # Trích xuất thửa đất
            self.extract_parcels()
            self.show_toast(f"Đã mở file thành công: {file_name}")
        else:
            self.show_toast(msg, is_error=True)
            messagebox.showerror("Lỗi mở file", msg)

    # ==========================================================================
    # LOGIC TRÍCH XUẤT TỌA ĐỘ VÀ CHIỀU DÀI CẠNH
    # ==========================================================================

    def extract_parcels(self):
        """Quét và trích xuất tất cả thửa đất trong file DGN hiện tại."""
        target_level = self.level_combo.get().strip() or "10"
        self.show_toast("Đang quét dữ liệu thửa đất...")

        def task():
            try:
                parcels = ParcelGeometryProcessor.extract_parcels_from_model(self.ms._app, target_level)
                self.root.after(0, lambda: self.on_extract_done(parcels, target_level))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"Lỗi quét thửa đất: {e}", is_error=True))

        threading.Thread(target=task, daemon=True).start()

    def on_extract_done(self, parcels: List[Dict[str, Any]], level: str):
        self.parcels_data = parcels
        if not parcels:
            self.current_parcel = None
            self.parcel_combo["values"] = ["Không tìm thấy thửa đất nào"]
            self.parcel_combo.set("Không tìm thấy thửa đất nào")
            self.clear_table()
            self.show_toast(f"Không tìm thấy ranh thửa khép kín nào trên Level {level}!", is_error=True)
            return

        combo_values = []
        for p in parcels:
            combo_values.append(f"{p['name']} (S = {p['area_m2']:,} m² - {p['vertices_count']} đỉnh)")
        self.parcel_combo["values"] = combo_values
        self.parcel_combo.current(0)
        self.current_parcel = parcels[0]

        self.display_parcel_data(self.current_parcel)
        self.show_toast(f"Tìm thấy {len(parcels)} thửa đất trên Level {level}!")

    def on_parcel_selected(self, event=None):
        """Khi người dùng chọn thửa đất khác trong danh sách."""
        idx = self.parcel_combo.current()
        if 0 <= idx < len(self.parcels_data):
            self.current_parcel = self.parcels_data[idx]
            self.display_parcel_data(self.current_parcel)

    def display_parcel_data(self, parcel: Dict[str, Any]):
        """Hiển thị số liệu của thửa đất lên Bảng Treeview và các KPI cards."""
        self.clear_table()
        if not parcel:
            return

        # Cập nhật KPI cards
        self.kpi_area.val_lbl.config(text=f"{parcel['area_m2']:,.1f} m²  ({parcel['area_ha']} ha)")
        self.kpi_perim.val_lbl.config(text=f"{parcel['perimeter_m']:,.2f} m")
        self.kpi_verts.val_lbl.config(text=f"{parcel['vertices_count']} đỉnh")
        cx, cy = parcel["centroid"]
        self.kpi_center.val_lbl.config(text=f"X: {cy:,.3f} | Y: {cx:,.3f}")

        # Điền bảng số liệu
        vertices = parcel["vertices"]
        edges = parcel["edges"]
        n = len(vertices)

        for i in range(n):
            v_num = i + 1
            pt = vertices[i]
            # Tọa độ CAD: X = Easting, Y = Northing
            cad_x, cad_y = pt[0], pt[1]
            # Tọa độ Trắc địa VN-2000: X = Northing (CAD Y), Y = Easting (CAD X)
            vn2000_x, vn2000_y = cad_y, cad_x

            edge_info = edges[i] if i < len(edges) else {}
            edge_name = edge_info.get("name", f"{v_num} – {(v_num % n) + 1}")
            edge_len = edge_info.get("length", 0.0)

            # Định dạng chuỗi số
            str_vn_x = f"{vn2000_x:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_vn_y = f"{vn2000_y:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_cad_x = f"{cad_x:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_cad_y = f"{cad_y:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
            str_len = f"{edge_len:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(i + 1, str(v_num), str_vn_x, str_vn_y, edge_name, str_len, str_cad_x, str_cad_y),
                tags=(tag,)
            )

        self.tree.tag_configure("even", background="#1e293b")
        self.tree.tag_configure("odd", background="#0f172a")

    def clear_table(self):
        """Xóa trắng bảng số liệu."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.kpi_area.val_lbl.config(text="0.0 m²")
        self.kpi_perim.val_lbl.config(text="0.0 m")
        self.kpi_verts.val_lbl.config(text="0 đỉnh")
        self.kpi_center.val_lbl.config(text="X: - | Y: -")

    # ==========================================================================
    # LOGIC XUẤT DỮ LIỆU (CLIPBOARD, EXCEL, CSV, CAD FIT)
    # ==========================================================================

    def copy_to_clipboard(self):
        """Sao chép toàn bộ bảng số liệu vào Clipboard (tab-separated) để dán vào Word/Excel."""
        if not self.current_parcel:
            messagebox.showwarning("Thông báo", "Chưa có dữ liệu thửa đất để sao chép!")
            return

        lines = [
            "STT\tĐỉnh mốc\tTọa độ X (m) [Northing]\tTọa độ Y (m) [Easting]\tTên cạnh\tChiều dài (m)\tX CAD\tY CAD"
        ]
        for child in self.tree.get_children():
            vals = self.tree.item(child)["values"]
            lines.append("\t".join(str(v) for v in vals))

        # Thêm dòng tổng kết
        p = self.current_parcel
        lines.append("")
        lines.append(f"Diện tích:\t{p['area_m2']} m² ({p['area_ha']} ha)")
        lines.append(f"Chu vi:\t{p['perimeter_m']} m")
        lines.append(f"Tâm thửa:\tX = {p['centroid'][1]} m, Y = {p['centroid'][0]} m")

        text_data = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(text_data)
        self.show_toast("✅ Đã sao chép vào Clipboard! Dán trực tiếp vào Excel/Word bằng Ctrl + V.")

    def export_to_excel(self):
        """Xuất dữ liệu ra file Excel (.xlsx) với định dạng chuẩn trích lục địa chính."""
        if not self.current_parcel:
            messagebox.showwarning("Thông báo", "Chưa có dữ liệu thửa đất để xuất Excel!")
            return

        if not HAS_OPENPYXL:
            messagebox.showerror("Thiếu thư viện", "Chưa cài đặt openpyxl! Vui lòng chạy lệnh: pip install openpyxl")
            return

        p = self.current_parcel
        default_name = f"Bang_Toa_Do_Thua_Dat_{p['parcel_index']}.xlsx"
        file_path = filedialog.asksaveasfilename(
            title="Lưu Bảng Tọa Độ Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Bảng kê tọa độ góc ranh"

            # Font và Kiểu
            font_title = Font(name="Times New Roman", size=14, bold=True, color="1E3A8A")
            font_sub = Font(name="Times New Roman", size=11, italic=True)
            font_header = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
            font_body = Font(name="Times New Roman", size=11)
            font_bold = Font(name="Times New Roman", size=11, bold=True)

            fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
            fill_zebra = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

            border_thin = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            # Tiêu đề
            ws.merge_cells("A1:G1")
            ws["A1"] = "BẢNG KÊ TỌA ĐỘ VÀ CHIỀU DÀI CẠNH THỬA ĐẤT"
            ws["A1"].font = font_title
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            # Thông tin phụ
            dgn_name = os.path.basename(self.file_entry.get()) or "Bản đồ địa chính"
            ws.merge_cells("A2:G2")
            ws["A2"] = f"File bản vẽ: {dgn_name}  |  Level ranh: {p['level']}  |  Hệ quy chiếu: VN-2000"
            ws["A2"].font = font_sub
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # Header bảng
            headers = [
                "STT",
                "Đỉnh mốc",
                "Tọa độ X (m)\n[Northing]",
                "Tọa độ Y (m)\n[Easting]",
                "Tên cạnh",
                "Chiều dài d (m)",
                "Ghi chú"
            ]
            row_idx = 4
            ws.row_dimensions[row_idx].height = 28
            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=h)
                cell.font = font_header
                cell.fill = fill_header
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border_thin

            # Dữ liệu từng đỉnh
            vertices = p["vertices"]
            edges = p["edges"]
            n = len(vertices)

            for i in range(n):
                row_idx += 1
                ws.row_dimensions[row_idx].height = 22
                pt = vertices[i]
                edge = edges[i] if i < len(edges) else {}

                vn_x = pt[1]  # CAD Y
                vn_y = pt[0]  # CAD X

                row_vals = [
                    i + 1,
                    f"Đ{i + 1}",
                    vn_x,
                    vn_y,
                    edge.get("name", ""),
                    edge.get("length", 0.0),
                    ""
                ]

                for col_idx, val in enumerate(row_vals, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = font_body
                    cell.border = border_thin
                    if i % 2 == 1:
                        cell.fill = fill_zebra

                    if col_idx in (1, 2, 5):
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col_idx in (3, 4, 6):
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        if col_idx in (3, 4):
                            cell.number_format = '#,##0.000'
                        else:
                            cell.number_format = '#,##0.00'

            # Hàng tổng kết
            row_idx += 1
            ws.row_dimensions[row_idx].height = 24
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=5)
            c_sum_label = ws.cell(row=row_idx, column=1, value="Tổng chu vi (P):")
            c_sum_label.font = font_bold
            c_sum_label.alignment = Alignment(horizontal="right", vertical="center")
            c_sum_label.border = border_thin

            c_sum_val = ws.cell(row=row_idx, column=6, value=p["perimeter_m"])
            c_sum_val.font = font_bold
            c_sum_val.alignment = Alignment(horizontal="right", vertical="center")
            c_sum_val.number_format = '#,##0.00'
            c_sum_val.border = border_thin

            ws.cell(row=row_idx, column=7).border = border_thin

            # Hàng diện tích
            row_idx += 1
            ws.row_dimensions[row_idx].height = 24
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=5)
            c_area_label = ws.cell(row=row_idx, column=1, value="Diện tích thửa đất (S):")
            c_area_label.font = font_bold
            c_area_label.alignment = Alignment(horizontal="right", vertical="center")
            c_area_label.border = border_thin

            c_area_val = ws.cell(row=row_idx, column=6, value=f"{p['area_m2']} m²")
            c_area_val.font = font_bold
            c_area_val.alignment = Alignment(horizontal="right", vertical="center")
            c_area_val.border = border_thin

            ws.cell(row=row_idx, column=7, value=f"({p['area_ha']} ha)").border = border_thin

            # Tự động căn chỉnh độ rộng cột
            col_widths = {1: 8, 2: 12, 3: 20, 4: 20, 5: 14, 6: 18, 7: 15}
            for col_idx, width in col_widths.items():
                ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

            wb.save(file_path)
            self.show_toast(f"✅ Đã xuất file Excel thành công: {os.path.basename(file_path)}")
            # Mở file Excel vừa xuất nếu người dùng muốn
            try:
                os.startfile(file_path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Lỗi xuất Excel", f"Không thể ghi file Excel: {e}")

    def export_to_csv(self):
        """Xuất dữ liệu ra file văn bản CSV."""
        if not self.current_parcel:
            messagebox.showwarning("Thông báo", "Chưa có dữ liệu thửa đất để xuất CSV!")
            return

        p = self.current_parcel
        default_name = f"Toa_Do_Thua_Dat_{p['parcel_index']}.csv"
        file_path = filedialog.asksaveasfilename(
            title="Lưu file CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write("STT,Dinh_Moc,X_VN2000,Y_VN2000,Ten_Canh,Chieu_Dai_m,X_CAD,Y_CAD\n")
                vertices = p["vertices"]
                edges = p["edges"]
                n = len(vertices)
                for i in range(n):
                    pt = vertices[i]
                    edge = edges[i] if i < len(edges) else {}
                    vn_x, vn_y = pt[1], pt[0]
                    f.write(f"{i + 1},Đ{i + 1},{vn_x:.3f},{vn_y:.3f},{edge.get('name', '')},{edge.get('length', 0.0):.2f},{pt[0]:.3f},{pt[1]:.3f}\n")

                f.write(f"\nDien_tich_m2,{p['area_m2']}\n")
                f.write(f"Chu_vi_m,{p['perimeter_m']}\n")

            self.show_toast(f"✅ Đã xuất CSV thành công: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Lỗi xuất CSV", f"Không thể ghi file CSV: {e}")

    def zoom_fit_cad(self):
        """Căn khung nhìn CAD (Fit View) vào vị trí thửa đất."""
        if not self.ms._app:
            self.show_toast("Chưa kết nối MicroStation!", is_error=True)
            return
        self.ms.fit_view()
        self.show_toast("🎯 Đã gửi lệnh Fit View lên màn hình MicroStation!")

    def show_toast(self, message: str, is_error: bool = False):
        """Hiển thị thông báo nhanh trên thanh trạng thái."""
        self.lbl_msg.config(text=message, fg=self.danger_color if is_error else self.success_color)
        self.root.after(4500, lambda: self.lbl_msg.config(text=""))


# ==============================================================================
# 4. ĐIỂM KHỞI CHẠY CHÍNH (MAIN ENTRYPOINT)
# ==============================================================================

def main():
    root = tk.Tk()
    app = CadastralExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
