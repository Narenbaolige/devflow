"""DeveloperAgent 单元测试。"""

from app.agents.developer import DeveloperAgent
from contracts.agent_result import AgentRole, PatchResult
from contracts.state import create_initial_state


class TestDeveloperAgent:
    """验证 DeveloperAgent 的接口、Mock 输出、上下文构建。"""

    # ------------------------------------------------------------------
    # 接口契约
    # ------------------------------------------------------------------

    def test_role(self):
        agent = DeveloperAgent()
        assert agent.role == AgentRole.DEVELOPER

    def test_output_schema(self):
        agent = DeveloperAgent()
        assert agent.output_schema == PatchResult

    def test_use_mock_default(self):
        agent = DeveloperAgent()
        assert agent.USE_MOCK is True

    # ------------------------------------------------------------------
    # Mock 输出
    # ------------------------------------------------------------------

    def test_mock_result_success(self):
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.success is True
        assert result.agent_role == AgentRole.DEVELOPER

    def test_mock_result_contains_patch_fields(self):
        """Mock 输出的 result 应包含 PatchResult 全部关键字段。"""
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        data = result.result
        for key in [
            "file_path", "original_snippet", "patched_snippet",
            "diff", "change_description", "change_type",
        ]:
            assert key in data, f"缺少字段: {key}"

    def test_mock_result_diff_is_unified_format(self):
        """diff 应为 unified diff 格式（以 @@ 开头）。"""
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.result["diff"].startswith("@@")

    def test_mock_result_change_type_valid(self):
        """change_type 必须是合法的枚举值。"""
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert result.result["change_type"] in ("add", "modify", "delete", "rename")

    def test_mock_result_has_reasoning(self):
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.mock_result(state)
        assert len(result.reasoning) > 0

    # ------------------------------------------------------------------
    # invoke（Mock 路径）
    # ------------------------------------------------------------------

    def test_invoke_uses_mock(self):
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        result = agent.invoke(state)
        assert result.success is True
        assert result.agent_role == AgentRole.DEVELOPER
        assert result.result.get("diff", "").startswith("@@")

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    def test_build_context_includes_repo(self):
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="https://github.com/org/r",
            branch="main", requirement="x",
        )
        ctx = agent.build_context(state)
        assert "https://github.com/org/r" in ctx

    def test_build_context_includes_reviewer_feedback_on_rework(self):
        """返工场景：build_context 应包含 Reviewer 的 actionable_feedback。"""
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="x", branch="main", requirement="x",
        )
        # 模拟一次未通过的 Review
        state["review"] = {
            "agent_role": "reviewer",
            "success": True,
            "result": {
                "passed": False,
                "risk_level": "medium",
                "issues": [
                    {
                        "severity": "major",
                        "file_path": "app.py",
                        "description": "缺少异常处理",
                        "suggestion": "加 try-except",
                    }
                ],
                "summary": "需要修复",
                "actionable_feedback": "在 app.py L42 添加 try-except 包裹数据库调用",
            },
            "reasoning": "发现问题",
        }
        ctx = agent.build_context(state)
        assert "返工" in ctx
        assert "try-except" in ctx

    def test_build_context_nonempty(self):
        agent = DeveloperAgent()
        state = create_initial_state(
            task_id="t-001", repo_url="", branch="main", requirement="",
        )
        ctx = agent.build_context(state)
        assert isinstance(ctx, str)
