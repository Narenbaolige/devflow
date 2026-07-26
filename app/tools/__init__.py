"""工具系统模块 — 注册表 + 可调用实现。"""

from app.tools.file_ops import (
    ToolResult,
    edit_file,
    glob,
    list_dir,
    read_file,
    set_workspace,
    write_file,
)
from app.tools.registry import TOOL_REGISTRY, ToolDefinition, ToolPermission
from app.tools.sandbox_ops import sandbox_execute
from app.tools.search import grep

# 工具执行映射：将注册表名称映射到可调用函数
TOOL_EXECUTORS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_dir": list_dir,
    "glob": glob,
    "grep": grep,
    "sandbox_execute": sandbox_execute,
    # 向后兼容别名
    "execute_test": sandbox_execute,
    "execute_command": sandbox_execute,
}

__all__ = [
    "TOOL_REGISTRY",
    "TOOL_EXECUTORS",
    "ToolDefinition",
    "ToolPermission",
    "ToolResult",
    "read_file",
    "write_file",
    "edit_file",
    "list_dir",
    "glob",
    "grep",
    "sandbox_execute",
    "set_workspace",
]
