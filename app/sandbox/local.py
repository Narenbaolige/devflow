"""
本地沙箱实现（默认模式）。

使用 subprocess 在本机直接执行命令，零额外依赖。
策略与 Claude Code 一致：直接在本机跑命令，使用系统原生 shell。

内置路径校验和结构化日志。
复杂逻辑由调用方拆分为多次 execute() 调用。

启用方式：SANDBOX_MODE=local（默认）
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.sandbox.base import (
    BaseSandbox,
    CommandResult,
    _check_paths,
    _log_execute,
    _setup_logger,
)


class LocalSandbox(BaseSandbox):
    """
    本地沙箱引擎。

    Agent 通过 execute() 自行决定跑什么命令。
    每条命令独立执行，文件系统跨调用持久。
    命令中的可疑路径会被检测并写入 CommandResult.warnings。

    用法：
        sandbox = LocalSandbox()
        r = sandbox.execute("git clone https://... repo")
        r = sandbox.execute("pip install -e .", cwd="repo", timeout=180)
        r = sandbox.execute("python -m pytest -v", cwd="repo")
        sandbox.cleanup()
    """

    def __init__(self, log_dir: str | Path | None = None):
        self._workspace: Path | None = None
        if log_dir:
            _setup_logger(log_dir)

    def execute(
        self,
        command: str,
        *,
        cwd: str = "/workspace",
        timeout: int = 60,
    ) -> CommandResult:
        """
        在本机执行一条 shell 命令。

        使用系统原生 shell。cwd 自动约束到临时工作区内。
        """
        start_time = time.time()

        if self._workspace is None:
            self._workspace = Path(tempfile.mkdtemp(prefix="devflow-"))

        # cwd 始终约束在 workspace 内
        if cwd == "/workspace":
            resolved_cwd = str(self._workspace)
        elif not Path(cwd).is_absolute():
            resolved_cwd = str(self._workspace / cwd)
        else:
            # 绝对路径但不在 workspace 内 → 强制放入 workspace
            if not Path(cwd).resolve().as_posix().startswith(
                self._workspace.resolve().as_posix()
            ):
                resolved_cwd = str(self._workspace / Path(cwd).name)
            else:
                resolved_cwd = cwd

        # 路径校验
        warnings = _check_paths(command, str(self._workspace))

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=resolved_cwd,
                capture_output=True,
                timeout=timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr_out = result.stderr.decode("utf-8", errors="replace")

            cmd_result = CommandResult(
                exit_code=result.returncode,
                stdout=stdout[-50_000:] if len(stdout) > 50_000 else stdout,
                stderr=stderr_out[-10_000:] if len(stderr_out) > 10_000 else stderr_out,
                timed_out=False,
                duration_ms=duration_ms,
                warnings=warnings,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            cmd_result = CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"命令超时 ({timeout}s): {command[:80]}",
                timed_out=True,
                duration_ms=duration_ms,
                warnings=warnings,
            )

        # 结构化日志
        _log_execute(
            command, resolved_cwd, timeout,
            cmd_result.exit_code, cmd_result.duration_ms, cmd_result.timed_out,
            (cmd_result.stdout or cmd_result.stderr)[:120],
            warnings=cmd_result.warnings,
            backend="local",
        )

        return cmd_result

    def cleanup(self) -> None:
        """删除临时工作区。"""
        if self._workspace is None:
            return
        ws = self._workspace
        self._workspace = None
        if not ws.exists():
            return
        for _ in range(3):
            try:
                shutil.rmtree(ws)
                break
            except OSError:
                time.sleep(0.1)

    def __del__(self):
        self.cleanup()
