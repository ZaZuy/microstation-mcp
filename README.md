# MicroStation V8i MCP Server

Cầu nối chuyên nghiệp theo chuẩn **Model Context Protocol (MCP)** giữa các Trợ lý AI (Google Antigravity, Anthropic Claude, Cursor, v.v.) và phần mềm thiết kế kỹ thuật **Bentley MicroStation V8i (SELECTseries)**.

---

## 🌟 Tính Năng Chính

- **Hệ thống 59 công cụ CAD chuyên sâu:** Bao phủ từ dựng hình 2D/3D, đo đạc kích thước, chỉnh sửa đối tượng, điều khiển khung nhìn, quản lý file/model/reference đến xử lý dữ liệu hàng loạt.
- **Kiến trúc phân tầng chuẩn Enterprise (Clean Architecture):** Phân chia rõ ràng giữa `core/` (giao tiếp COM), `server/` (factory & lifecycle), `tools/`, `resources/`, `prompts/` và `transports/`.
- **Hỗ trợ đầy đủ bộ ba MCP:**
  - **Tools (59 công cụ):** 10 nhóm tính năng đồ họa, đo đạc và điều khiển.
  - **Resources:** Cung cấp thông tin trực tiếp về bản vẽ (`ms://drawing/info`), danh sách level (`ms://drawing/levels`), trạng thái active (`ms://drawing/settings`).
  - **Prompts:** Khuôn mẫu hướng dẫn quy trình vẽ kỹ thuật (`cad_drawing_workflow`) và kiểm toán bản vẽ (`element_inspection`).
- **Đa kênh truyền tải (Transports):** Hỗ trợ cả `stdio` (cho Antigravity / Claude Desktop) và `sse` (Server-Sent Events qua HTTP).
- **An toàn luồng:** Quản lý `CoInitialize` / COM Apartment trên từng luồng worker tự động.
- **Logging an toàn:** Toàn bộ log được định tuyến ra `sys.stderr`, bảo toàn 100% định dạng JSON-RPC trên kênh `stdout`.

---

## 📊 Bảng Danh Mục 10 Nhóm Công Cụ (59 Tools)

| Nhóm | Số lượng | Công cụ |
|---|---|---|
| **1. Hình học** | 10 | `draw_line`, `draw_linestring`, `draw_shape`, `draw_rectangle`, `draw_circle`, `draw_arc`, `draw_ellipse`, `draw_point`, `draw_bspline_curve`, `place_cell` |
| **2. Đo đạc & Kích thước** | 5 | `measure_distance`, `measure_area`, `dimension_linear`, `dimension_aligned`, `dimension_radius` |
| **3. Chỉnh sửa & Biến đổi** | 7 | `move_element`, `copy_element`, `rotate_element`, `scale_element`, `mirror_element`, `change_element_symbology`, `drop_element` |
| **4. Văn bản & Tìm kiếm** | 4 | `place_text`, `place_text_node`, `find_text`, `replace_text` |
| **5. Khung nhìn (Views)** | 7 | `fit_view`, `zoom_window`, `pan_view`, `zoom_in`, `zoom_out`, `get_view_info`, `capture_view_image` |
| **6. Quản lý File & Model** | 9 | `open_design_file`, `save_design_file`, `create_new_dgn`, `get_models`, `activate_model`, `create_model`, `get_references`, `attach_reference`, `detach_reference` |
| **7. Xử lý hàng loạt** | 3 | `batch_draw_points`, `batch_draw_lines`, `batch_place_texts` |
| **8. Cấu hình bản vẽ** | 6 | `set_active_level`, `set_active_color`, `set_active_weight`, `set_active_style`, `create_level`, `set_level_display` |
| **9. Truy vấn & Bóc tách** | 6 | `get_drawing_info`, `get_levels`, `get_active_settings`, `scan_elements`, `get_element_details`, `delete_element_by_id` |
| **10. Lệnh CAD trực tiếp** | 2 | `send_keyin`, `run_keyin_script` |

---

## 📁 Cấu Trúc Thư Mục

```text
microstation-mcp/
├── README.md                   # Tài liệu tổng quan & hướng dẫn cài đặt
├── AGENTS.md                   # Cẩm nang chỉ dẫn cho AI Agent
├── pyproject.toml              # Metadata dự án chuẩn PEP 621
├── requirements.txt            # Thư viện phụ thuộc
├── server.py                   # Shim tương thích ngược
│
├── docs/                       # Tài liệu thiết kế nội bộ
│   ├── architecture.md         # Kiến trúc chi tiết và luồng dữ liệu
│   ├── features.md             # Danh mục toàn bộ 59 Tools, Resources, Prompts
│   └── instructions.md         # Chỉ dẫn hệ thống gửi cho LLM
│
└── src/
    ├── main.py                 # Entry point chính (hỗ trợ --transport stdio|sse)
    ├── core/                   # Cầu nối COM với MicroStation V8i
    ├── server/                 # McpServer factory, logging, context
    ├── tools/                  # 10 module công cụ CAD (59 tools)
    ├── resources/              # Dynamic Resources
    ├── prompts/                # CAD Prompt templates
    └── transports/             # Kênh truyền tải stdio và sse
```

---

## 🚀 Cài Đặt & Cấu Hình

### 1. Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 2. Cấu hình MCP Client (Antigravity / Claude Desktop)
```json
{
  "mcpServers": {
    "microstation-v8i": {
      "command": "python",
      "args": [
        "-X",
        "utf8",
        "D:\\3. Task\\MCPserver-MicrostationV8i\\microstation-mcp\\src\\main.py"
      ]
    }
  }
}
```

### 3. Chạy độc lập qua giao thức SSE (Tùy chọn)
```bash
python src/main.py --transport sse --host 127.0.0.1 --port 8000
```
