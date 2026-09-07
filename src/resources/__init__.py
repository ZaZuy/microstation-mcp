"""
src/resources package
Hợp nhất và đăng ký toàn bộ MCP Resources.
"""

from src.resources.drawing import register_drawing_resources
from src.resources.levels import register_levels_resources


def register_resources(mcp):
    """Đăng ký tất cả các Resource vào MCP Server."""
    register_drawing_resources(mcp)
    register_levels_resources(mcp)


__all__ = ["register_resources"]
