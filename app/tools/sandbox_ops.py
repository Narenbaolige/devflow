"""
沙箱命令执行工具。

封装沙箱的 execute() 接口，提供 sandbox_execute 工具函数。
同一个 task_id 的多次调用复用同一个沙箱实例（文件系统持久）。

Agent 通过此工具自行决定跑什么命令、如何解读结果。
"""

from app.sandbox import BaseSandbox, create_sandbox
from app.tools.file_ops import ToolResult

# =============================================================================
# 沙箱实例注册表 — 按 task_id 复用
# =============================================================================

_sandboxes: dict[str, BaseSandbox] = {}


def get_sandbox(task_id: str = "default") -> BaseSandbox:
    """
    获取或创建 task 专属的沙箱实例。

    同一 task_id 的多次调用返回同一个沙箱，
    保证 git clone → pip install → pytest 在同一个文件系统中执行。
    """
    if task_id not in _sandboxes:
        _sandboxes[task_id] = create_sandbox()
    return _sandboxes[task_id]


def cleanup_sandbox(task_id: str = "default") -> None:
    """清理指定 task 的沙箱（删除临时目录/销毁容器）。"""
    sandbox = _sandboxes.pop(task_id, None)
    if sandbox is not None:
        sandbox.cleanup()


def reset_all() -> None:
    """清理所有沙箱实例。"""
    for sandbox in _sandboxes.values():
        sandbox.cleanup()
    _sandboxes.clear()


# =============================================================================
# sandbox_execute — Agent 可调用的工具函数
# =============================================================================

def sandbox_execute(
    command: str,
    *,
    cwd: str = "/workspace",
    timeout: int = 60,
    task_id: str = "default",
) -> ToolResult:
    """
    在沙箱中执行 shell 命令。

    Agent 自行决定跑什么命令、如何解读结果。
    沙箱不限制语言和工具，Python/Rust/Go/C++/JS 均可。

    同一 task_id 的调用共享文件系统，
    例如 git clone 后后续命令可在 cwd="repo" 下操作克隆的仓库。

    Args:
        command: 要执行的 shell 命令
        cwd: 工作目录，默认 /workspace
        timeout: 超时秒数，默认 60
        task_id: 任务 ID，用于沙箱复用

    Returns:
        ToolResult.data 为命令输出文本（含 stdout + stderr）。
    """
    try:
        sandbox = get_sandbox(task_id)
        result = sandbox.execute(command, cwd=cwd, timeout=timeout)
    except Exception as e:
        return ToolResult(success=False, error=f"沙箱执行异常: {e}")

    output_parts: list[str] = []
    if result.stdout:
        output_parts.append(result.stdout.rstrip())
    if result.stderr:
        output_parts.append(f"[stderr]\n{result.stderr.rstrip()}")
    if result.timed_out:
        output_parts.append(f"[超时] 命令在 {timeout}s 后被终止")

    status = "成功" if result.exit_code == 0 else f"失败 (exit_code={result.exit_code})"
    header = f"[{status}] [{result.duration_ms}ms] $ {command}"

    return ToolResult(
        success=result.exit_code == 0 and not result.timed_out,
        data=header + "\n" + ("\n".join(output_parts) if output_parts else "(无输出)"),
    )
