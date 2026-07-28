"""
Developer Agent — 代码开发。

根据方案规划，读取目标文件，生成 unified diff 格式的代码修改。
"""

from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, PatchResult
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class DeveloperAgent(AgentBase):

    ENABLE_TOOL_CALLING = True

    @property
    def role(self) -> AgentRole:
        return AgentRole.DEVELOPER

    def _load_system_prompt(self) -> str:
        base = (PROMPTS_DIR / "developer_agent.md").read_text("utf-8")
        tools_guide = PROMPTS_DIR / "developer_tools.md"
        if tools_guide.exists():
            base += "\n\n" + tools_guide.read_text("utf-8")
        return base

    @property
    def output_schema(self):
        return PatchResult

    def build_context(self, state: TeamState) -> str:
        meta = state.get("task_meta", {})
        plan = state.get("plan", {})
        plan_result = plan.get("result", {}) if plan else {}
        review = state.get("review", {})
        review_result = review.get("result", {}) if review else {}

        context = (
            f"仓库地址：{meta.get('repo_url', '')}\n"
            f"分支：{meta.get('branch', 'main')}\n"
            f"技术方案：{plan_result.get('approach', '待规划')}\n"
            f"修改步骤：{plan_result.get('steps', [])}\n"
        )

        # 如果是返工迭代，附上 Reviewer 的反馈
        if review_result and not review_result.get("passed", True):
            context += (
                f"\n[返工] Reviewer 反馈：\n"
                f"{review_result.get('actionable_feedback', '')}\n"
                f"问题列表：{review_result.get('issues', [])}\n"
            )

        return context

    def mock_result(self, state: TeamState) -> AgentResult:
        return AgentResult(
            agent_role=AgentRole.DEVELOPER,
            success=True,
            result=PatchResult(
                file_path="src/main.py",
                original_snippet="# TODO: 添加参数校验",
                patched_snippet=(
                    "def validated_input(value):\n"
                    '    if not isinstance(value, (int, float)):\n'
                    '        raise TypeError(f"Expected number, got {type(value)}")\n'
                    "    return value"
                ),
                diff=(
                    "@@ -1,1 +1,4 @@\n"
                    "-# TODO: 添加参数校验\n"
                    "+def validated_input(value):\n"
                    '+    if not isinstance(value, (int, float)):\n'
                    '+        raise TypeError(f"Expected number, got {type(value)}")\n'
                    "+    return value"
                ),
                change_description="Mock: 为目标函数添加参数类型校验",
                change_type="modify",
            ).model_dump(),
            reasoning="Mock: 代码开发完成（Day 2 模式）",
        )
