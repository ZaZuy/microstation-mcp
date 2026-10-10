# MicroStation V8i MCP Server

Cầu nối chuyên nghiệp theo chuẩn **Model Context Protocol (MCP)** giữa các Trợ lý AI (Google Antigravity, Anthropic Claude, Cursor, v.v.) và phần mềm thiết kế kỹ thuật **Bentley MicroStation V8i (SELECTseries)**.

---

## 🌟 Tính Năng Chính

- **Hệ thống 133 công cụ CAD chuyên sâu:** Bao phủ từ dựng hình 2D/3D, đo đạc kích thước, chỉnh sửa đối tượng, điều khiển khung nhìn, quản lý file/model/reference đến xử lý dữ liệu hàng loạt.
- **Kiến trúc Dual-Mode hiệu năng cao (High Performance & Zero Overhead):**
  - **Mode 1 (Native IPC - Khuyến nghị):** Giao tiếp trực tiếp với MicroStation V8i qua ứng dụng **MDL C++ Native (`MsNativePipe.ma`)** bằng **Windows Named Pipe** (`\\.\pipe\MsNativeMCP`). Tốc độ thực thi tiệm cận native (~0.05-0.2ms/call, nhanh hơn COM 10-50x), hỗ trợ **Batch Draw** (tạo hàng trăm đối tượng trong 1 transaction/round-trip), và **Undo Groups**.
  - **Mode 2 (COM Fallback):** Tự động chuyển đổi hoặc dùng song song khi chưa load MDL application, bảo đảm tính sẵn sàng 100%.
- **Công cụ bảo toàn ngữ cảnh & phòng ngừa sai lệch:** Cung cấp `get_model_snapshot` và `native_get_active_settings` giúp AI nắm bắt trạng thái thực tế của bản vẽ (bounding box, element count, active symbology) trước khi vẽ.
- **Hỗ trợ đầy đủ bộ ba MCP:**
  - **Tools (133 công cụ):** Toàn bộ primitive CAD 2D/3D, batch native, transaction control, và COM tools.
  - **Resources:** Cung cấp thông tin trực tiếp về bản vẽ (`ms://drawing/info`), danh sách level (`ms://drawing/levels`), trạng thái active (`ms://drawing/settings`).
  - **Prompts:** Khuôn mẫu hướng dẫn quy trình vẽ kỹ thuật (`cad_drawing_workflow`) và kiểm toán bản vẽ (`element_inspection`).
- **Đa kênh truyền tải (Transports):** Hỗ trợ cả `stdio` (cho Antigravity / Claude Desktop) và `sse` (Server-Sent Events qua HTTP).
- **An toàn luồng:** Quản lý an toàn luồng Overlapped I/O cho Named Pipe và COM Apartment riêng biệt trên từng worker thread.
- **Logging an toàn:** Toàn bộ log được định tuyến ra `sys.stderr`, bảo toàn 100% định dạng JSON-RPC trên kênh `stdout`.

---

## ⚡ So Sánh Hiệu Năng (COM vs MDL Named Pipe)

| Thao tác | COM Out-of-Process | MDL Native Named Pipe | Cải thiện |
|---|---|---|---|
| Vẽ 1 đoạn thẳng (`draw_line`) | ~3.0 ms | **~0.15 ms** | **20x nhanh hơn** |
| Tạo 100 đoạn thẳng tuần tự | ~300 ms | **~15 ms** | **20x nhanh hơn** |
| Batch tạo 100 đối tượng hỗn hợp | ~300 ms (100 calls) | **~3 ms** (1 round-trip) | **100x nhanh hơn** |
| Quét 500 phần tử (`scan_elements`) | ~2,000 ms | **~50 ms** | **40x nhanh hơn** |
| Lấy snapshot model (`get_model_snapshot`) | ~10,000 ms | **~200 ms** | **50x nhanh hơn** |
| Giao dịch Undo/Redo | Không hỗ trợ native | `begin_transaction` / `end_transaction` | **Native Undo Group** |

---

## 📁 Cấu Trúc Thư Mục

