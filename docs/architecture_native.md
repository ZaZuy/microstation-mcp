# Kiến Trúc Native — MicroStation V8i MCP Server

## Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AI Client (Antigravity / Claude)                    │
│                         stdio / SSE (JSON-RPC 2.0)                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  Python MCP Server (FastMCP)                            │
│                   src/main.py → src/server/__init__.py                  │
│                                                                         │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐  │
│  │   COM Tools (62+)    │    │       Native Pipe Tools (23+)        │  │
│  │  src/tools/*.py      │    │  src/tools/drawing_native.py         │  │
│  │  src/tools/drawing   │    │  src/tools/native_batch.py           │  │
│  │  src/tools/modify    │    │                                      │  │
│  │  src/tools/query     │    │  Prefix: native_*, batch_draw_*,     │  │
│  │  ...                 │    │  get_model_snapshot, begin/end_trans  │  │
│  └──────────┬───────────┘    └─────────────────┬────────────────────┘  │
│             │                                   │                       │
│  ┌──────────▼───────────┐    ┌─────────────────▼────────────────────┐  │
│  │  src/core/ms_bridge  │    │      src/core/pipe_client.py         │  │
│  │  (COM out-of-process)│    │      (Named Pipe IPC client)         │  │
│  └──────────┬───────────┘    └─────────────────┬────────────────────┘  │
└─────────────│──────────────────────────────────│────────────────────────┘
              │                                   │
              │ COM RPC (~1-5ms/call)             │ Named Pipe (~0.1ms/call)
              │ Cross-process                     │ In-process MDL
              │                                   │
              ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MicroStation V8i (ustation.exe)                      │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    MDL Native App (MsNativePipe.ma)               │  │
│  │                                                                   │  │
│  │  [Windows Thread: Pipe Server]    [MDL Main Thread]               │  │
│  │  pipe_server.cpp                  MsNativePipe.cpp                │  │
│  │  ┌──────────────────┐            ┌─────────────────────────────┐  │  │
│  │  │ CreateNamedPipe  │   Events   │ mdlSystem_startTimer(50ms)  │  │  │
│  │  │ ConnectNamedPipe │ ─────────→ │ TimerCallback()             │  │  │
│  │  │ ReadFile()       │            │ HandleRequest()             │  │  │
│  │  │ WriteFile()      │ ←───────── │ handlers.cpp                │  │  │
│  │  └──────────────────┘            └─────────────────────────────┘  │  │
│  │                                          │                         │  │
│  │                                  ┌───────▼──────────────────────┐ │  │
│  │                                  │  MDL API (geometry.cpp)       │ │  │
│  │                                  │  mdlLine_create()             │ │  │
│  │                                  │  mdlShape_create()            │ │  │
│  │                                  │  mdlArc_create2()             │ │  │
│  │                                  │  mdlElmdscr_add()             │ │  │
│  │                                  │  mdlUndo_startGroup()         │ │  │
│  │                                  │  mdlModify_*()                │ │  │
│  │                                  └───────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                 MicroStation DGN Engine                           │  │
│  │  (Element storage, rendering, UOR system, level manager, ...)    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Luồng dữ liệu — Tạo element qua Named Pipe

```
AI → MCP Server → pipe_client.send_command("draw_line", {x1,y1,x2,y2}) 
  → [4-byte length][JSON bytes] → Windows Named Pipe
  → MDL Pipe Thread: ReadFile() → g_requestMsg
  → SetEvent(g_hRequestEvent)
  → MDL Main Thread (timer 50ms): HandleRequest()
    → handlers.cpp dispatch → "draw_line" → CreateLine()
    → geometry.cpp: mdlLine_create() → mdlElmdscr_add()
    → element_id = mdlElement_getFilePos()
  → g_responseMsg = {"success":true,"data":{"element_id":"123"}}
  → SetEvent(g_hResponseEvent)
  → MDL Pipe Thread: WriteFile() → [4-byte length][JSON bytes]
  → pipe_client: recv_frame() → parse JSON → return dict
  → MCP Server: tool returns JSON string → AI receives result
```

**Tổng thời gian**: ~0.1-0.3ms (vs ~1-5ms COM)

---

## Luồng dữ liệu — Batch tạo 100 element

```
AI → batch_draw_elements([100 element defs], use_undo_group=True)
  → pipe_client.send_batch()
  → 1 lần WriteFile (1 JSON lớn)
  → MDL: HandleRequest("batch_create")
    → batch.cpp: BatchCreate()
    → mdlUndo_startGroup()
    → loop 100: CreateLine/Circle/Arc/...
    → mdlUndo_endGroup()
    → return [{id1}, {id2}, ..., {id100}]
  → 1 lần ReadFile
  → 100 element IDs trả về AI

Thời gian: ~3ms (vs ~300ms nếu gọi 100 lần COM riêng lẻ)
```

---

## Wire Protocol — Named Pipe

### Frame format
```
┌──────────────────────┬───────────────────────────────────┐
│  Header (4 bytes)    │  Payload (N bytes)                 │
│  uint32 LE = N       │  UTF-8 JSON string                 │
└──────────────────────┴───────────────────────────────────┘
```

### Request JSON
```json
{
  "id": 42,
  "cmd": "draw_line",
  "params": {
    "x1": 0.0, "y1": 0.0, "z1": 0.0,
    "x2": 100.0, "y2": 50.0, "z2": 0.0,
    "level": "Default",
    "color": 2,
    "weight": 1,
    "style": 0
  }
}
```

### Response JSON (success)
```json
{
  "id": 42,
  "success": true,
  "data": {
    "element_id": "4503599627370496",
    "type": "Line",
    "level": "Default",
    "color": 2,
    "weight": 1
  },
  "message": "OK"
}
```

### Response JSON (error)
```json
{
  "id": 42,
  "success": false,
  "data": null,
  "message": "Không tìm thấy level 'XYZ' trong file DGN"
}
```

### Batch Request
```json
{
  "id": 43,
  "cmd": "batch_create",
  "params": {
    "undo_group": true,
    "elements": [
      {"type": "line", "x1":0,"y1":0,"z1":0,"x2":100,"y2":0,"z2":0},
      {"type": "arc",  "cx":50,"cy":0,"cz":0,"radius":50,"start_angle":0,"sweep_angle":180},
      {"type": "text", "x":10,"y":20,"z":0,"text":"Nhà A1","height":3.5}
    ]
  }
}
```

---

## Danh sách đầy đủ các commands MDL hỗ trợ

### Geometry Creation
| Command | Params | Mô tả |
|---------|--------|-------|
| `draw_line` | x1,y1,z1,x2,y2,z2,level,color,weight,style | Đoạn thẳng |
| `draw_linestring` | points[[x,y,z]],level,color,weight,style | Đường gấp khúc |
| `draw_shape` | points[[x,y,z]],filled,fill_color,level,... | Polygon |
| `draw_circle` | cx,cy,cz,radius,level,color,weight,style | Đường tròn |
| `draw_arc` | cx,cy,cz,radius,start_angle,sweep_angle,... | Cung tròn |
| `draw_ellipse` | cx,cy,cz,primary_r,secondary_r,rotation,... | Ellipse |
| `draw_point` | x,y,z,level,color,weight | Điểm mốc |
| `place_text` | x,y,z,text,height,rotation,level,color | Văn bản |
| `batch_create` | undo_group,elements[] | Tạo nhiều element |

### Modification
| Command | Params | Mô tả |
|---------|--------|-------|
| `move_element` | element_id,dx,dy,dz | Di chuyển |
| `copy_element` | element_id,dx,dy,dz | Sao chép |
| `rotate_element` | element_id,cx,cy,cz,angle_degrees | Xoay |
| `scale_element` | element_id,cx,cy,cz,scale_x,scale_y,scale_z | Scale |
| `delete_element` | element_id | Xóa |
| `change_symbology` | element_id,level,color,weight,style | Đổi thuộc tính |

### Query
| Command | Params | Mô tả |
|---------|--------|-------|
| `get_drawing_info` | — | Thông tin file/model |
| `get_active_settings` | — | Active level/color/weight/style |
| `scan_elements` | type_filter,max_count | Quét element |
| `get_element_details` | element_id | Chi tiết 1 element |
| `get_model_snapshot` | max_elements | Toàn bộ model |

### Active Settings
| Command | Params | Mô tả |
|---------|--------|-------|
| `set_active_level` | level_name | Đặt active level |
| `set_active_color` | color | Đặt active color |
| `set_active_weight` | weight | Đặt active weight |

### Transaction
| Command | Params | Mô tả |
|---------|--------|-------|
| `begin_transaction` | description | Bắt đầu undo group |
| `end_transaction` | — | Kết thúc undo group |
| `cancel_transaction` | — | Hủy undo group |

### Utility
| Command | Params | Mô tả |
|---------|--------|-------|
| `ping` | — | Kiểm tra kết nối |

---

## So sánh hiệu suất

```
Thao tác                 │ COM (cũ) │ Named Pipe MDL │ Cải thiện
─────────────────────────┼──────────┼────────────────┼───────────
draw_line (1 lần)        │   ~3ms   │   ~0.15ms      │   20x
draw_line (100 lần)      │  ~300ms  │    ~15ms       │   20x
batch 100 elements       │  ~300ms  │     ~3ms       │  100x
scan 500 elements        │   ~2s    │    ~50ms       │   40x
get_drawing_info         │   ~1ms   │   ~0.1ms       │   10x
get_model_snapshot(2000) │   ~10s   │   ~200ms       │   50x
```

---

## Cấu trúc thư mục đầy đủ sau khi implement

```
microstation-mcp/
├── mdl/                               ← MDL Native App
│   ├── build_instructions.md          ← Hướng dẫn biên dịch
│   └── MsNativePipe/
│       ├── MsNativePipe.mke           ← Makefile MDL
│       ├── MsNativePipe.cpp           ← Entry point + timer
│       ├── json_lite.h                ← Tiny JSON header-only
│       ├── pipe_server.h / .cpp       ← Named Pipe server thread
│       ├── handlers.h / .cpp          ← Command dispatcher
│       ├── geometry.h / .cpp          ← MDL API geometry ops
│       └── batch.h / .cpp             ← Batch + undo group
│
└── src/
    ├── main.py                        ← Entry point (không đổi)
    ├── core/
    │   ├── ms_bridge.py               ← COM bridge (giữ nguyên)
    │   └── pipe_client.py             ← [NEW] Named Pipe client
    ├── tools/
    │   ├── __init__.py                ← [UPDATED] đăng ký native tools
    │   ├── drawing.py                 ← COM drawing (giữ nguyên)
    │   ├── drawing_native.py          ← [NEW] Native drawing tools
    │   ├── native_batch.py            ← [NEW] Batch/transaction/snapshot
    │   └── ... (các module khác giữ nguyên)
    └── ...
```

---

## Chiến lược dual-mode

Server hiện tại hỗ trợ **cả hai mode** cùng lúc:

```
AI gọi draw_line()        → COM (luôn sẵn sàng, không cần MDL)
AI gọi native_draw_line() → Named Pipe MDL (cần load MDL trước)
AI gọi batch_draw_elements() → Named Pipe MDL (pipe-only)
AI gọi get_model_snapshot() → Named Pipe MDL (pipe-only)
```

**Gợi ý workflow tối ưu cho AI:**
1. Gọi `get_pipe_status()` để kiểm tra MDL có sẵn không
2. Nếu `connected: true`: dùng `native_*` tools và `batch_draw_elements` cho tốc độ cao
3. Nếu `connected: false`: dùng COM tools bình thường (`draw_line`, `draw_circle`, ...)
4. Trước khi vẽ lớn: gọi `get_model_snapshot()` để biết context, tránh vẽ sai
