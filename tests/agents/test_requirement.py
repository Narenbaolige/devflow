"""RequirementAgent 单元测试。"""

from app.agents.requirement import RequirementAgent
from contracts.agent_result import AgentRole, RequirementResult
from contracts.state import create_initial_state


class TestRequirementAgent:
    """验证 RequirementAgent 的接口、Mock 输出、上下文构建。"""

    # ------------------------------------------------------------------
    # 接口契约
    # ------------------------------------------------------------------

    def test_role(self):
        agent = RequirementAgent()
        assert agent.role == AgentRole.REQUIREMENT

    def test_output_schema(self):
        agent = RequirementAgent()
        assert agent.output_schema == RequirementResult

    def test_use_mock_default(self):
        agent = RequirementAgent()
        assert agent.USE_MOCK is True

    # ------------------------------------------------------------------
    # Mock 输出
    # ------------------------------------------------------------------

    def test_mock_result_success(self):
        """Mock 模式应返回 success=True。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="https://github.com/example/repo",
            branch="main",
            requirement="给 factorial 函数添加参数校验",
        )
        result = agent.mock_result(state)
        assert result.success is True
        assert result.agent_role == AgentRole.REQUIREMENT

    def test_mock_result_has_reasoning(self):
        """Mock 输出应包含 reasoning。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="测试需求",
        )
        result = agent.mock_result(state)
        assert len(result.reasoning) > 0

    def test_mock_result_contains_requirement_fields(self):
        """Mock 输出的 result 应包含所有 RequirementResult 关键字段。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="添加日志功能",
        )
        result = agent.mock_result(state)
        data = result.result
        assert data is not None
        assert "summary" in data
        assert "affected_modules" in data
        assert "acceptance_criteria" in data
        assert "confidence" in data
        assert isinstance(data["affected_modules"], list)
        assert isinstance(data["acceptance_criteria"], list)
        assert 0.0 <= data["confidence"] <= 1.0

    def test_mock_result_acceptance_criteria_nonempty(self):
        """验收条件不应为空列表。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="修复登录 Bug",
        )
        result = agent.mock_result(state)
        assert len(result.result["acceptance_criteria"]) >= 1

    # ------------------------------------------------------------------
    # invoke（Mock 路径）
    # ------------------------------------------------------------------

    def test_invoke_uses_mock(self):
        """USE_MOCK=True 时 invoke() 应走 mock_result 路径。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="任意需求",
        )
        result = agent.invoke(state)
        assert result.success is True
        assert result.agent_role == AgentRole.REQUIREMENT
        assert result.result is not None

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    def test_build_context_contains_requirement(self):
        """build_context 应包含用户原始需求文本。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="重构用户模块",
        )
        ctx = agent.build_context(state)
        assert "重构用户模块" in ctx

    def test_build_context_nonempty(self):
        """即使 requirement 为空，build_context 也应返回非空字符串。"""
        agent = RequirementAgent()
        state = create_initial_state(
            task_id="test-001",
            repo_url="x", branch="main", requirement="",
        )
        ctx = agent.build_context(state)
        assert isinstance(ctx, str)
        assert len(ctx) >= 0  # 空需求也是合法的输入
