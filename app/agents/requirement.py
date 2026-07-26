"""
Requirement Agent — 需求分析。

将用户的自然语言需求转化为结构化的需求规格。
"""

from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, RequirementResult
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class RequirementAgent(AgentBase):

    @property
    def role(self) -> AgentRole:
        return AgentRole.REQUIREMENT

    def _load_system_prompt(self) -> str:
        return (PROMPTS_DIR / "requirement_agent.md").read_text("utf-8")

    @property
    def output_schema(self):
        return RequirementResult

    def build_context(self, state: TeamState) -> str:
        meta = state.get("task_meta", {})
        return f"用户需求：\n{meta.get('requirement', '')}"

    def mock_result(self, state: TeamState) -> AgentResult:
        meta = state.get("task_meta", {})
        req_text = meta.get("requirement", "")
        return AgentResult(
            agent_role=AgentRole.REQUIREMENT,
            success=True,
            result=RequirementResult(
                summary=f"需求概述：{req_text[:80]}",
                affected_modules=["待分析"],
                acceptance_criteria=[
                    "功能行为符合需求描述",
                    "边界条件处理正确",
                    "错误输入有合理提示",
                ],
                ambiguity_flags=[],
                confidence=0.85,
            ).model_dump(),
            reasoning="Mock: 需求分析完成（Day 2 模式）",
        )