```text
microstation-mcp/
├── README.md                   # Tài liệu tổng quan & hướng dẫn cài đặt
├── AGENTS.md                   # Cẩm nang chỉ dẫn cho AI Agent
├── pyproject.toml              # Metadata dự án chuẩn PEP 621
├── requirements.txt            # Thư viện phụ thuộc
│
├── mdl/                        # Ứng dụng C++ Native chạy trong ustation.exe
│   ├── build_instructions.md   # Hướng dẫn biên dịch chi tiết (VS2005/2008 + V8i SDK)
│   └── MsNativePipe/
│       ├── MsNativePipe.mke    # Makefile bmake cho MDL
│       ├── MsNativePipe.cpp    # Entry point MdlMain, Timer loop
│       ├── pipe_server.h/.cpp  # Named Pipe Server (Overlapped I/O, Thread-safe)
│       ├── handlers.h/.cpp     # Dispatcher & 25 CAD Command Handlers
│       ├── geometry.h/.cpp     # MDL Geometry APIs (Native primitives & transforms)
│       ├── batch.h/.cpp        # Batch creation & Undo grouping
│       └── json_lite.h         # Header-only JSON parser/builder (zero dependency)
│
├── docs/                       # Tài liệu thiết kế nội bộ
│   ├── architecture_native.md  # Kiến trúc chi tiết luồng IPC và Wire Protocol
│   ├── architecture.md         # Kiến trúc phân tầng
│   └── features.md             # Danh mục công cụ
│
└── src/
    ├── main.py                 # Entry point chính (hỗ trợ --transport stdio|sse)
    ├── core/                   # Cầu nối IPC (Named Pipe client & COM bridge)
    │   ├── pipe_client.py      # Win32 Named Pipe client với auto-reconnect
    │   ├── _pipe_singleton.py  # Singleton quản lý kết nối pipe
    │   └── ms_bridge.py        # COM bridge fallback
    ├── server/                 # McpServer factory, logging, context
    ├── tools/                  # 18 module công cụ CAD (133 tools)
    │   ├── native_batch.py     # Batch, transaction & snapshot tools (Native)
    │   ├── drawing_native.py   # Primitive drawing tools (Native)
    │   └── ...                 # Các công cụ COM hiện hữu
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
        "{path}\\microstation-mcp\\src\\main.py"
      ]
    }
  }
}
```

### 3. Chạy độc lập qua giao thức SSE (Tùy chọn)
```bash
python src/main.py --transport sse --host 127.0.0.1 --port 8000
```

---

## 🛠️ Danh Mục 8 Công Cụ Hợp Nhất (Consolidated Tools v3.0)

Lấy cảm hứng từ kiến trúc của **AutoCAD MCP v3.1**, hệ thống hợp nhất 147 công cụ vi mô thành **8 công cụ cốt lõi**, giúp giảm 95% token schema, tăng tốc độ phản hồi và ngăn ngừa hoàn toàn tình trạng AI bị loop:

| Tool | Chức năng chính | Operations tiêu biểu |
|---|---|---|
| **`drawing`** | Quản lý tệp DGN & Khung vẽ | `info`, `open`, `save`, `create`, `models`, `references`, `undo`, `redo` |
| **`entity`** | CRUD đối tượng 2D / 3D | `create_line`, `create_linestring`, `create_shape`, `create_circle`, `create_arc`, `list`, `count`, `get`, `move`, `rotate`, `scale`, `erase`, `batch_create` |
| **`layer`** | Quản lý lớp bản vẽ (Level) | `list`, `create`, `set_active`, `set_display` |
| **`cell`** | Quản lý Cell & Khối thư viện | `list`, `place`, `drop` |
| **`annotation`** | Ghi chú & Đo kích thước | `create_text`, `create_dimension_linear`, `create_dimension_aligned`, `find_text`, `replace_text` |
| **`view`** | Khung nhìn & Chụp ảnh đối soát | `fit_view`, `zoom_window`, `zoom_in`, `zoom_out`, `get_screenshot` *(trả về ImageContent đối soát)* |
| **`cadastral`** | Chuyên gia Địa chính VN (TT 26/2024 & TT 23/2025) | `auto_workflow` *(giải quyết trọn gói ranh thửa L10, chuyển mục đích L10 nét đứt, lộ giới L50, đánh số mốc, ghi kích thước cạnh, dựng bảng tọa độ VN-2000)*, `analyze`, `draw_table`, `draw_parcel_label` |
| **`system`** | Quản trị & Thực thi mã nội bộ | `status`, `health`, `execute_keyin`, `execute_python` *(chạy Python an toàn trong server)* |
