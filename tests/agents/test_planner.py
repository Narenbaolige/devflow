"""PlannerAgent 单元测试。"""

from app.agents.planner import PlannerAgent
from contracts.agent_result import AgentRole, PlanResult
from contracts.state import create_initial_state


class TestPlannerAgent:
    """验证 PlannerAgent 的接口、Mock 输出、上下文构建。"""

    # ------------------------------------------------------------------
    # 接口契约
    # ------------------------------------------------------------------

    def test_role(self):
        agent = PlannerAgent()
        assert agent.role == AgentRole.PLANNER

    def test_output_schema(self):
        agent = PlannerAgent()
        assert agent.output_schema == PlanResult

    def test_use_mock_default(self):
        agent = PlannerAgent()
        assert agent.USE_MOCK is True

    # ------------------------------------------------------------------
    # Mock 输出
    # ------------------------------------------------------------------

    def test_mock_result_success(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="https://github.com/example/r",
            branch="main", requirement="添加缓存层",
        )
        result = agent.mock_result(state)
        assert result.success is True
        assert result.agent_role == AgentRole.PLANNER

    def test_mock_result_has_plan_structure(self):
        """Mock 输出的 result 应包含 PlanResult 全部关键字段。"""
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="重构",
        )
        result = agent.mock_result(state)
        data = result.result
        assert data is not None
        for key in ["approach", "steps", "risk_points", "estimated_changed_files", "confidence"]:
            assert key in data, f"缺少字段: {key}"

    def test_mock_result_steps_are_ordered(self):
        """PlanStep 应有序号且依赖关系合法。"""
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        steps = result.result["steps"]
        assert len(steps) >= 1
        step_ids = {s["step_id"] for s in steps}
        for s in steps:
            # 每个 step 的依赖必须在 step_ids 中（或为空）
            for dep_id in s.get("depends_on", []):
                assert dep_id in step_ids, f"step {s['step_id']} 依赖不存在的 step {dep_id}"

    def test_mock_result_confidence_range(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert 0.0 <= result.result["confidence"] <= 1.0

    def test_mock_result_has_reasoning(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert len(result.reasoning) > 0

    # ------------------------------------------------------------------
    # invoke（Mock 路径）
    # ------------------------------------------------------------------

    def test_invoke_uses_mock(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.invoke(state)
        assert result.success is True
        assert result.agent_role == AgentRole.PLANNER
        assert "steps" in result.result

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    def test_build_context_includes_repo(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="https://github.com/org/repo",
            branch="main", requirement="升级依赖",
        )
        ctx = agent.build_context(state)
        assert "https://github.com/org/repo" in ctx

    def test_build_context_includes_branch(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x",
            branch="develop", requirement="x",
        )
        ctx = agent.build_context(state)
        assert "develop" in ctx

    def test_build_context_nonempty(self):
        agent = PlannerAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="", branch="main", requirement="",
        )
        ctx = agent.build_context(state)
        assert isinstance(ctx, str)
