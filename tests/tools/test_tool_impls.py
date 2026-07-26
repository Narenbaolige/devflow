"""
工具实现函数的单元测试。

覆盖 file_ops / search / sandbox_ops 的所有工具函数。
使用临时目录隔离，不依赖真实仓库或 Docker。
"""

import tempfile
from pathlib import Path

import pytest

from app.tools.file_ops import (
    ToolResult,
    edit_file,
    glob,
    list_dir,
    read_file,
    set_workspace,
    write_file,
)
from app.tools.search import grep


@pytest.fixture
def workspace():
    """创建临时工作区并设置路径限制。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # 创建测试文件结构
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text(
            "def hello():\n    return 'Hello, World!'\n\ndef add(a, b):\n    return a + b\n"
        )
        (root / "src" / "utils.py").write_text(
            "import os\n\ndef get_env(key):\n    return os.getenv(key)\n"
        )
        (root / "tests").mkdir()
        (root / "tests" / "test_main.py").write_text(
            "from src.main import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        )
        (root / "README.md").write_text("# Test Project\n")
        set_workspace(root)
        yield root
    set_workspace(None)


# =============================================================================
# read_file
# =============================================================================

class TestReadFile:
    def test_read_existing_file(self, workspace):
        result = read_file("src/main.py")
        assert result.success
        assert "def hello()" in result.data

    def test_read_nonexistent_file(self, workspace):
        result = read_file("nonexistent.py")
        assert not result.success
        assert "不存在" in result.error

    def test_read_outside_workspace(self, workspace):
        result = read_file("../etc/passwd")
        assert not result.success
        assert "超出工作区" in result.error

    def test_read_binary_file(self, workspace):
        (workspace / "data.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
        result = read_file("data.bin")
        assert not result.success
        # 可能因无法解码失败（二进制内容）
        assert not result.success

    def test_read_with_max_bytes(self, workspace):
        (workspace / "large.txt").write_text("x" * 200_000)
        result = read_file("large.txt")
        assert not result.success
        assert "过大" in result.error


# =============================================================================
# write_file
# =============================================================================

class TestWriteFile:
    def test_write_new_file(self, workspace):
        result = write_file("new.py", "print('hello')")
        assert result.success
        assert (workspace / "new.py").read_text() == "print('hello')"

    def test_overwrite_existing_file(self, workspace):
        result = write_file("src/main.py", "# overwritten")
        assert result.success
        assert (workspace / "src" / "main.py").read_text() == "# overwritten"

    def test_write_creates_parent_dirs(self, workspace):
        result = write_file("deep/nested/file.txt", "content")
        assert result.success
        assert (workspace / "deep" / "nested" / "file.txt").exists()

    def test_write_outside_workspace(self, workspace):
        result = write_file("../outside.txt", "content")
        assert not result.success
        assert "超出工作区" in result.error


# =============================================================================
# edit_file
# =============================================================================

class TestEditFile:
    def test_edit_single_occurrence(self, workspace):
        result = edit_file("src/main.py", "def hello():", "def greet():")
        assert result.success
        content = (workspace / "src" / "main.py").read_text()
        assert "def greet():" in content
        assert "def hello():" not in content

    def test_edit_nonexistent_string(self, workspace):
        result = edit_file("src/main.py", "this does not exist", "x")
        assert not result.success
        assert "未找到" in result.error

    def test_edit_multiple_occurrences(self, workspace):
        (workspace / "dup.py").write_text("x = 1\nx = 1\n")
        result = edit_file("dup.py", "x = 1", "y = 2")
        assert not result.success
        assert "2 次" in result.error

    def test_edit_nonexistent_file(self, workspace):
        result = edit_file("ghost.py", "a", "b")
        assert not result.success
        assert "不存在" in result.error


# =============================================================================
# list_dir
# =============================================================================

class TestListDir:
    def test_list_root(self, workspace):
        result = list_dir(".")
        assert result.success
        names = result.data
        assert "src/" in names
        assert "tests/" in names
        assert "README.md" in names

    def test_list_subdir(self, workspace):
        result = list_dir("src")
        assert result.success
        assert "main.py" in result.data
        assert "utils.py" in result.data

    def test_list_not_directory(self, workspace):
        result = list_dir("README.md")
        assert not result.success
        assert "不是目录" in result.error

    def test_list_nonexistent(self, workspace):
        result = list_dir("nonexistent")
        assert not result.success


# =============================================================================
# glob
# =============================================================================

class TestGlob:
    def test_glob_py_files(self, workspace):
        result = glob("src/*.py")
        assert result.success
        paths = set(result.data)
        assert "src/main.py" in paths
        assert "src/utils.py" in paths

    def test_glob_recursive(self, workspace):
        result = glob("**/*.py")
        assert result.success
        assert len(result.data) >= 3  # main.py, utils.py, test_main.py

    def test_glob_no_match(self, workspace):
        result = glob("*.rs")
        assert result.success
        assert result.data == []

    def test_glob_md_only(self, workspace):
        result = glob("*.md")
        assert result.success
        assert "README.md" in result.data


# =============================================================================
# grep
# =============================================================================

class TestGrep:
    def test_grep_simple_pattern(self, workspace):
        result = grep("def ", "src")
        assert result.success
        lines = result.data
        assert any("main.py" in line and "def hello" in line for line in lines)
        assert any("main.py" in line and "def add" in line for line in lines)

    def test_grep_no_match(self, workspace):
        result = grep("NO_SUCH_STRING_999", ".")
        assert result.success
        assert result.data == []

    def test_grep_invalid_regex(self, workspace):
        result = grep("[invalid", ".")
        assert not result.success
        assert "无效的正则" in result.error

    def test_grep_specific_file(self, workspace):
        result = grep("import", "src/utils.py")
        assert result.success
        assert len(result.data) == 1
        assert "utils.py" in result.data[0]
        assert "import os" in result.data[0]


# =============================================================================
# ToolResult model
# =============================================================================

class TestToolResult:
    def test_success_result(self):
        r = ToolResult(success=True, data="hello")
        assert r.success
        assert r.data == "hello"
        assert r.error is None

    def test_failure_result(self):
        r = ToolResult(success=False, error="something went wrong")
        assert not r.success
        assert r.data is None
        assert "wrong" in r.error
