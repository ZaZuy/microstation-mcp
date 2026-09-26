"""
src/core package
Lõi giao tiếp với MicroStation V8i — hỗ trợ cả COM và Named Pipe.
"""
from src.core.ms_bridge import MicroStationBridge, bridge
from src.core.pipe_client import PipeClient, PipeConnectionError, PipeTimeoutError
from src.core._pipe_singleton import get_pipe_client, reset_pipe_client

__all__ = [
    "MicroStationBridge",
    "bridge",
    "PipeClient",
    "PipeConnectionError",
    "PipeTimeoutError",
    "get_pipe_client",
    "reset_pipe_client",
]
