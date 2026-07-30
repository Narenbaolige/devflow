"""
工具的实际执行函数。

Agent 通过 tool-calling 机制调用这些函数在沙箱中执行实际操作。
每个函数接收 task_id 参数以使用正确的沙箱实例。
"""

from app.tools.sandbox_ops import sandbox_execute as _exec


def tool_read_file(file_path: str, task_id: str = "default") -> str:
    """读取沙箱中指定文件的内容。"""
    if not file_path:
        return "[错误] file_path 不能为空"
    # Both `repo/foo.py` (from prompts) and `foo.py` are accepted.
    if file_path.startswith("repo/"):
        file_path = file_path.removeprefix("repo/")
    # 路径遍历保护：拒绝包含 .. 或绝对路径的路径
    if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
        return f"[安全拒绝] 不允许的路径: {file_path}"
    # 检测 Windows 盘符 (如 C:/)
    if len(file_path) >= 2 and file_path[1] == ":":
        return f"[安全拒绝] 不允许的路径: {file_path}"
    r = _exec(f"cat repo/{file_path}", timeout=15, task_id=task_id)
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
    import shlex
    safe_pattern = shlex.quote(pattern)
    safe_path = shlex.quote(path)
    r = _exec(
        f"grep -rn {safe_pattern} {safe_path} 2>&1 | head -50",
        timeout=30, task_id=task_id,
    )
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


def tool_glob(pattern: str, task_id: str = "default") -> str:
    """按 glob 模式匹配沙箱仓库中的文件路径。"""
    import shlex
    safe_pattern = shlex.quote(pattern)
    # Use python to perform glob matching (more portable than bash glob)
    script = (
        f"import glob, os; "
        f"os.chdir('repo'); "
        f"matches = glob.glob({safe_pattern}, recursive=True); "
        f"print('\\n'.join(matches) if matches else '[无匹配]')"
    )
    r = _exec(f"python -c {shlex.quote(script)}", timeout=15, task_id=task_id)
    return r.data.strip() if r.success else f"[glob 失败] {r.error}"


def tool_write_file(file_path: str, content: str, task_id: str = "default") -> str:
    """在沙箱仓库中写入或覆盖文件。"""
    import shlex
    safe_path = shlex.quote(f"repo/{file_path}")
    # Write content via Python to handle multiline/special chars safely
    safe_content = shlex.quote(content)
    r = _exec(
        f"python -c {shlex.quote(f'import sys; sys.stdout.write({safe_content})')} > {safe_path}",
        timeout=15, task_id=task_id,
    )
    if r.success:
        return f"[写入成功] {file_path}"
    return f"[写入失败] {r.error}"


def tool_edit_file(
    file_path: str, old_string: str, new_string: str, task_id: str = "default"
) -> str:
    """精确替换沙箱仓库文件中的指定字符串（old_string → new_string）。"""
    import json as _json
    import shlex
    safe_path = shlex.quote(f"repo/{file_path}")
    payload = _json.dumps({"old": old_string, "new": new_string})
    safe_payload = shlex.quote(payload)
    script = shlex.quote(
        f"import json, sys; "
        f"d = json.loads({safe_payload}); "
        f"with open({safe_path}, 'r', encoding='utf-8') as f: c = f.read(); "
        f"count = c.count(d['old']); "
        f"if count == 0: sys.exit(1); "
        f"c = c.replace(d['old'], d['new'], 1); "
        f"with open({safe_path}, 'w', encoding='utf-8') as f: f.write(c); "
        f"print(f'[替换成功] 1/{{count}} 处匹配')"
    )
    r = _exec(f"python -c {script}", timeout=15, task_id=task_id)
    if r.success:
        return f"[替换成功] {file_path}"
    return f"[替换失败] old_string 在文件中未找到: {file_path}"


# 工具名 → 执行函数映射
TOOL_IMPL_MAP = {
    "read_file": tool_read_file,
    "list_dir": tool_list_dir,
    "grep": tool_grep,
    "glob": tool_glob,
    "sandbox_execute": tool_sandbox_execute,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    # 向后兼容别名
    "execute_test": tool_pytest,
    "execute_command": tool_sandbox_execute,
}
