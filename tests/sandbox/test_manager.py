"""沙箱管理测试。"""

from contracts.sandbox_result import SandboxResult, TestFailure, TestSummary


class TestSandboxResultContracts:
    """验证 SandboxResult 契约的正确性。"""

    def test_success_result(self):
        """测试全部通过的结果。"""
        result = SandboxResult(
            execution_id="exec-001",
            task_id="task-001",
            sandbox_type="test",
            status="success",
            exit_code=0,
            timed_out=False,
            duration_ms=3812,
            test_summary=TestSummary(total=42, passed=42, failed=0),
            started_at="2026-07-22T10:00:00",
            finished_at="2026-07-22T10:00:03",
        )
        assert result.status == "success"
        assert result.test_summary is not None
        assert result.test_summary.failed == 0

    def test_failure_result_with_test_details(self):
        """测试失败的结果应包含详细的失败信息。"""
        result = SandboxResult(
            execution_id="exec-002",
            task_id="task-002",
            sandbox_type="test",
            status="failure",
            exit_code=1,
            timed_out=False,
            duration_ms=5200,
            test_summary=TestSummary(total=42, passed=40, failed=2),
            test_failures=[
                TestFailure(
                    test_name="test_edge_case",
                    test_file="tests/test_utils.py",
                    failure_type="assertion",
                    message="AssertionError: expected 5, got 6",
                    traceback="...",
                    is_new_failure=True,
                ),
            ],
            started_at="2026-07-22T11:00:00",
            finished_at="2026-07-22T11:00:05",
        )
        assert result.status == "failure"
        assert len(result.test_failures) == 1
        assert result.test_failures[0].is_new_failure

    def test_timeout_result(self):
        """超时结果。"""
        result = SandboxResult(
            execution_id="exec-003",
            task_id="task-003",
            sandbox_type="test",
            status="timeout",
            exit_code=-1,
            timed_out=True,
            duration_ms=300_000,
        )
        assert result.timed_out
        assert result.status == "timeout"

    def test_stdout_truncation(self):
        """stdout 超过 100000 字符时应由调用方截断后传入。"""
        # Pydantic max_length 在创建时校验，超过会抛 ValidationError
        # 实际使用中，SandboxManager._exec_command 会在传入前截断
        import pytest as pt
        from pydantic import ValidationError

        long_output = "x" * 200_000
        with pt.raises(ValidationError):
            SandboxResult(
                execution_id="exec-004",
                task_id="task-004",
                sandbox_type="test",
                status="success",
                exit_code=0,
                timed_out=False,
                duration_ms=1000,
                stdout=long_output,
            )
