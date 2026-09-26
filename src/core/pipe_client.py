"""
src/core/pipe_client.py
Named Pipe client để giao tiếp với MDL Native App trong MicroStation V8i.
Đây là kênh IPC hiệu năng cao, thay thế COM out-of-process cho các thao tác vẽ chính.

Giao thức wire format:
  - 4-byte uint32 little-endian: độ dài payload
  - N bytes: JSON UTF-8 payload
  - Kích thước tối đa 1 message: 512 KB

Sử dụng:
    with PipeClient() as client:
        result = client.send_command('draw_line', {'x1':0,'y1':0,'x2':100,'y2':0})
"""

import struct
import json
import threading
import time
import sys
import logging
from typing import Any, Dict, List, Optional

# Chỉ import win32 API trên Windows
if sys.platform == 'win32':
    try:
        import win32pipe
        import win32file
        import pywintypes
        _WIN32_AVAILABLE = True
    except ImportError:
        _WIN32_AVAILABLE = False
else:
    _WIN32_AVAILABLE = False

# ─────────────────────────── Hằng số ───────────────────────────
PIPE_NAME           = r'\\.\pipe\MsNativeMCP'   # Tên Named Pipe (phải khớp với MDL side)
CONNECT_TIMEOUT_MS  = 2_000                       # Timeout kết nối ban đầu (ms)
REQUEST_TIMEOUT_MS  = 10_000                      # Timeout mỗi request (ms)
MAX_RETRIES         = 3                           # Số lần retry tối đa khi gửi lệnh
BUFFER_SIZE         = 512 * 1024                  # Kích thước buffer tối đa = 512 KB
FRAME_HEADER_SIZE   = 4                           # 4 bytes uint32 little-endian length prefix
_RECONNECT_DELAYS   = [0.1, 0.5, 1.0]            # Backoff delays (giây) khi reconnect

logger = logging.getLogger(__name__)


# ─────────────────────────── Exceptions ───────────────────────────

class PipeError(RuntimeError):
    """Base exception cho mọi lỗi Named Pipe."""
    pass


class PipeConnectionError(PipeError):
    """Không thể kết nối hoặc mất kết nối tới Named Pipe."""
    pass


class PipeTimeoutError(PipeError):
    """Request vượt quá thời gian chờ cho phép."""
    pass


class PipeProtocolError(PipeError):
    """Lỗi giao thức: frame không hợp lệ hoặc JSON bị lỗi."""
    pass


# ─────────────────────────── PipeClient ───────────────────────────

