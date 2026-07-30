"""
Developer Agent — 代码开发。

根据方案规划，读取目标文件，生成 unified diff 格式的代码修改。
"""

import os
from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, PatchResult, PatchSetResult
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class DeveloperAgent(AgentBase):

    # Tool calling is essential for the Developer to read real source files,
    # explore the repository structure, and run validation commands.  When the
    # LLM provider's tool-call payloads stall at the proxy, the invoke path
    # degrades gracefully: it retries without tool definitions first, then
    # falls back to the static repository_context snapshot.
    ENABLE_TOOL_CALLING = os.getenv("DEVFLOW_ENABLE_TOOLS", "true").lower() == "true"
    REQUIRE_READ_FOR_EXISTING_PATCHES = True
    # A unified diff can be substantially larger than a requirement analysis.
    # Do not turn a valid in-flight model response into a synthetic patch.
    TIMEOUT_SECONDS = None
    FALLBACK_TO_MOCK_ON_ERROR = False
    # Patch generation needs the actual target-file contents.  The base-agent
    # default (2K tokens) truncates that context and makes the model invent
    # snippets which cannot be applied.  Bumped to 32K so tool-call history
    # and repository context fit alongside the system prompt and plan data.
    max_context_tokens = 32_000

    @property
    def role(self) -> AgentRole:
        return AgentRole.DEVELOPER

    def _load_system_prompt(self) -> str:
        base = (PROMPTS_DIR / "developer_agent.md").read_text("utf-8")
        base += """

## Delivery contract (non-negotiable)

Return one complete `patches` array, with one PatchResult for every file that
must change. Implement every acceptance criterion, not merely the first
planning step. Include focused automated tests whenever behavior changes.
Never use placeholder output, Hello World, TODO-only code, or claim a feature
is implemented without executable behavior. For existing files, copy
`original_snippet` verbatim from the supplied repository source. For new files,
use `change_type: add` and an empty `original_snippet`.
"""
        tools_guide = PROMPTS_DIR / "developer_tools.md"
        if self.ENABLE_TOOL_CALLING and tools_guide.exists():
            base += "\n\n" + tools_guide.read_text("utf-8")
        return base

    @property
    def output_schema(self):
        return PatchSetResult

    def build_context(self, state: TeamState) -> str:
        meta = state.get("task_meta", {})
        plan = state.get("plan", {})
        plan_result = plan.get("result", {}) if plan else {}
        requirement = state.get("requirement_analysis", {})
        requirement_result = requirement.get("result", {}) if requirement else {}
        review = state.get("review", {})
        review_result = review.get("result", {}) if review else {}

        # ── Section 1: Task overview ──
        steps = plan_result.get("steps", [])
        steps_text = "\n".join(
            f"  {s.get('step_id', '?')}. {s.get('description', '?')} "
            f"→ {s.get('target_files', [])}"
            for s in (steps if isinstance(steps, list) else [])
        )
        context = (
            f"=== 任务概述 ===\n"
            f"仓库: {meta.get('repo_url', '')} (分支: {meta.get('branch', 'main')})\n"
            f"原始需求: {meta.get('requirement', '')}\n"
            f"验收条件: {requirement_result.get('acceptance_criteria', [])}\n"
            f"技术方案: {plan_result.get('approach', '待规划')}\n"
            f"修改步骤:\n{steps_text}\n"
        )

        # ── Section 2: Repository source code ──
        repository_context = state.get("repository_context") or ""
        if repository_context:
            context += (
                "\n=== 仓库源码（用于生成精确的 original_snippet） ===\n"
                "规则:\n"
                "  - 修改已有文件: original_snippet 必须从下面的 FILE: 块中逐字复制\n"
                "  - 创建新文件: original_snippet 留空, change_type 用 add\n"
                "  - file_path 只用相对路径, 禁止绝对路径\n\n"
                f"{repository_context}\n"
            )
        else:
            context += "\n[注意] 无仓库源码快照——将根据需求从零生成代码。\n"

        # ── Section 3: Rework / test failures ──
        if review_result and not review_result.get("passed", True):
            context += (
                f"\n=== Reviewer 反馈 ===\n"
                f"{review_result.get('actionable_feedback', '')}\n"
                f"问题: {review_result.get('issues', [])}\n"
            )

        rework = state.get("rework_context")
        if rework:
            rounds = rework.get("rounds", [])
            context += f"\n=== 返工诊断（共 {len(rounds)} 轮） ===\n"
            if rounds:
                # Show trend
                first = rounds[0]["failed_count"]
                last = rounds[-1]["failed_count"]
                trend = "↓ 改善中" if last < first else ("→ 无变化" if last == first else "↑ 恶化")
                context += f"趋势: {first} → {last} ({trend})\n"
                for r in rounds:
                    context += (
                        f"  第{r['round']}轮: {r['failed_count']} fail"
                        f" ({', '.join(r['failed_tests'][:3])})\n"
                    )
                if trend == "→ 无变化" and len(rounds) >= 2:
                    context += "⚠️ 多轮修复无进展——请用完全不同的实现思路！\n"

            context += f"\n本轮失败 ({rework.get('failed_count', 0)} 个):\n"
            details = rework.get("failure_details", [])
            for d in details:
                context += f"{d}\n---\n"
            context += (
                "\n请: (1)阅读断言值理解预期行为 (2)对比 repository_context 的实际代码 "
                "(3)如果多轮无进展，换一个实现方案。\n"
            )

        return context

    def mock_result(self, state: TeamState) -> AgentResult:
        """返回 Mock 结果。

        正常 Mock 模式（USE_MOCK=True）下，返回 success=True 用于开发调试。
        LLM 失败回退时，reasoning 会被基类覆写为 [FALLBACK] 前缀，
        下游可通过 success 字段判断 patch 是否可信任。
        """
        return AgentResult(
            agent_role=AgentRole.DEVELOPER,
            success=True,
            result=PatchSetResult(
                patches=[PatchResult(
                    file_path="math_utils.py",
                    original_snippet=(
                        "def factorial(n):\n"
                        "    if n == 0:\n"
                        "        return 1\n"
                        "    return n * factorial(n - 1)"
                    ),
                    patched_snippet=(
                    "def factorial(n):\n"
                    "    if not isinstance(n, int):\n"
                    "        raise TypeError('Input must be an integer')\n"
                    "    if n < 0:\n"
                    "        raise ValueError('Input must be non-negative')\n"
                    "    if n == 0:\n"
                    "        return 1\n"
                    "    return n * factorial(n - 1)"
                    ),
                    diff=(
                    "--- a/math_utils.py\n"
                    "+++ b/math_utils.py\n"
                    "@@ -1,4 +1,8 @@\n"
                    " def factorial(n):\n"
                    "+    if not isinstance(n, int):\n"
                    "+        raise TypeError('Input must be an integer')\n"
                    "+    if n < 0:\n"
                    "+        raise ValueError('Input must be non-negative')\n"
                    "     if n == 0:\n"
                    "         return 1\n"
                    "     return n * factorial(n - 1)"
                    ),
                    change_description="Mock: 为目标函数添加参数类型校验",
                    change_type="modify",
                )]
            ).model_dump(),
            reasoning="Mock: 代码开发完成（Day 2 模式）",
        )
