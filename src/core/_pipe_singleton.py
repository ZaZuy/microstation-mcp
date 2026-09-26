

# ---------------------------------------------------------------------------
# Singleton instance dùng chung toàn hệ thống
# ---------------------------------------------------------------------------
from src.core.pipe_client import PipeClient

_pipe_client_instance = None
_pipe_client_lock = __import__("threading").Lock()


def get_pipe_client() -> "PipeClient":
    """
    Lấy singleton PipeClient. Tạo mới nếu chưa có.

    Sử dụng pattern này để tránh tạo nhiều kết nối pipe cùng lúc.
    """
    global _pipe_client_instance
    if _pipe_client_instance is None:
        with _pipe_client_lock:
            if _pipe_client_instance is None:
                _pipe_client_instance = PipeClient(auto_connect=False)
    return _pipe_client_instance


def reset_pipe_client() -> None:
    """
    Reset singleton PipeClient.
    Dùng khi cần reconnect sau lỗi nghiêm trọng hoặc khi test.
    """
    global _pipe_client_instance
    with _pipe_client_lock:
        if _pipe_client_instance is not None:
            _pipe_client_instance.close()
        _pipe_client_instance = None
