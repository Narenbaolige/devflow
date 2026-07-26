"""ReviewerAgent 单元测试。"""

from app.agents.reviewer import ReviewerAgent
from contracts.agent_result import AgentRole, ReviewResult
from contracts.state import create_initial_state


class TestReviewerAgent:
    """验证 ReviewerAgent 的接口、Mock 输出、上下文构建。"""

    # ------------------------------------------------------------------
    # 接口契约
    # ------------------------------------------------------------------

    def test_role(self):
        agent = ReviewerAgent()
        assert agent.role == AgentRole.REVIEWER

    def test_output_schema(self):
        agent = ReviewerAgent()
        assert agent.output_schema == ReviewResult

    def test_use_mock_default(self):
        agent = ReviewerAgent()
        assert agent.USE_MOCK is True

    # ------------------------------------------------------------------
    # Mock 输出 — 通过场景（默认）
    # ------------------------------------------------------------------

    def test_mock_result_success(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.success is True
        assert result.agent_role == AgentRole.REVIEWER

    def test_mock_result_default_passed(self):
        """默认 Mock 输出应为通过。"""
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.result["passed"] is True

    def test_mock_result_contains_review_fields(self):
        """Mock 输出应包含 ReviewResult 全部关键字段。"""
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        data = result.result
        for key in ["passed", "risk_level", "issues", "summary"]:
            assert key in data, f"缺少字段: {key}"

    def test_mock_result_risk_level_valid(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.result["risk_level"] in ("low", "medium", "high")

    def test_mock_result_issues_is_list(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert isinstance(result.result["issues"], list)

    def test_mock_result_has_reasoning(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert len(result.reasoning) > 0

    # ------------------------------------------------------------------
    # invoke（Mock 路径）
    # ------------------------------------------------------------------

    def test_invoke_uses_mock(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.invoke(state)
        assert result.success is True
        assert result.agent_role == AgentRole.REVIEWER
        assert result.result["passed"] is True

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    def test_build_context_includes_test_results(self):
        """build_context 应包含沙箱测试结果。"""
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        state["sandbox_results"] = [
            {
                "execution_id": "abc12345",
                "task_id": "t-001",
                "sandbox_type": "test",
                "status": "success",
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 1200,
                "test_summary": {"total": 10, "passed": 10, "failed": 0},
            }
        ]
        ctx = agent.build_context(state)
        assert "abc12345" in ctx
        assert "success" in ctx

    def test_build_context_handles_empty_patches(self):
        """patches 为空时不应崩溃。"""
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        state["patches"] = []
        state["sandbox_results"] = []
        ctx = agent.build_context(state)
        assert isinstance(ctx, str)
        assert len(ctx) > 0  # 即使无数据也应返回有效的上下文字符串

    def test_build_context_nonempty(self):
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="", branch="main", requirement="",
        )
        ctx = agent.build_context(state)
        assert isinstance(ctx, str)

    # ------------------------------------------------------------------
    # 安全规则集成
    # ------------------------------------------------------------------

    def test_system_prompt_includes_security_rules(self):
        """system_prompt 应包含安全检测规则（CWE-89 / CWE-798 / CWE-22）。"""
        agent = ReviewerAgent()
        prompt = agent.system_prompt
        assert "CWE-89" in prompt or "SQL 注入" in prompt
        assert "CWE-798" in prompt or "硬编码密钥" in prompt
        assert "CWE-22" in prompt or "路径遍历" in prompt

    def test_build_context_includes_security_checklist(self):
        """build_context 应包含安全审查要求。"""
        agent = ReviewerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        ctx = agent.build_context(state)
        assert "安全审查" in ctx
        assert "SQL 注入" in ctx
        assert "硬编码密钥" in ctx
        assert "路径遍历" in ctx

    def test_system_prompt_cached_includes_security(self):
        """缓存的 system_prompt 应包含安全规则（只加载一次）。"""
        agent = ReviewerAgent()
        first = agent.system_prompt
        second = agent.system_prompt
        # 缓存：两次访问返回相同对象
        assert first is second
        # 内容包含安全规则
        assert "CWE-89" in first or "SQL 注入" in first
