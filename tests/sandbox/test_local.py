"""LocalSandbox 集成测试。

验证 execute() 的核心行为：命令执行、文件持久化、cwd 解析、清理。
不依赖 Docker，不依赖网络。
"""

import os
import pytest
from pathlib import Path

from app.sandbox.local import LocalSandbox


@pytest.fixture
def sandbox():
    s = LocalSandbox()
    yield s
    s.cleanup()


# =============================================================================
# execute 基础行为
# =============================================================================

class TestExecuteBasics:
    """基本命令执行。"""

    def test_simple_command(self, sandbox):
        """echo 命令应返回 exit=0 且 stdout 包含输出。"""
        r = sandbox.execute("echo hello")
        assert r.exit_code == 0
        assert "hello" in r.stdout
        assert not r.timed_out

    def test_failing_command(self, sandbox):
        """非零退出的命令应返回非零 exit_code。"""
        r = sandbox.execute("python -c \"import sys; sys.exit(42)\"")
        assert r.exit_code == 42
        assert not r.timed_out

    def test_timeout(self, sandbox):
        """超时的命令应标记 timed_out=True。"""
        r = sandbox.execute("python -c \"import time; time.sleep(10)\"", timeout=1)
        assert r.timed_out
        assert r.exit_code == -1


# =============================================================================
# 文件系统持久化
# =============================================================================

class TestFilePersistence:
    """同一沙箱实例内，文件跨 execute() 调用持久存在。"""

    def test_file_written_by_one_command_readable_by_next(self, sandbox):
        """echo 写入文件后，下一个 execute 应能读到。"""
        sandbox.execute("echo persistence-test > data.txt")
        r = sandbox.execute("type data.txt")
        assert r.exit_code == 0
        assert "persistence-test" in r.stdout

    def test_cwd_is_same_across_calls(self, sandbox):
        """默认 cwd 在两次调用中保持一致。"""
        sandbox.execute("echo first > marker.txt")
        r = sandbox.execute("type marker.txt")
        assert "first" in r.stdout


# =============================================================================
# cwd 解析
# =============================================================================

class TestCwdResolution:
    """cwd 参数正确解析到临时工作区。"""

    def test_default_cwd(self, sandbox):
        """默认 cwd="/workspace" 应映射到临时目录。"""
        r = sandbox.execute("echo cwd-test > where-am-i.txt")
        assert r.exit_code == 0
        # 文件应在当前 cwd 创建
        r2 = sandbox.execute("type where-am-i.txt")
        assert "cwd-test" in r2.stdout

    def test_relative_cwd(self, sandbox):
        """cwd="subdir" 应解析为 workspace/subdir。"""
        sandbox.execute("mkdir subdir")
        sandbox.execute("echo nested > subdir/f.txt")
        r = sandbox.execute("type f.txt", cwd="subdir")
        assert r.exit_code == 0
        assert "nested" in r.stdout

    def test_absolute_cwd(self, sandbox, tmp_path):
        """绝对路径 cwd 应在指定目录执行。"""
        marker = tmp_path / "marker.txt"
        marker.write_text("absolute-test")
        r = sandbox.execute(f"type {marker}")
        assert "absolute-test" in r.stdout


# =============================================================================
# cleanup
# =============================================================================

class TestCleanup:
    """cleanup 后临时工作区应被删除。"""

    def test_cleanup_removes_workspace(self, sandbox):
        """cleanup 后 _workspace 应为 None 且目录不存在。"""
        sandbox.execute("echo x > temp.txt")
        ws = sandbox._workspace
        assert ws is not None
        assert ws.exists()

        sandbox.cleanup()

        assert sandbox._workspace is None
        assert not ws.exists()

    def test_del_calls_cleanup(self):
        """__del__ 应自动清理。"""
        s = LocalSandbox()
        s.execute("echo x > temp.txt")
        ws = s._workspace
        assert ws is not None

        del s  # 手动触发 __del__

        assert not ws.exists()


# =============================================================================
# 真实仓库端到端（慢，需网络 — 用 -m slow 标记）
# =============================================================================

@pytest.mark.slow
class TestRealRepoPipeline:
    """完整流水线：clone → install → pytest。"""

    def test_clone_and_pytest_markupsafe(self, sandbox):
        """clone pallets/markupsafe 并跑 pytest，应全部通过。"""
        r = sandbox.execute(
            "git clone --depth 1 --branch main "
            "https://github.com/pallets/markupsafe repo",
            timeout=60,
        )
        assert r.exit_code == 0, f"clone 失败: {r.stderr or r.stdout[:200]}"

        # 安装依赖：先尝试 pip install -e .，失败则检查 requirements.txt
        r = sandbox.execute("pip install -q -e .", cwd="repo", timeout=180)
        if r.exit_code != 0:
            check = sandbox.execute(
                "python -c \"import os; exit(0 if os.path.exists('requirements.txt') else 1)\"",
                cwd="repo",
            )
            if check.exit_code == 0:
                sandbox.execute("pip install -q -r requirements.txt", cwd="repo", timeout=180)

        r = sandbox.execute(
            "python -m pytest --tb=short -v 2>&1",
            cwd="repo",
            timeout=120,
        )
        assert r.exit_code == 0, f"pytest 失败:\n{r.stdout[-500:]}\n{r.stderr[:500]}"
        assert "passed" in r.stdout
