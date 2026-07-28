"""
工具的实际执行函数。

Agent 通过 tool-calling 机制调用这些函数在沙箱中执行实际操作。
每个函数接收 task_id 参数以使用正确的沙箱实例。
"""

from app.tools.sandbox_ops import sandbox_execute as _exec


def tool_read_file(file_path: str, task_id: str = "default") -> str:
    """读取沙箱中指定文件的内容。"""
    if not file_path or "/" in file_path.lstrip("/"):
        pass  # Keep path as-is (relative to repo)
    r = _exec(f"cat {file_path}", cwd="repo", timeout=15, task_id=task_id)
    return r.data if r.success else f"[读取失败] {r.error}"


def tool_list_dir(path: str = ".", task_id: str = "default") -> str:
    """列出沙箱工作目录中的文件和子目录。"""
    target = f"repo/{path}" if path != "." and not path.startswith("repo/") else path
    if path == ".":
        target = "repo"
    r = _exec(f"ls -la {target}", timeout=15, task_id=task_id)
    return r.data if r.success else f"[列出失败] {r.error}"


def tool_grep(pattern: str, path: str = "repo", task_id: str = "default") -> str:
    """在代码仓库中搜索匹配正则模式的文件和行。"""
    # Sanitize: wrap pattern in quotes to avoid shell injection
    safe_pattern = pattern.replace("'", "'\"'\"'")
    r = _exec(f"grep -rn '{safe_pattern}' {path} 2>&1 | head -50", timeout=30, task_id=task_id)
    return r.data if r.success else f"[搜索失败或无匹配] {r.error or r.data}"


def tool_sandbox_execute(
    command: str,
    cwd: str = "repo",
    timeout: int = 60,
    task_id: str = "default",
) -> str:
    """在沙箱中执行 shell 命令并返回输出。
    Agent 自行决定跑什么命令、如何解读结果。"""
    r = _exec(command, cwd=cwd, timeout=timeout, task_id=task_id)
    return r.data if r.success else f"[命令失败 (exit={r.data})]"


def tool_pytest(
    test_path: str = "",
    cwd: str = "repo",
    task_id: str = "default",
) -> str:
    """在沙箱中运行 pytest 并返回测试结果摘要。"""
    cmd = f"python -m pytest --tb=short -v {test_path} 2>&1 | tail -50"
    r = _exec(cmd, cwd=cwd, timeout=300, task_id=task_id)
    return r.data if r.success else f"[pytest 失败] {r.error or r.data}"


# 工具名 → 执行函数映射
TOOL_IMPL_MAP = {
    "read_file": tool_read_file,
    "list_dir": tool_list_dir,
    "grep": tool_grep,
    "sandbox_execute": tool_sandbox_execute,
}
