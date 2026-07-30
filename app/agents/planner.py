"""
Planner Agent — 方案规划。

基于需求分析和代码仓库结构，设计文件级别的实现方案。
"""

from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, PlanResult, PlanStep
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PlannerAgent(AgentBase):
    # The workspace is prepared before this node runs, so the Planner can
    # ground its file-level plan in the actual repository rather than guess.
    ENABLE_TOOL_CALLING = True
    REQUIRE_TOOL_CALLING = True
    TIMEOUT_SECONDS = None
    FALLBACK_TO_MOCK_ON_ERROR = False

    @property
    def role(self) -> AgentRole:
        return AgentRole.PLANNER

    def _load_system_prompt(self) -> str:
        return (PROMPTS_DIR / "planner_agent.md").read_text("utf-8")

    @property
    def output_schema(self):
        return PlanResult

    def build_context(self, state: TeamState) -> str:
        meta = state.get("task_meta", {})
        req = state.get("requirement_analysis", {})
        req_result = req.get("result", {}) if req else {}
        return (
            f"仓库地址：{meta.get('repo_url', '')}\n"
            f"分支：{meta.get('branch', 'main')}\n"
            f"需求概要：{req_result.get('summary', meta.get('requirement', ''))}\n"
            f"受影响模块：{', '.join(req_result.get('affected_modules', []))}\n"
            f"验收条件：{'; '.join(req_result.get('acceptance_criteria', []))}"
        )

    def mock_result(self, state: TeamState) -> AgentResult:
        return AgentResult(
            agent_role=AgentRole.PLANNER,
            success=True,
            result=PlanResult(
                approach="Mock: 采用最小侵入式修改，在目标函数入口处添加参数校验逻辑。",
                steps=[
                    PlanStep(
                        step_id=1,
                        description="定位目标函数所在文件并读取当前代码",
                        target_files=["待定位"],
                        expected_changes="了解现有函数签名和逻辑",
                        depends_on=[],
                    ),
                    PlanStep(
                        step_id=2,
                        description="在函数入口添加参数校验逻辑",
                        target_files=["待定位"],
                        expected_changes="添加 isinstance/type 检查或 ValueError 抛出",
                        depends_on=[1],
                    ),
                    PlanStep(
                        step_id=3,
                        description="补充或更新相关测试用例",
                        target_files=["待定位"],
                        expected_changes="添加边界条件测试",
                        depends_on=[2],
                    ),
                ],
                risk_points=["参数类型假设可能与现有调用方不兼容"],
                estimated_changed_files=2,
                confidence=0.80,
            ).model_dump(),
            reasoning="Mock: 方案规划完成（Day 2 模式）",
        )
