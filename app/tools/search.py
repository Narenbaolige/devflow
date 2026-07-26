"""
代码搜索工具实现。

提供 grep 工具：在代码仓库中搜索正则模式，返回匹配的文件和行。
"""

import re
from pathlib import Path

from app.tools.file_ops import ToolResult, _resolve


def grep(
    pattern: str,
    path: str = ".",
    *,
    max_matches: int = 200,
    max_file_size: int = 500_000,
) -> ToolResult:
    """
    在代码仓库中搜索正则模式，返回匹配的文件路径和行内容。

    递归搜索目录。二进制文件和超大文件自动跳过。

    Args:
        pattern: 正则表达式（Python re 语法）
        path: 搜索起始路径（相对于工作区根目录），默认 "." 搜索整个工作区
        max_matches: 最大返回匹配数（防止结果爆炸）
        max_file_size: 跳过大文件（字节）

    Returns:
        ToolResult.data 为 list[str]，每项格式: "file_path:line_num: 内容"
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return ToolResult(success=False, error=str(e))

    # 编译正则
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return ToolResult(success=False, error=f"无效的正则表达式: {e}")

    if not target.exists():
        return ToolResult(success=False, error=f"路径不存在: {path}")

    # 收集要搜索的文件
    if target.is_file():
        files = [target]
    else:
        files = [p for p in target.rglob("*") if p.is_file()]

    results: list[str] = []
    for filepath in files:
        if len(results) >= max_matches:
            break

        # 跳过二进制文件和超大文件
        try:
            fsize = filepath.stat().st_size
        except OSError:
            continue
        if fsize > max_file_size:
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        for lineno, line in enumerate(content.splitlines(), 1):
            if regex.search(line):
                rel_path = str(filepath.relative_to(get_workspace()))
                results.append(f"{rel_path}:{lineno}: {line.rstrip()}")
                if len(results) >= max_matches:
                    break

    return ToolResult(success=True, data=results)


def get_workspace() -> Path:
    """获取当前工作区根目录。"""
    from app.tools.file_ops import get_workspace as _gw
    return _gw()
