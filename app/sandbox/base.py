"""
沙箱抽象基类 — 接口契约。

设计原则：沙箱是工具，Agent 是大脑。

沙箱只做一件事：execute(command) → CommandResult。
不解析输出、不判断语言、不决策下一步。一切由 Agent 完成。
"""

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field

# =============================================================================
# 结构化日志
# =============================================================================

_sandbox_logger = logging.getLogger("devflow.sandbox")


def _setup_logger(log_dir: str | Path | None = None) -> None:
    """初始化沙箱日志：控制台 + 可选 JSON 文件。"""
    if _sandbox_logger.handlers:
        return

    _sandbox_logger.setLevel(logging.DEBUG)

    # 控制台：简洁
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    _sandbox_logger.addHandler(ch)

    # JSON 文件：完整
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "sandbox.jsonl", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(message)s"))
        _sandbox_logger.addHandler(fh)


def _log_execute(
    command: str,
    cwd: str,
    timeout: int,
    exit_code: int,
    duration_ms: int,
    timed_out: bool,
    stdout_preview: str,
    warnings: list[str] | None = None,
    *,
    backend: str = "local",
    container_id: str = "",
) -> None:
    """记录一条 execute() 调用到结构化日志。"""
    record = {
        "timestamp": time.time(),
        "backend": backend,
        "command": command[:200],
        "cwd": cwd,
        "timeout": timeout,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "stdout_preview": stdout_preview[:120],
        "warnings": warnings or [],
    }
    if container_id:
        record["container_id"] = container_id

    # JSON 行写入文件日志
    _sandbox_logger.debug(json.dumps(record, ensure_ascii=False))

    # 控制台一行摘要
    status = "TIMEOUT" if timed_out else f"exit={exit_code}"
    _sandbox_logger.info(
        "[%s] [%s] %dms $ %s",
        backend, status, duration_ms, command[:100],
    )


# =============================================================================
# 路径校验
# =============================================================================

# 绝对路径中不应出现的敏感目录（跨平台）
_SENSITIVE_ROOTS = [
    "/etc/", "/root/", "/var/log/", "/proc/", "/sys/", "/dev/",
    "C:\\Windows", "C:\\WINDOWS", "C:\\windows",
    "/System/", "/Library/", "/Applications/",
    "~/.ssh", "~/.aws", "~/.config",
]


def _check_paths(command: str, workspace: str) -> list[str]:
    """扫描命令字符串中的可疑绝对路径。返回警告列表，不阻塞执行。"""
    warnings: list[str] = []

    # 检查常见敏感绝对路径
    for root in _SENSITIVE_ROOTS:
        if root.lower() in command.lower():
            warnings.append(f"命令引用了敏感路径: {root}")

    # 检查 Windows 盘符绝对路径（不在 workspace 内）
    # [^\\/] 确保不匹配 https:// 等 URL
    win_paths = re.findall(r'([A-Za-z]:[\\/][^\\/\s;|&][^\s;|&]*)', command)
    for p in win_paths:
        if not Path(p).resolve().as_posix().startswith(Path(workspace).resolve().as_posix()):
            warnings.append(f"命令引用了工作区外的 Windows 路径: {p}")

    # 检查 Linux 绝对路径（不在 workspace 内）
    unix_paths = re.findall(r'(/[^\s;|&]{2,})', command)
    for p in unix_paths:
        # 跳过 URL（//）和 UNC 路径，避免 Windows 上 Path.resolve() 挂起
        if p.startswith("//"):
            continue
        if p.startswith("/workspace"):
            continue
        if p.startswith("/tmp"):
            continue
        if p.startswith("/dev/"):
            continue
        try:
            if not Path(p).resolve().as_posix().startswith(Path(workspace).resolve().as_posix()):
                warnings.append(f"命令引用了工作区外的绝对路径: {p}")
        except Exception:
            pass

    return warnings


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
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# BaseSandbox
# =============================================================================

class BaseSandbox(ABC):
    """
    沙箱抽象基类。

    子类需实现 execute() 和 workspace 属性。
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
