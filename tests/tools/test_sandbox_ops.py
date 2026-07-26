"""sandbox_ops 工具封装集成测试。

验证沙箱注册表（复用/隔离/清理）和 sandbox_execute 工具函数。
不依赖 Docker，不依赖网络。
"""

import pytest

from app.tools.sandbox_ops import (
    cleanup_sandbox,
    get_sandbox,
    reset_all,
    sandbox_execute,
)


@pytest.fixture(autouse=True)
def _reset():
    """每个测试前后清空注册表，确保隔离。"""
    reset_all()
    yield
    reset_all()


# =============================================================================
# 注册表
# =============================================================================

class TestRegistry:
    """沙箱实例注册表：复用、隔离、清理。"""

    def test_same_task_returns_same_instance(self):
        """同一 task_id 多次调用返回同一个沙箱实例。"""
        s1 = get_sandbox("task-001")
        s2 = get_sandbox("task-001")
        assert s1 is s2

    def test_different_task_returns_different_instance(self):
        """不同 task_id 返回不同沙箱实例。"""
        s1 = get_sandbox("task-001")
        s2 = get_sandbox("task-002")
        assert s1 is not s2

    def test_default_task_id(self):
        """未指定 task_id 时使用 "default"。"""
        s = get_sandbox()
        assert s is get_sandbox("default")

    def test_cleanup_removes_and_new_instance_created(self):
        """cleanup 后再次获取应返回新实例。"""
        s1 = get_sandbox("task-001")
        cleanup_sandbox("task-001")
        s2 = get_sandbox("task-001")
        assert s1 is not s2

    def test_cleanup_nonexistent_does_not_raise(self):
        """清理不存在的 task_id 不抛异常。"""
        cleanup_sandbox("nonexistent")  # 不应 raise

    def test_reset_all_clears_everything(self):
        """reset_all 应清理所有已注册的沙箱。"""
        get_sandbox("a")
        get_sandbox("b")
        reset_all()
        # 清理后重新获取应为新实例
        s1 = get_sandbox("a")
        s2 = get_sandbox("b")
        assert s1 is not s2  # 不同 task
        cleanup_sandbox("a")
        cleanup_sandbox("b")


class TestFilePersistenceAcrossCalls:
    """同一 task 的多次 sandbox_execute 共享文件系统。"""

    def test_write_then_read(self):
        """先写文件再读文件，文件应持久存在。"""
        r1 = sandbox_execute("echo shared-data > shared.txt", task_id="persist-test")
        assert r1.success, f"写文件失败: {r1.error}"

        r2 = sandbox_execute("type shared.txt", task_id="persist-test")
        assert r2.success
        assert "shared-data" in (r2.data or "")

    def test_different_tasks_isolated(self):
        """不同 task 的文件系统应隔离。"""
        sandbox_execute("echo task-a-data > a.txt", task_id="task-a")
        r = sandbox_execute("type a.txt 2>&1", task_id="task-b")
        # task-b 不应看到 task-a 的文件（type 返回非零）
        assert not r.success or "task-a-data" not in (r.data or "")


# =============================================================================
# 工具函数
# =============================================================================

class TestSandboxExecute:
    """sandbox_execute 工具函数的行为。"""

    def test_success_command(self):
        """成功的命令返回 ToolResult(success=True)。"""
        r = sandbox_execute("echo ok", task_id="tool-test")
        assert r.success
        assert "ok" in (r.data or "")

    def test_failing_command(self):
        """失败的命令返回 ToolResult(success=False)。"""
        r = sandbox_execute("exit 1", task_id="tool-test")
        assert not r.success
        assert "失败" in (r.data or "")

    def test_timeout(self):
        """超时命令返回 success=False。"""
        r = sandbox_execute("python -c \"import time; time.sleep(10)\"", timeout=1, task_id="tool-test")
        assert not r.success
        assert "超时" in (r.data or "")

    def test_cwd_parameter(self):
        """cwd 参数应生效。"""
        sandbox_execute("mkdir sub", task_id="tool-test")
        sandbox_execute("echo nested > f.txt", cwd="sub", task_id="tool-test")
        r = sandbox_execute("type f.txt", cwd="sub", task_id="tool-test")
        assert r.success
        assert "nested" in (r.data or "")

    def test_output_contains_command_info(self):
        """输出应包含命令文本和耗时。"""
        r = sandbox_execute("echo test-output", task_id="tool-test")
        assert "$ echo test-output" in (r.data or "")
        assert "ms" in (r.data or "")
