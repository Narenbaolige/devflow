"""
沙箱抽象基类 — 接口契约。

设计原则：沙箱是工具，Agent 是大脑。

沙箱只做一件事：execute(command) → CommandResult。
不解析输出、不判断语言、不决策下一步。一切由 Agent 完成。
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


# =============================================================================
# CommandResult — 命令执行结果
# =============================================================================

class CommandResult(BaseModel):
    """
    单条命令的执行结果。

    沙箱不解析、不判断、不决策。Agent 拿到结果后自行解读。
    """

    exit_code: int
    stdout: str = Field(default="", max_length=50_000)
    stderr: str = Field(default="", max_length=10_000)
    timed_out: bool = False
    duration_ms: int = 0


# =============================================================================
# BaseSandbox
# =============================================================================

class BaseSandbox(ABC):
    """
    沙箱抽象基类。

    子类只需实现 execute() 一个方法。
    """

    @abstractmethod
    def execute(
        self,
        command: str,
        *,
        cwd: str = "/workspace",
        timeout: int = 60,
    ) -> CommandResult:
        """
        执行一条命令，返回结果。

        沙箱的唯一职责。不解析输出、不判断成功失败、不决策下一步。

        Args:
            command: 要执行的 shell 命令
            cwd: 工作目录
            timeout: 超时秒数

        Returns:
            CommandResult — Agent 自行解读
        """
        ...