class PipeClient:
    """
    Client giao tiếp với MDL Native App qua Windows Named Pipe.

    Thread-safe: nhiều thread có thể gọi send_command() đồng thời nhờ _lock.
    Hỗ trợ context manager (with ... as ...).

    Giao thức:
        → [4-byte uint32 LE length][JSON UTF-8 payload]
        ← [4-byte uint32 LE length][JSON UTF-8 payload]
    """

    def __init__(self, pipe_name: str = PIPE_NAME, auto_connect: bool = True) -> None:
        """
        Khởi tạo PipeClient.

        Args:
            pipe_name:    Ten pipe day du, mac dinh PIPE_NAME = '\\\\\\\\.\\\\pipe\\\\MsNativeMCP'.
            auto_connect: Neu True, thu ket noi ngay khi khoi tao object.
        """
        self._pipe_name: str            = pipe_name
        self._handle: Any               = None          # win32file HANDLE
        self._lock: threading.Lock      = threading.Lock()
        self._request_counter: int      = 0             # Auto-increment request ID

        if auto_connect:
            try:
                self._connect()
            except PipeConnectionError as exc:
                # Không raise khi auto_connect - chỉ log warning, retry khi dùng
                logger.warning("PipeClient: Kết nối ban đầu thất bại: %s", exc)

    # ───────────────── Context Manager ─────────────────

    def __enter__(self) -> "PipeClient":
        """Hỗ trợ 'with PipeClient() as client'."""
        if not self.is_connected():
            self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Đóng pipe khi thoát khỏi context."""
        self._disconnect()
        return False  # Không suppress exceptions

    # ───────────────── Kết nối / Ngắt kết nối ─────────────────

    def _connect(self) -> bool:
        """
        Mở Named Pipe handle tới MDL Native App.

        Dùng blocking mode (không OVERLAPPED) cho đơn giản và tương thích tốt nhất
        với MDL server. Pipe phải đã được tạo bởi MDL trước khi gọi hàm này.

        Returns:
            True nếu kết nối thành công.

        Raises:
            PipeConnectionError: Nếu không thể mở pipe (MDL chưa chạy, v.v.)
        """
        if not _WIN32_AVAILABLE:
            raise PipeConnectionError(
                "pywin32 không có sẵn hoặc không chạy trên Windows. "
                "Named Pipe chỉ hoạt động trên Windows."
            )

        # Đóng handle cũ nếu còn
        self._disconnect()

        # Chờ pipe sẵn sàng (MDL có thể đang bận tạo pipe)
        deadline = time.time() + CONNECT_TIMEOUT_MS / 1000.0
        last_err: Optional[Exception] = None
        attempted_auto_load = False

        while time.time() < deadline:
            try:
                handle = win32file.CreateFile(
                    self._pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,          # Không share
                    None,       # Default security
                    win32file.OPEN_EXISTING,
                    0,          # Blocking mode (không FILE_FLAG_OVERLAPPED)
                    None,
                )
                self._handle = handle
                logger.info("PipeClient: Kết nối thành công tới %s", self._pipe_name)
                return True
            except pywintypes.error as exc:
                last_err = exc
                error_code = exc.args[0]
                if error_code == 2:    # ERROR_FILE_NOT_FOUND - pipe chưa tồn tại
                    if not attempted_auto_load:
                        attempted_auto_load = True
                        if self._try_auto_load_mdl():
                            time.sleep(0.3)
                            continue
                    break
                elif error_code == 231: # ERROR_PIPE_BUSY - server bận, chờ pipe rảnh
                    try:
                        win32pipe.WaitNamedPipe(self._pipe_name, 500)
                    except pywintypes.error:
                        pass
                    continue
                else:
                    break  # Lỗi khác, không retry

        raise PipeConnectionError(
            f"Không thể mở pipe '{self._pipe_name}'. "
            f"Kiểm tra MDL App 'MsNativePipe.ma' đã load trong MicroStation. "
            f"Lỗi: {last_err}"
        )

    def _try_auto_load_mdl(self) -> bool:
        """Thử tự động nạp ứng dụng MDL MsNativePipe vào MicroStation qua COM Key-in."""
        try:
            from src.core.ms_bridge import bridge
            app = bridge.get_app(require_file=False)
            if app:
                logger.info("PipeClient: Đang tự động gửi lệnh 'mdl load MsNativePipe' qua COM...")
                app.CadInputQueue.SendCommand("mdl load MsNativePipe")
                return True
        except Exception as ex:
            logger.debug(f"PipeClient: Không thể tự động nạp MDL qua COM: {ex}")
        return False

    def _disconnect(self) -> None:
        """
        Đóng pipe handle một cách an toàn.
        Không raise exception - luôn thành công (idempotent).
        """
        if self._handle is not None:
            try:
                win32file.CloseHandle(self._handle)
            except Exception as exc:
                logger.debug("PipeClient: Lỗi khi đóng handle: %s", exc)
            finally:
                self._handle = None
                logger.debug("PipeClient: Đã ngắt kết nối.")

    # ───────────────── Kiểm tra trạng thái ─────────────────

    def is_connected(self) -> bool:
        """
        Kiểm tra pipe handle hiện tại có hợp lệ không.

        Note: Chỉ kiểm tra handle != None, không gửi ping.
              Dùng ping() để kiểm tra kết nối thực sự end-to-end.

        Returns:
            True nếu handle đang mở.
        """
        return self._handle is not None

    def ping(self) -> bool:
        """
        Gửi lệnh 'ping' tới MDL và kiểm tra response.

        Dùng để xác nhận MDL Native App đang hoạt động và sẵn sàng nhận lệnh.

        Returns:
            True nếu MDL phản hồi 'pong' thành công, False trong mọi trường hợp lỗi.
        """
        try:
            response = self.send_command('ping', {}, request_id=-1)
            return response.get('status') in ('ok', 'pong')
        except (PipeError, Exception):
            return False

    # ───────────────── Gửi / Nhận frame ─────────────────

    def _send_frame(self, data: bytes) -> None:
        """
        Ghi một frame vào pipe: [4-byte uint32 LE length][data].

        Args:
            data: Payload bytes cần gửi. Kích thước tối đa = BUFFER_SIZE.

        Raises:
            PipeConnectionError: Nếu handle không hợp lệ hoặc ghi thất bại.
            PipeProtocolError:   Nếu data vượt quá BUFFER_SIZE.
        """
        if len(data) > BUFFER_SIZE:
            raise PipeProtocolError(
                f"Payload quá lớn: {len(data)} bytes > giới hạn {BUFFER_SIZE} bytes."
            )
        if not self.is_connected():
            raise PipeConnectionError("Pipe chưa được kết nối.")

        # Tạo frame: header (4 bytes LE uint32) + payload
        header = struct.pack('<I', len(data))
        frame  = header + data

        try:
            win32file.WriteFile(self._handle, frame)
        except pywintypes.error as exc:
            self._disconnect()
            raise PipeConnectionError(
                f"Lỗi ghi pipe: {exc.args[2]} (code {exc.args[0]})"
            ) from exc

    def _recv_frame(self) -> bytes:
        """
        Đọc một frame từ pipe: đọc 4 bytes header, rồi đọc đúng length bytes payload.

        Returns:
            Payload bytes nhận được.

        Raises:
            PipeConnectionError: Nếu pipe bị đóng hoặc đọc thất bại.
            PipeProtocolError:   Nếu length trong header vượt BUFFER_SIZE hoặc = 0.
        """
        if not self.is_connected():
            raise PipeConnectionError("Pipe chưa được kết nối.")

        # Bước 1: Đọc 4 bytes header
        try:
            _, header_bytes = win32file.ReadFile(self._handle, FRAME_HEADER_SIZE)
        except pywintypes.error as exc:
            self._disconnect()
            raise PipeConnectionError(
                f"Lỗi đọc header pipe: {exc.args[2]} (code {exc.args[0]})"
            ) from exc

        if len(header_bytes) < FRAME_HEADER_SIZE:
            self._disconnect()
            raise PipeConnectionError("Pipe đóng bất ngờ khi đọc header.")

        # Bước 2: Giải mã length
        (payload_length,) = struct.unpack('<I', header_bytes)
        if payload_length == 0:
            raise PipeProtocolError("Frame có length = 0, không hợp lệ.")
        if payload_length > BUFFER_SIZE:
            raise PipeProtocolError(
                f"Frame length {payload_length} vượt giới hạn {BUFFER_SIZE} bytes."
            )

        # Bước 3: Đọc đúng payload_length bytes
        received = bytearray()
        remaining = payload_length
        try:
            while remaining > 0:
                _, chunk = win32file.ReadFile(self._handle, min(remaining, 65536))
                if not chunk:
                    break
                received.extend(chunk)
                remaining -= len(chunk)
        except pywintypes.error as exc:
            self._disconnect()
            raise PipeConnectionError(
                f"Lỗi đọc payload pipe: {exc.args[2]} (code {exc.args[0]})"
            ) from exc

        if len(received) != payload_length:
            raise PipeProtocolError(
                f"Payload không đủ: nhận {len(received)}, mong đợi {payload_length} bytes."
            )

        return bytes(received)

    # ───────────────── Gửi lệnh chính ─────────────────

    def send_command(
        self,
        cmd: str,
        params: Dict[str, Any],
        request_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gửi một lệnh tới MDL Native App và chờ response.

        Frame gửi đi (JSON):
            {"id": <int>, "cmd": "<command>", "params": {...}}

        Frame nhận về (JSON):
            {"id": <int>, "status": "ok"|"error", "result": {...}, "message": "..."}

        Args:
            cmd:        Tên lệnh MDL (ví dụ: 'draw_line', 'get_active_settings').
            params:     Dict tham số của lệnh.
            request_id: ID tùy chỉnh (None = auto-increment).

        Returns:
            Dict kết quả từ MDL (trường 'result' hoặc toàn bộ response).

        Raises:
            PipeConnectionError: Không thể kết nối sau MAX_RETRIES lần.
            PipeTimeoutError:    MDL không phản hồi trong REQUEST_TIMEOUT_MS.
            PipeProtocolError:   Response JSON không hợp lệ.
        """
        with self._lock:
            # Tạo request ID
            if request_id is None:
                self._request_counter += 1
                rid = self._request_counter
            else:
                rid = request_id

            # Serialize payload: hỗ trợ cả 2 key 'command' (MDL native) và 'cmd'
            payload_dict = {"id": rid, "command": cmd, "cmd": cmd, "params": params}
            payload_bytes = json.dumps(payload_dict, ensure_ascii=False).encode('utf-8')

            # Retry logic
            last_exc: Optional[Exception] = None
            for attempt in range(MAX_RETRIES):
                try:
                    # Đảm bảo có kết nối
                    if not self.is_connected():
                        self._auto_reconnect()

                    self._send_frame(payload_bytes)
                    response_bytes = self._recv_frame()

                    # Parse response JSON
                    try:
                        response = json.loads(response_bytes.decode('utf-8'))
                    except json.JSONDecodeError as exc:
                        raise PipeProtocolError(
                            f"Response JSON không hợp lệ: {exc}"
                        ) from exc

                    # Kiểm tra ID khớp (nếu MDL echo lại ID)
                    resp_id = response.get('id')
                    if resp_id is not None and resp_id != rid:
                        logger.warning(
                            "PipeClient: Response ID không khớp: gửi %d, nhận %d", rid, resp_id
                        )

                    # Chuẩn hóa 2 chiều: tương thích cả native C++ (success, data) và Python (status, result)
                    is_ok = (response.get('success') is True) or (response.get('status') == 'ok')
                    data = response.get('data') if response.get('data') is not None else response.get('result', {})

                    response['status'] = 'ok' if is_ok else 'error'
                    response['success'] = is_ok
                    response['result'] = data
                    response['data'] = data

                    # Trích xuất các trường thường dùng lên top-level nếu có trong data
                    if isinstance(data, dict):
                        for k in ('results', 'elements', 'element_id', 'new_element_id', 'model_name'):
                            if k in data and k not in response:
                                response[k] = data[k]

                    return response

                except PipeConnectionError as exc:
                    last_exc = exc
                    logger.warning(
                        "PipeClient: Thử lần %d/%d thất bại cho lệnh '%s': %s",
                        attempt + 1, MAX_RETRIES, cmd, exc
                    )
                    self._disconnect()
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(_RECONNECT_DELAYS[min(attempt, len(_RECONNECT_DELAYS) - 1)])

            raise PipeConnectionError(
                f"Gửi lệnh '{cmd}' thất bại sau {MAX_RETRIES} lần thử. "
                f"Lỗi cuối: {last_exc}"
            )

    def send_batch(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Gửi một batch nhiều lệnh trong một round-trip duy nhất.

        Đây là API tốc độ cao nhất: toàn bộ danh sách commands được đóng gói
        vào một frame JSON duy nhất và MDL xử lý tuần tự, trả về array kết quả.

        Frame gửi đi:
            {"id": <int>, "cmd": "batch_create", "params": {"commands": [...]}}

        Frame nhận về:
            {"id": <int>, "status": "ok", "results": [...]}

        Args:
            commands: Danh sách dict lệnh, mỗi dict có 'type' và tham số tương ứng.
                      Ví dụ: [{"type":"line","x1":0,"y1":0,"x2":100,"y2":0}, ...]

        Returns:
            Danh sách kết quả tương ứng với từng lệnh trong batch.

        Raises:
            PipeConnectionError: Không thể gửi batch.
            PipeProtocolError:   Response không có trường 'results'.
        """
        response = self.send_command('batch_create', {'commands': commands})

        # Trích xuất danh sách kết quả
        if 'results' in response:
            return response['results']
        elif 'result' in response and isinstance(response['result'], list):
            return response['result']
        else:
            raise PipeProtocolError(
                f"Batch response thiếu trường 'results'. Response: {response}"
            )

    # ───────────────── Auto Reconnect ─────────────────

    def _auto_reconnect(self) -> bool:
        """
        Thử kết nối lại với backoff delays.

        Thử lần lượt sau 0.1s, 0.5s, 1.0s (tổng ~1.6s) trước khi từ bỏ.

        Returns:
            True nếu reconnect thành công.

        Raises:
            PipeConnectionError: Nếu tất cả lần thử đều thất bại.
        """
        logger.info("PipeClient: Đang thử reconnect...")
        for i, delay in enumerate(_RECONNECT_DELAYS):
            try:
                self._connect()
                logger.info("PipeClient: Reconnect thành công sau %d lần thử.", i + 1)
                return True
            except PipeConnectionError as exc:
                logger.debug("PipeClient: Reconnect lần %d thất bại: %s", i + 1, exc)
                time.sleep(delay)

        raise PipeConnectionError(
            f"Không thể reconnect tới '{self._pipe_name}' "
            f"sau {len(_RECONNECT_DELAYS)} lần thử."
        )

    # ───────────────── Cleanup ─────────────────

    def close(self) -> None:
        """
        Đóng kết nối pipe thủ công.
        Tương đương với _disconnect(), dùng trong trường hợp không dùng context manager.
        """
        self._disconnect()

    def __del__(self) -> None:
        """Đảm bảo handle được đóng khi object bị garbage collect."""
        self._disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        return f"PipeClient(pipe='{self._pipe_name}', status='{status}')"
