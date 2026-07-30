"""
Planner Agent — 方案规划。

基于需求分析和代码仓库结构，设计文件级别的实现方案。
"""

import os
import re as _re
from pathlib import Path

from app.agents.base import AgentBase
from contracts.agent_result import AgentResult, AgentRole, PlanResult, PlanStep
from contracts.state import TeamState

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PlannerAgent(AgentBase):

    # setup_workspace now runs *before* this node (graph reorder, Phase 1.2),
    # so the repository is already cloned and repository_context is available.
    # Enabling tool calling lets the Planner browse real source files before
    # designing its implementation plan — target_files become grounded in the
    # actual project structure instead of guessed.
    ENABLE_TOOL_CALLING = os.getenv("DEVFLOW_ENABLE_TOOLS", "true").lower() == "true"
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
        ctx = (
            f"仓库地址：{meta.get('repo_url', '')}\n"
            f"分支：{meta.get('branch', 'main')}\n"
            f"需求概要：{req_result.get('summary', meta.get('requirement', ''))}\n"
            f"受影响模块：{', '.join(req_result.get('affected_modules', []))}\n"
            f"验收条件：{'; '.join(req_result.get('acceptance_criteria', []))}"
        )
        repo = state.get("repository_context", "")
        if repo:
            ctx += f"\n仓库代码结构（用于定位目标文件）：\n{repo[:8000]}\n"
        return ctx

    def _infer_target_files(self, state: TeamState) -> tuple[str, str]:
        """从 repository_context 和 requirement 推断目标文件。"""
        repo = state.get("repository_context", "") or ""
        meta = state.get("task_meta", {})
        req = (meta.get("requirement", "") or "").lower()

        # Extract filenames from repository_context FILE: lines
        repo_files = _re.findall(r"FILE:\s+(\S+)", repo)

        # Match requirement keywords to repo files
        kw_map = {
            "sort": ["sort", "bubble"], "bubble": ["sort", "bubble"],
            "calculator": ["calc"], "calc": ["calc"],
            "factorial": ["factorial", "math"], "math": ["math", "utils"],
            "validation": ["valid"], "validate": ["valid"],
            "refactor": ["service", "utils"], "extract": ["service", "utils"],
            "retry": ["retry", "network"], "cache": ["cache"],
            "api": ["api", "route"], "database": ["db", "database"],
        }
        matched = []
        for kw, suffixes in kw_map.items():
            if kw in req:
                for f in repo_files:
                    if any(s in f.lower() for s in suffixes) and f not in matched:
                        matched.append(f)

        if not matched:
            src = [f for f in repo_files if f.endswith(".py") and "test" not in f.lower()]
            test = [f for f in repo_files if "test" in f.lower()]
            matched = (src[:2] + test[:1]) if src else list(repo_files[:2])

        target_src = matched[0] if matched else "src/main.py"
        target_test = matched[1] if len(matched) > 1 else (
            f"tests/test_{target_src.rsplit('/', 1)[-1]}" if "/" in target_src
            else f"tests/test_{target_src}"
        )
        return target_src, target_test

    def mock_result(self, state: TeamState) -> AgentResult:
        target_src, target_test = self._infer_target_files(state)
        meta = state.get("task_meta", {})
        req = (meta.get("requirement", "") or "")[:60]

        return AgentResult(
            agent_role=AgentRole.PLANNER,
            success=True,
            result=PlanResult(
                approach=f"Mock: 基于需求「{req}」推断目标文件为 {target_src}。",
                steps=[
                    PlanStep(
                        step_id=1,
                        description=f"读取 {target_src} 了解现有代码结构",
                        target_files=[target_src],
                        expected_changes="理解现有函数签名和逻辑",
                        depends_on=[],
                    ),
                    PlanStep(
                        step_id=2,
                        description=f"在 {target_src} 中实现或修改核心逻辑",
                        target_files=[target_src],
                        expected_changes="根据需求实现功能或修复 Bug",
                        depends_on=[1],
                    ),
                    PlanStep(
                        step_id=3,
                        description=f"编写或更新测试用例 {target_test}",
                        target_files=[target_test],
                        expected_changes="覆盖边界条件和正常路径",
                        depends_on=[2],
                    ),
                ],
                risk_points=["Mock 模式——基于关键词匹配推断，可能与实际仓库结构不完全一致"],
                alternative_approaches=["真实分析模式：手动浏览仓库后再确认方案"],
                estimated_changed_files=2,
                confidence=0.7,
            ).model_dump(),
            reasoning=f"Mock: 方案规划完成，目标文件={target_src}, {target_test}",
        )
