"""
contracts/agent_result.py — Agent 输入输出契约。

定义所有 Agent 的结构化输出模型 + 统一包装类。
每个 Agent 的输出都是独立的 Pydantic BaseModel，
再通过 AgentResult 统一包装，确保可观测性一致。

P0 冻结，修改需四人评审。
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Agent 角色枚举
# =============================================================================

class AgentRole(StrEnum):
    """Agent 角色枚举"""
    REQUIREMENT = "requirement"
    PLANNER = "planner"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    SECURITY = "security"


# =============================================================================
# Requirement Agent
# =============================================================================

class RequirementResult(BaseModel):
    """需求分析输出 — Requirement Agent"""

    summary: str = Field(
        description="需求一句话概述（≤100 字）"
    )
    affected_modules: list[str] = Field(
        description="受影响的模块或文件路径列表"
    )
    acceptance_criteria: list[str] = Field(
        description="可验证的验收条件（每条都是可测试的）"
    )
    ambiguity_flags: list[str] = Field(
        default_factory=list,
        description="模糊点或需要人类澄清的问题",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="分析置信度。≥0.6 直接进入规划，<0.6 触发人工",
    )


# =============================================================================
# Planner Agent
# =============================================================================

class PlanStep(BaseModel):
    """单个计划步骤"""

    step_id: int
    description: str = Field(description="本步骤要做什么")
    target_files: list[str] = Field(description="需要修改的文件路径")
    expected_changes: str = Field(description="预期变更描述")
    depends_on: list[int] = Field(
        default_factory=list,
        description="依赖的前置步骤 ID",
    )


class PlanResult(BaseModel):
    """方案规划输出 — Planner Agent"""

    approach: str = Field(
        description="总体技术方案（≤500 字）"
    )
    steps: list[PlanStep]
    risk_points: list[str] = Field(
        default_factory=list,
        description="识别的技术风险点",
    )
    alternative_approaches: list[str] = Field(
        default_factory=list,
        description="备选方案（如有）",
    )
    estimated_changed_files: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


# =============================================================================
# Developer Agent
# =============================================================================

class PatchResult(BaseModel):
    """单个文件的代码修改"""

    file_path: str
    original_snippet: str = Field(description="修改前的代码片段（上下文）")
    patched_snippet: str = Field(description="修改后的代码片段")
    diff: str = Field(description="unified diff 格式的完整差异")
    change_description: str = Field(description="本修改做了什么，一句话")
    change_type: Literal["add", "modify", "delete", "rename"]


# =============================================================================
# Reviewer Agent（含测试结果分析）
# =============================================================================

class ReviewIssue(BaseModel):
    """审查发现的问题"""

    severity: Literal["critical", "high", "major", "minor", "suggestion"]
    file_path: str
    line_range: str | None = None
    description: str
    suggestion: str = Field(description="可执行的修复建议")


class ReviewResult(BaseModel):
    """代码审查输出 — Reviewer Agent（含测试结果分析）"""

    passed: bool
    risk_level: Literal["low", "medium", "high"]
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str
    actionable_feedback: str = Field(
        default="",
        description="如果未通过，给 Developer 的可执行返工指令（直接可据此修改）",
    )


# =============================================================================
# Security Agent
# =============================================================================

class SecurityIssue(BaseModel):
    """安全审查发现的问题"""

    vulnerability_type: str = Field(
        description="漏洞类型，如 sql_injection, path_traversal, hardcoded_secret"
    )
    severity: Literal["critical", "high", "medium", "low"]
    file_path: str
    line_range: str | None = None
    description: str
    remediation: str = Field(description="修复建议")
    cwe_id: str | None = Field(
        default=None,
        description="CWE 编号，如 CWE-89",
    )


class SecurityResult(BaseModel):
    """安全审查输出 — Security Agent"""

    passed: bool
    issues: list[SecurityIssue] = Field(default_factory=list)
    summary: str
    requires_approval: bool = Field(
        description=(
            "是否触发人工审批。"
            "规则：存在 critical 级别 → True；≥2 个 high → True；其余 → False"
        ),
    )


# =============================================================================
# 统一 Agent 调用记录
# =============================================================================

class AgentInvocation(BaseModel):
    """每次 Agent 调用的元信息"""

    agent_role: AgentRole
    model: str                       # 使用的模型名称
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# 统一 Agent 返回包装
# =============================================================================

class AgentResult(BaseModel):
    """
    统一 Agent 返回包装。

    所有 Agent 节点的输出均使用此模型包装。
    具体产出物（RequirementResult 等）放在 result 字段中。

    用法：
        req = RequirementResult(summary="...", ...)
        wrapped = AgentResult(
            agent_role=AgentRole.REQUIREMENT,
            success=True,
            result=req.model_dump(),
            invocation=AgentInvocation(...),
            reasoning="需求描述清晰，置信度高",
        )
    """

    agent_role: AgentRole
    success: bool
    result: dict | None = Field(
        default=None,
        description="具体 Agent 的 Pydantic 模型 .model_dump() 结果",
    )
    error: str | None = Field(
        default=None,
        description="失败时的错误信息",
    )
    invocation: AgentInvocation | None = Field(
        default=None,
        description="LLM 调用元信息",
    )
    reasoning: str = Field(
        default="",
        description="Agent 决策理由（一句话，用于可解释性）",
    )
    next_action: str = Field(
        default="continue",
        description="建议的下一步：continue / retry / abort / await_approval",
    )
