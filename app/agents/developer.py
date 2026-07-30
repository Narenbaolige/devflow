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

    # DeepSeek's OpenAI-compatible endpoint accepts ordinary structured
    # completions reliably in this deployment, while native tool-call payloads
    # stall at the local proxy.  Generate the patch directly from the verified
    # plan; sandbox application and tests still run against the real checkout.
    ENABLE_TOOL_CALLING = False
    # A unified diff can be substantially larger than a requirement analysis.
    # Do not turn a valid in-flight model response into a synthetic patch.
    TIMEOUT_SECONDS = 120
    FALLBACK_TO_MOCK_ON_ERROR = False
    # Patch generation needs the actual target-file contents.  The base-agent
    # default (2K tokens) truncates that context and makes the model invent
    # snippets which cannot be applied.
    max_context_tokens = 8_000

    @property
    def role(self) -> AgentRole:
        return AgentRole.DEVELOPER

    def _load_system_prompt(self) -> str:
        base = (PROMPTS_DIR / "developer_agent.md").read_text("utf-8")
        tools_guide = PROMPTS_DIR / "developer_tools.md"
        if self.ENABLE_TOOL_CALLING and tools_guide.exists():
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
        repository_context = state.get("repository_context") or ""
        if repository_context:
            context += (
                "\n以下是仓库的真实源码摘要。修改已有文件时，file_path 必须出现在摘要中，"
                "且 original_snippet 必须逐字复制摘要中的原文。"
                "新增文件时，original_snippet 必须为空字符串，并在 change_type 中使用 add。\n"
                f"{repository_context}\n"
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
        """返回 Mock 结果。

        正常 Mock 模式（USE_MOCK=True）下，返回 success=True 用于开发调试。
        LLM 失败回退时，reasoning 会被基类覆写为 [FALLBACK] 前缀，
        下游可通过 success 字段判断 patch 是否可信任。
        """
        return AgentResult(
            agent_role=AgentRole.DEVELOPER,
            success=True,
            result=PatchResult(
                file_path="math_utils.py",
                original_snippet="def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)",
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
            ).model_dump(),
            reasoning="Mock: 代码开发完成（Day 2 模式）",
        )
