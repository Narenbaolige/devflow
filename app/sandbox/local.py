"""
本地沙箱实现（默认模式）。

使用 subprocess 在本机直接执行命令，零额外依赖。
策略与 Claude Code 一致：直接在本机跑命令，沙箱是工具不是决策者。

实现 execute(command, cwd, timeout) → CommandResult。
在系统临时目录中管理文件，首次调用自动创建，cleanup() 或 __del__ 时删除。

启用方式：SANDBOX_MODE=local（默认）
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.sandbox.base import BaseSandbox, CommandResult


class LocalSandbox(BaseSandbox):
    """
    本地沙箱引擎。

    Agent 通过 execute() 自行决定跑什么命令。

    用法：
        sandbox = LocalSandbox()
        r = sandbox.execute("git clone https://... repo")
        r = sandbox.execute("pip install -e .", cwd="repo", timeout=180)
        r = sandbox.execute("python -m pytest -v", cwd="repo")
        sandbox.cleanup()
    """

    def __init__(self):
        self._workspace: Path | None = None

    def execute(
        self,
        command: str,
        *,
        cwd: str = "/workspace",
        timeout: int = 60,
    ) -> CommandResult:
        """
        在本机执行一条 shell 命令。

        cwd 解析规则：
          - "/workspace" → 自动创建的临时目录
          - "repo" 等相对路径 → 基于临时目录解析
          - 绝对路径 → 直接使用
        """
        start_time = time.time()

        if self._workspace is None:
            self._workspace = Path(tempfile.mkdtemp(prefix="devflow-"))

        if cwd == "/workspace":
            resolved_cwd = str(self._workspace)
        elif not Path(cwd).is_absolute():
            resolved_cwd = str(self._workspace / cwd)
        else:
            resolved_cwd = cwd

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=resolved_cwd,
                capture_output=True,
                timeout=timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return CommandResult(
                exit_code=result.returncode,
                stdout=result.stdout.decode("utf-8", errors="replace"),
                stderr=result.stderr.decode("utf-8", errors="replace"),
                timed_out=False,
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"命令超时 ({timeout}s): {command[:80]}",
                timed_out=True,
                duration_ms=duration_ms,
            )

    def cleanup(self) -> None:
        """删除临时工作区。"""
        if self._workspace and self._workspace.exists():
            shutil.rmtree(self._workspace, ignore_errors=True)
            self._workspace = None

    def __del__(self):
        self.cleanup()
