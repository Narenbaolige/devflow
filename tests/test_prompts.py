"""
Prompt 文件正确性验证。

6 个 System Prompt 文件是 Agent 行为的核心驱动。
验证文件存在、非空、编码正确、不超 token 预算。
"""

from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ALL_PROMPTS = [
    "developer_agent.md",
    "planner_agent.md",
    "requirement_agent.md",
    "reviewer_agent.md",
    "reviewer_security_rules.md",
    "single_agent.md",
]

# AgentBase max_context_tokens 默认值
TOKEN_BUDGET = 2000


def _estimate_tokens(text: str) -> int:
    """与 AgentBase._estimate_tokens 一致的估算：1 token ≈ 4 字符。"""
    return max(1, len(text) // 4)


# =============================================================================
# 文件存在性与完整性
# =============================================================================


class TestPromptFiles:
    """验证所有 prompt 文件存在、非空且编码正确。"""

    @pytest.mark.parametrize("filename", ALL_PROMPTS)
    def test_prompt_exists(self, filename):
        """每个 prompt 文件必须存在于 prompts/ 目录。"""
        path = PROMPTS_DIR / filename
        assert path.exists(), f"{filename} 不存在"
        assert path.is_file(), f"{filename} 不是文件"

    @pytest.mark.parametrize("filename", ALL_PROMPTS)
    def test_prompt_not_empty(self, filename):
        """每个 prompt 文件必须有实质内容。"""
        content = (PROMPTS_DIR / filename).read_text("utf-8")
        assert len(content.strip()) > 50, (
            f"{filename} 内容过短（{len(content.strip())} 字符），"
            f"可能为空或缺少有效 prompt"
        )

    def test_all_prompts_are_utf8(self):
        """所有 prompt 文件可正常以 UTF-8 解码。"""
        for filename in ALL_PROMPTS:
            (PROMPTS_DIR / filename).read_text("utf-8")  # 不抛异常即通过


# =============================================================================
# Token 预算合规
# =============================================================================


class TestPromptTokenBudget:
    """验证每个 Agent 的 System Prompt 不超出 2000 token 预算。"""

    def test_developer_prompt_under_budget(self):
        content = (PROMPTS_DIR / "developer_agent.md").read_text("utf-8")
        tokens = _estimate_tokens(content)
        assert tokens <= TOKEN_BUDGET, (
            f"developer_agent.md: {tokens} tokens，超出预算 {TOKEN_BUDGET}"
        )

    def test_planner_prompt_under_budget(self):
        content = (PROMPTS_DIR / "planner_agent.md").read_text("utf-8")
        tokens = _estimate_tokens(content)
        assert tokens <= TOKEN_BUDGET, (
            f"planner_agent.md: {tokens} tokens，超出预算 {TOKEN_BUDGET}"
        )

    def test_requirement_prompt_under_budget(self):
        content = (PROMPTS_DIR / "requirement_agent.md").read_text("utf-8")
        tokens = _estimate_tokens(content)
        assert tokens <= TOKEN_BUDGET, (
            f"requirement_agent.md: {tokens} tokens，超出预算 {TOKEN_BUDGET}"
        )

    def test_reviewer_prompt_under_budget(self):
        """ReviewerAgent 加载 main + security_rules，验证合并后不超预算。"""
        main = (PROMPTS_DIR / "reviewer_agent.md").read_text("utf-8")
        security = (PROMPTS_DIR / "reviewer_security_rules.md").read_text("utf-8")
        combined = main + "\n\n" + security
        tokens = _estimate_tokens(combined)
        assert tokens <= TOKEN_BUDGET, (
            f"reviewer main + security_rules: {tokens} tokens，超出预算 {TOKEN_BUDGET}"
        )

    def test_single_agent_prompt_under_budget(self):
        content = (PROMPTS_DIR / "single_agent.md").read_text("utf-8")
        tokens = _estimate_tokens(content)
        assert tokens <= TOKEN_BUDGET, (
            f"single_agent.md: {tokens} tokens，超出预算 {TOKEN_BUDGET}"
        )


# =============================================================================
# Agent 加载行为验证
# =============================================================================


class TestAgentPromptLoading:
    """验证各 Agent 的 _load_system_prompt() 正确加载文件并返回可读内容。"""

    def test_requirement_agent_loads_prompt(self):
        from app.agents.requirement import RequirementAgent
        agent = RequirementAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 100
        assert "需求" in prompt or "requirement" in prompt.lower()

    def test_planner_agent_loads_prompt(self):
        from app.agents.planner import PlannerAgent
        agent = PlannerAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 100

    def test_developer_agent_loads_prompt(self):
        from app.agents.developer import DeveloperAgent
        agent = DeveloperAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 100

    def test_reviewer_agent_loads_prompt_with_security_rules(self):
        from app.agents.reviewer import ReviewerAgent
        agent = ReviewerAgent()
        prompt = agent.system_prompt
        # Reviewer 必须包含安全规则附录
        assert "CWE-89" in prompt or "SQL" in prompt or "sql" in prompt, (
            "Reviewer prompt 应包含安全规则（CWE-89 / SQL注入）"
        )
        assert len(prompt) > 500, (
            f"Reviewer prompt 过短（{len(prompt)} 字符），可能未加载 security_rules"
        )

    def test_single_agent_loads_prompt(self):
        from app.agents.single_agent import SingleAgent
        agent = SingleAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 100
