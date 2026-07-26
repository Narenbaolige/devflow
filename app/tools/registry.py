"""
工具注册表。

每个工具通过 ToolDefinition 注册，声明其权限级别和可使用的 Agent。
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ToolPermission(StrEnum):
    """工具权限级别"""
    READ_ONLY = "read_only"              # 不修改任何文件，可在任何环境执行
    WRITE_SANDBOX = "write_sandbox"      # 在沙箱工作区内修改文件
    EXECUTE_SANDBOX = "execute_sandbox"  # 在沙箱内执行命令


class ToolDefinition(BaseModel):
    """工具注册定义"""
    name: str
    description: str
    permission: ToolPermission
    parameters: dict = Field(default_factory=dict)  # JSON Schema
    allowed_agents: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = 10


# =============================================================================
# 工具注册表
# =============================================================================

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # --- 文件读取 ---
    "read_file": ToolDefinition(
        name="read_file",
        description="读取指定文件的完整内容",
        permission=ToolPermission.READ_ONLY,
        allowed_agents=["planner", "developer", "reviewer", "security"],
    ),
    "list_dir": ToolDefinition(
        name="list_dir",
        description="列出目录下的文件和子目录",
        permission=ToolPermission.READ_ONLY,
        allowed_agents=["requirement", "planner", "developer"],
    ),
    "glob": ToolDefinition(
        name="glob",
        description="按 glob 模式匹配文件路径（如 **/*.py）",
        permission=ToolPermission.READ_ONLY,
        allowed_agents=["planner", "developer"],
    ),

    # --- 代码搜索 ---
    "grep": ToolDefinition(
        name="grep",
        description="在代码仓库中搜索正则模式，返回匹配的文件和行",
        permission=ToolPermission.READ_ONLY,
        allowed_agents=["planner", "developer", "reviewer", "security"],
    ),

    # --- 文件修改 ---
    "write_file": ToolDefinition(
        name="write_file",
        description="在沙箱工作区中写入或覆盖文件",
        permission=ToolPermission.WRITE_SANDBOX,
        allowed_agents=["developer"],
    ),
    "edit_file": ToolDefinition(
        name="edit_file",
        description="精确替换文件中的指定字符串（old_string → new_string）",
        permission=ToolPermission.WRITE_SANDBOX,
        allowed_agents=["developer"],
    ),

    # --- 沙箱命令执行 ---
    "sandbox_execute": ToolDefinition(
        name="sandbox_execute",
        description=(
            "在沙箱中执行 shell 命令。Agent 自行决定跑什么命令、如何解读结果。"
            "沙箱不限制语言和工具，Python/Rust/Go/C++/JS 均可。"
        ),
        permission=ToolPermission.EXECUTE_SANDBOX,
        parameters={
            "command": {"type": "string", "description": "要执行的 shell 命令"},
            "cwd": {"type": "string", "description": "工作目录，默认 /workspace"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 60"},
        },
        allowed_agents=["developer"],
        rate_limit_per_minute=10,
    ),

    # --- 向后兼容别名 ---
    "execute_test": ToolDefinition(
        name="execute_test",
        description="[已废弃] 使用 sandbox_execute 替代。在沙箱中运行 pytest。",
        permission=ToolPermission.EXECUTE_SANDBOX,
        allowed_agents=["developer"],
        rate_limit_per_minute=5,
    ),
    "execute_command": ToolDefinition(
        name="execute_command",
        description="[已废弃] 使用 sandbox_execute 替代。在沙箱中执行 shell 命令。",
        permission=ToolPermission.EXECUTE_SANDBOX,
        allowed_agents=["developer"],
    ),
}


def get_tools_for_agent(agent_name: str) -> list[ToolDefinition]:
    """获取指定 Agent 可用的工具列表。"""
    return [
        tool for tool in TOOL_REGISTRY.values()
        if agent_name in tool.allowed_agents
    ]
