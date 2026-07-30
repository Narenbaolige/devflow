"""
Reviewer Agent — 代码审查 + 测试结果分析 + 安全风险标注。

审查 Developer 的代码修改，分析沙箱测试结果，
标注安全风险（两周版：Security Agent 集成于此）。
"""

from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, ReviewResult
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class ReviewerAgent(AgentBase):

    # A fabricated approval defeats the quality gate. Surface upstream errors
    # rather than accepting a Mock review in production mode.
    FALLBACK_TO_MOCK_ON_ERROR = False
    TIMEOUT_SECONDS = None

    @property
    def role(self) -> AgentRole:
        return AgentRole.REVIEWER

    def _load_system_prompt(self) -> str:
        main = (PROMPTS_DIR / "reviewer_agent.md").read_text("utf-8")
        security = (PROMPTS_DIR / "reviewer_security_rules.md").read_text("utf-8")
        return main + "\n\n" + security

    @property
    def output_schema(self):
        return ReviewResult

    def build_context(self, state: TeamState) -> str:
        patches = state.get("patches", [])
        sandbox_results = state.get("sandbox_results", [])
        req = state.get("requirement_analysis", {})
        req_result = req.get("result", {}) if req else {}

        patch_summary = "\n".join(
            f"  - {p.get('file_path', 'unknown')}: "
            f"{p.get('change_description', '无描述')}\n"
            f"    实际修改内容:\n{p.get('patched_snippet', '')[:4000]}"
            for p in patches
        )

        test_summary = "\n".join(
            f"  - execution {r.get('execution_id', '?')}: "
            f"status={r.get('status', '?')}, "
            f"exit_code={r.get('exit_code', '?')}"
            for r in sandbox_results
        )

        return (
            f"原始需求：{req_result.get('summary', '无')}\n"
            f"验收条件：{req_result.get('acceptance_criteria', [])}\n"
            f"代码修改：\n{patch_summary or '  无'}\n"
            f"测试结果：\n{test_summary or '  无'}\n"
            f"\n--- 安全审查 ---\n"
            f"请根据 System Prompt 中的安全检测规则，逐项检查以下三类安全问题：\n"
            f"1. SQL 注入 (CWE-89) — 是否存在字符串拼接/格式化 SQL？\n"
            f"2. 硬编码密钥 (CWE-798) — 是否存在密码/Token/API Key 明文？\n"
            f"3. 路径遍历 (CWE-22) — 用户输入是否直接控制文件路径？\n"
        )

    def mock_result(self, state: TeamState) -> AgentResult:
        return AgentResult(
            agent_role=AgentRole.REVIEWER,
            success=True,
            result=ReviewResult(
                passed=True,
                risk_level="low",
                issues=[],
                summary="Mock: 代码审查通过，未发现问题。",
                actionable_feedback="",
            ).model_dump(),
            reasoning="Mock: 代码审查完成（Day 2 模式）",
        )
