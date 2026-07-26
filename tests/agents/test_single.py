"""SingleAgent 单元测试 — 单 Agent 基线。"""

from app.agents.single_agent import SingleAgent, SingleAgentResult, SinglePatchItem
from contracts.state import create_initial_state


class TestSingleAgentResult:
    """验证 SingleAgentResult 模型的正确性。"""

    def test_empty_result_validation(self):
        """最小合法 SingleAgentResult 应能创建成功。"""
        r = SingleAgentResult(
            summary="测试",
            approach="方案",
        )
        assert r.summary == "测试"
        assert r.patches == []
        assert r.self_review_passed is True

    def test_full_result_with_patches(self):
        """含 Patch 的完整结果。"""
        r = SingleAgentResult(
            summary="需求概述",
            affected_modules=["a.py", "b.py"],
            acceptance_criteria=["条件1", "条件2"],
            requirement_confidence=0.9,
            approach="技术方案描述",
            modification_steps=["步骤1", "步骤2"],
            risk_points=["风险1"],
            plan_confidence=0.85,
            patches=[
                SinglePatchItem(
                    file_path="a.py",
                    diff="@@ -1 +1 @@\n-old\n+new",
                    change_description="修改 a.py",
                    change_type="modify",
                )
            ],
            self_review_passed=True,
            self_review_issues=[],
            self_review_summary="通过",
        )
        assert len(r.patches) == 1
        assert r.patches[0].file_path == "a.py"

    def test_confidence_bounds(self):
        """置信度必须在 0.0-1.0 范围内。"""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SingleAgentResult(summary="x", approach="x", requirement_confidence=1.5)

    def test_can_serialize_to_dict(self):
        """model_dump() 应可序列化为 plain dict（用于对比实验数据收集）。"""
        r = SingleAgentResult(
            summary="s",
            approach="a",
            patches=[
                SinglePatchItem(
                    file_path="f.py",
                    diff="@@ -1 +1 @@",
                    change_description="c",
                    change_type="modify",
                )
            ],
        )
        data = r.model_dump()
        assert isinstance(data, dict)
        assert data["summary"] == "s"
        assert len(data["patches"]) == 1


class TestSingleAgent:
    """验证 SingleAgent 的接口和 Mock 输出。"""

    def test_role_is_reviewer_placeholder(self):
        """SingleAgent 的 role 使用 REVIEWER 占位（contracts 无 SINGLE 枚举）。"""
        from contracts.agent_result import AgentRole
        agent = SingleAgent()
        assert agent.role == AgentRole.REVIEWER

    def test_output_schema_is_single_agent_result(self):
        agent = SingleAgent()
        assert agent.output_schema == SingleAgentResult

    def test_use_mock_default(self):
        agent = SingleAgent()
        assert agent.USE_MOCK is True

    def test_mock_result_success(self):
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.mock_result(state)
        assert result.success is True

    def test_mock_result_contains_all_sections(self):
        """Mock 输出应包含 Requirement / Plan / Development / Review 四个部分。"""
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.mock_result(state)
        data = result.result

        # Requirement
        assert "summary" in data
        assert "acceptance_criteria" in data
        assert "requirement_confidence" in data
        # Plan
        assert "approach" in data
        assert "modification_steps" in data
        assert "plan_confidence" in data
        # Development
        assert "patches" in data
        assert len(data["patches"]) >= 1
        # Self-Review
        assert "self_review_passed" in data
        assert "self_review_summary" in data

    def test_mock_result_patches_are_unified_diff(self):
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.mock_result(state)
        for patch in result.result["patches"]:
            assert patch["diff"].startswith("@@")

    def test_mock_result_has_reasoning(self):
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.mock_result(state)
        assert len(result.reasoning) > 0

    # ------------------------------------------------------------------
    # invoke（Mock 路径）
    # ------------------------------------------------------------------

    def test_invoke_uses_mock(self):
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.invoke(state)
        assert result.success is True
        assert len(result.result["patches"]) >= 1

    # ------------------------------------------------------------------
    # 与 4-Agent Pipeline 输出的对比性
    # ------------------------------------------------------------------

    def test_output_mappable_to_pipeline_fields(self):
        """
        SingleAgentResult 的字段应可映射到 4-Agent Pipeline 的对应字段，
        确保消融实验数据可对比。
        """
        agent = SingleAgent()
        state = create_initial_state(
            task_id="t-sa", repo_url="x", branch="main", requirement="测试",
        )
        result = agent.mock_result(state)
        data = result.result

        # 可映射到 RequirementResult
        assert "summary" in data
        assert "affected_modules" in data
        assert "acceptance_criteria" in data
        assert "requirement_confidence" in data

        # 可映射到 PlanResult
        assert "approach" in data
        assert "modification_steps" in data
        assert "risk_points" in data

        # 可映射到 PatchResult
        for p in data["patches"]:
            assert "file_path" in p
            assert "diff" in p
            assert "change_description" in p
            assert "change_type" in p

        # 可映射到 ReviewResult
        assert "self_review_passed" in data
        assert "self_review_issues" in data
        assert "self_review_summary" in data
