"""
文件操作工具实现。

提供 read_file / write_file / edit_file / list_dir / glob 五个工具的可调用函数。
每个函数独立、无副作用（除 write_file/edit_file 外）、可直接在 Agent 中调用。
"""

from pathlib import Path

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具调用统一返回"""

    success: bool
    data: str | list[str] | None = Field(default=None, description="成功时的返回数据")
    error: str | None = Field(default=None, description="失败时的错误信息")


# =============================================================================
# 路径安全校验
# =============================================================================

_WORKSPACE_ROOT: Path | None = None


def set_workspace(root: str | Path | None) -> None:
    """设置沙箱工作区根目录，所有文件操作被限制在此范围内。传入 None 重置。"""
    global _WORKSPACE_ROOT
    if root is None:
        _WORKSPACE_ROOT = None
    else:
        _WORKSPACE_ROOT = Path(root).resolve()


def get_workspace() -> Path:
    """获取当前工作区根目录（未设置时默认当前目录）。"""
    return _WORKSPACE_ROOT or Path.cwd()


def _resolve(path: str | Path) -> Path:
    """
    将相对路径解析为工作区下的绝对路径，并校验不逃逸。

    Raises:
        ValueError: 路径超出工作区范围
    """
    root = get_workspace()
    resolved = (root / path).resolve()
    # 允许访问工作区内的路径
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"路径超出工作区范围: {path}")
    return resolved


# =============================================================================
# 文件读取
# =============================================================================

def read_file(path: str, *, encoding: str = "utf-8", max_bytes: int = 100_000) -> ToolResult:
    """
    读取指定文件的完整内容。

    Args:
        path: 相对于工作区根目录的文件路径
        encoding: 文件编码
        max_bytes: 最大读取字节数（防止 OOM）
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return ToolResult(success=False, error=str(e))

    try:
        if not target.is_file():
            return ToolResult(success=False, error=f"文件不存在: {path}")
        content = target.read_bytes()
        if len(content) > max_bytes:
            return ToolResult(
                success=False,
                error=f"文件过大 ({len(content)} bytes)，超过限制 ({max_bytes} bytes)",
            )
        return ToolResult(success=True, data=content.decode(encoding))
    except UnicodeDecodeError:
        return ToolResult(success=False, error=f"无法以 {encoding} 解码文件（可能是二进制文件）")
    except PermissionError:
        return ToolResult(success=False, error=f"没有读取权限: {path}")
    except OSError as e:
        return ToolResult(success=False, error=f"读取文件失败: {e}")


# =============================================================================
# 文件写入
# =============================================================================

def write_file(path: str, content: str, *, encoding: str = "utf-8") -> ToolResult:
    """
    在沙箱工作区中写入或覆盖文件。自动创建不存在的父目录。

    Args:
        path: 相对于工作区根目录的文件路径
        content: 文件内容
        encoding: 文件编码
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return ToolResult(success=False, error=str(e))

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return ToolResult(success=True, data=f"写入成功: {path} ({len(content)} 字符)")
    except PermissionError:
        return ToolResult(success=False, error=f"没有写入权限: {path}")
    except OSError as e:
        return ToolResult(success=False, error=f"写入文件失败: {e}")


# =============================================================================
# 文件编辑（精确替换）
# =============================================================================

def edit_file(
    path: str, old_string: str, new_string: str, *, encoding: str = "utf-8"
) -> ToolResult:
    """
    精确替换文件中的指定字符串（old_string → new_string）。

    要求 old_string 在文件中恰好出现一次；零次或多次均报错。

    Args:
        path: 相对于工作区根目录的文件路径
        old_string: 要被替换的原字符串（需精确匹配，包括缩进和空白）
        new_string: 替换后的新字符串
        encoding: 文件编码
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return ToolResult(success=False, error=str(e))

    try:
        if not target.is_file():
            return ToolResult(success=False, error=f"文件不存在: {path}")
        original = target.read_text(encoding=encoding)
    except (PermissionError, OSError) as e:
        return ToolResult(success=False, error=f"读取文件失败: {e}")

    count = original.count(old_string)
    if count == 0:
        return ToolResult(success=False, error="未找到目标字符串（0 次匹配）")
    if count > 1:
        return ToolResult(
            success=False,
            error=(
                f"目标字符串出现 {count} 次（要求恰好 1 次），"
                "请提供更多上下文字符"
            ),
        )

    modified = original.replace(old_string, new_string, 1)
    try:
        target.write_text(modified, encoding=encoding)
        return ToolResult(success=True, data=f"替换成功: {path}，{count} 处替换")
    except (PermissionError, OSError) as e:
        return ToolResult(success=False, error=f"写入文件失败: {e}")


# =============================================================================
# 目录列表
# =============================================================================

def list_dir(path: str = ".") -> ToolResult:
    """
    列出目录下的文件和子目录（不含递归）。

    Args:
        path: 相对于工作区根目录的目录路径，默认 "."
    """
    try:
        target = _resolve(path)
    except ValueError as e:
        return ToolResult(success=False, error=str(e))

    try:
        if not target.is_dir():
            return ToolResult(success=False, error=f"不是目录: {path}")
        entries: list[str] = []
        for entry in sorted(target.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(entry.name + suffix)
        return ToolResult(success=True, data=entries)
    except PermissionError:
        return ToolResult(success=False, error=f"没有读取权限: {path}")
    except OSError as e:
        return ToolResult(success=False, error=f"列出目录失败: {e}")


# =============================================================================
# Glob 模式匹配
# =============================================================================

def glob(pattern: str) -> ToolResult:
    """
    按 glob 模式匹配工作区内的文件路径。

    支持 ** 递归匹配。只返回文件（不返回目录）。

    Args:
        pattern: glob 模式，如 "src/**/*.py"、"tests/*.py"
    """
    root = get_workspace()
    try:
        matches = sorted(
            p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file()
        )
        return ToolResult(success=True, data=matches)
    except OSError as e:
        return ToolResult(success=False, error=f"glob 匹配失败: {e}")
