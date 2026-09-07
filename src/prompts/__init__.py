"""
src/prompts package
Hợp nhất và đăng ký tất cả các Prompt vào MCP Server.
"""

from src.prompts.drawing_workflow import register_drawing_workflow_prompt
from src.prompts.element_inspection import register_element_inspection_prompt


def register_prompts(mcp):
    """Đăng ký tất cả các MCP Prompts."""
    register_drawing_workflow_prompt(mcp)
    register_element_inspection_prompt(mcp)


__all__ = ["register_prompts"]
