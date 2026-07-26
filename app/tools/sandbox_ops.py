"""
沙箱命令执行工具。

封装沙箱的 execute() 接口，提供 sandbox_execute 工具函数。
"""

from app.sandbox import create_sandbox
from app.tools.file_ops import ToolResult


def sandbox_execute(
    command: str,
    *,
    cwd: str = "/workspace",
    timeout: int = 60,
) -> ToolResult:
    """
    在沙箱中执行 shell 命令。

    Agent 自行决定跑什么命令、如何解读结果。
    沙箱不限制语言和工具，Python/Rust/Go/C++/JS 均可。

    Args:
        command: 要执行的 shell 命令
        cwd: 工作目录，默认 /workspace
        timeout: 超时秒数，默认 60

    Returns:
        ToolResult.data 为命令输出文本（包含 stdout + stderr 摘要）。
    """
    try:
        sandbox = create_sandbox()
        result = sandbox.execute(command, cwd=cwd, timeout=timeout)
    except Exception as e:
        return ToolResult(success=False, error=f"沙箱执行异常: {e}")

    # 构建人类可读的输出
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
