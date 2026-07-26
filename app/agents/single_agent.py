"""
Single Agent — 单 Agent 基线。

一个 Agent 完成需求分析 + 方案规划 + 代码开发 + 自我审查全部工作。
用于消融实验：单 Agent vs 多 Agent（4-Agent Pipeline）对比。
"""

from pathlib import Path

from pydantic import BaseModel, Field

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


# =============================================================================
# SingleAgentResult — 组合输出模型
# =============================================================================

class SinglePatchItem(BaseModel):
    """单文件修改。"""
    file_path: str
    diff: str = Field(description="unified diff 格式")
    change_description: str
    change_type: str = Field(default="modify")


class SingleReviewIssue(BaseModel):
    """自审发现的问题。"""
    severity: str = Field(default="minor")
    file_path: str
    description: str
    suggestion: str = ""


class SingleAgentResult(BaseModel):
    """
    单 Agent 组合输出。

    一次性包含全部 4 个 Agent 的产出物，
    可直接映射到多 Agent Pipeline 的对应字段进行对比。
    """

    # --- Requirement ---
    summary: str = Field(description="需求一句话概述")
    affected_modules: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    requirement_confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    # --- Plan ---
    approach: str = Field(description="总体技术方案")
    modification_steps: list[str] = Field(
        default_factory=list,
        description="修改步骤（每步一条文字描述）",
    )
    risk_points: list[str] = Field(default_factory=list)
    plan_confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    # --- Development ---
    patches: list[SinglePatchItem] = Field(default_factory=list)

    # --- Self-Review ---
    self_review_passed: bool = Field(default=True)
    self_review_issues: list[SingleReviewIssue] = Field(default_factory=list)
    self_review_summary: str = Field(default="")


# =============================================================================
# SingleAgent
# =============================================================================

class SingleAgent(AgentBase):
    """
    单 Agent 基线。

    一个 Agent 完成全部分析→规划→开发→审查工作。
    用于消融实验中与 4-Agent Pipeline 对比。

    AgentRole 使用 REVIEWER 作为占位（因为 contracts 中无 SINGLE 枚举）。
    实际实验中通过 result 字段的 SingleAgentResult 结构区分。
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.REVIEWER  # 占位——不影响实验数据收集

    def _load_system_prompt(self) -> str:
        return (PROMPTS_DIR / "single_agent.md").read_text("utf-8")

    @property
    def output_schema(self):
        return SingleAgentResult

    def build_context(self, state: TeamState) -> str:
        meta = state.get("task_meta", {})
        return (
            f"仓库地址：{meta.get('repo_url', '')}\n"
            f"分支：{meta.get('branch', 'main')}\n"
            f"用户需求：\n{meta.get('requirement', '')}\n"
        )

    def mock_result(self, state: TeamState) -> AgentResult:
        meta = state.get("task_meta", {})
        req_text = meta.get("requirement", "")
        return AgentResult(
            agent_role=self.role,
            success=True,
            result=SingleAgentResult(
                # Requirement
                summary=f"需求概述：{req_text[:80]}",
                affected_modules=["待分析"],
                acceptance_criteria=[
                    "功能行为符合需求描述",
                    "边界条件处理正确",
                ],
                requirement_confidence=0.85,
                # Plan
                approach="采用最小侵入式修改，在目标位置添加逻辑。",
                modification_steps=[
                    "1. 定位目标代码所在文件",
                    "2. 实现核心逻辑修改",
                    "3. 补充边界条件处理",
                ],
                risk_points=["可能与现有调用方不兼容"],
                plan_confidence=0.80,
                # Development
                patches=[
                    SinglePatchItem(
                        file_path="src/main.py",
                        diff=(
                            "@@ -1,3 +1,5 @@\n"
                            " def process(value):\n"
                            "+    if not isinstance(value, (int, float)):\n"
                            '+        raise TypeError(f"Expected number")\n'
                            "     return value * 2"
                        ),
                        change_description="添加参数类型校验",
                        change_type="modify",
                    )
                ],
                # Self-Review
                self_review_passed=True,
                self_review_issues=[],
                self_review_summary="自审通过：代码修改逻辑正确，无安全风险。",
            ).model_dump(),
            reasoning="Mock: 单 Agent 全流程完成（Day 2 模式）",
        )
