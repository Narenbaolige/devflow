"""Agent 基类与契约验证测试。"""

import pytest

from contracts.agent_result import (
    AgentInvocation,
    AgentResult,
    AgentRole,
    PatchResult,
    RequirementResult,
    ReviewResult,
    SecurityResult,
)


class TestAgentResultContracts:
    """验证 AgentResult 契约的正确性。"""

    def test_requirement_result_validation(self):
        """RequirementResult 合法输入应通过校验。"""
        result = RequirementResult(
            summary="修复 factorial 函数的参数校验",
            affected_modules=["math_utils.py"],
            acceptance_criteria=["输入负数时应抛出 ValueError"],
            confidence=0.85,
        )
        assert result.summary
        assert result.confidence >= 0.6

    def test_requirement_result_invalid_confidence(self):
        """RequirementResult confidence 越界应抛出 ValidationError。"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RequirementResult(
                summary="test",
                affected_modules=["test.py"],
                acceptance_criteria=["test"],
                confidence=1.5,  # 非法
            )

    def test_agent_result_wrapper(self):
        """AgentResult 统一包装应正确序列化。"""
        req = RequirementResult(
            summary="需求概述",
            affected_modules=["a.py"],
            acceptance_criteria=["验收条件1"],
            confidence=0.9,
        )
        wrapped = AgentResult(
            agent_role=AgentRole.REQUIREMENT,
            success=True,
            result=req.model_dump(),
            invocation=AgentInvocation(
                agent_role=AgentRole.REQUIREMENT,
                model="gpt-4o-mini",
                input_tokens=500,
                output_tokens=200,
                duration_ms=1200,
            ),
            reasoning="需求清晰",
        )
        data = wrapped.model_dump()
        assert data["success"] is True
        assert data["result"]["summary"] == "需求概述"

    def test_review_result_passed(self):
        """ReviewResult 通过时应无 issues。"""
        result = ReviewResult(
            passed=True,
            risk_level="low",
            summary="代码质量良好",
        )
        assert result.passed
        assert len(result.issues) == 0

    def test_review_result_failed_with_feedback(self):
        """ReviewResult 不通过时必须包含 actionable_feedback。"""
        result = ReviewResult(
            passed=False,
            risk_level="high",
            issues=[
                {
                    "severity": "major",
                    "file_path": "app.py",
                    "description": "缺少异常处理",
                    "suggestion": "加 try-except 包裹",
                }
            ],
            summary="需要改进",
            actionable_feedback="在 app.py 第 42 行加 try-except",
        )
        assert not result.passed
        assert len(result.actionable_feedback) > 0

    def test_patch_result_unified_diff(self):
        """PatchResult 应包含 unified diff。"""
        patch = PatchResult(
            file_path="math_utils.py",
            original_snippet=(
                "def factorial(n):\n    return n * factorial(n-1)"
            ),
            patched_snippet=(
                "def factorial(n):\n"
                "    if n < 0: raise ValueError\n"
                "    return n * factorial(n-1)"
            ),
            diff=(
                "@@ -1,2 +1,3 @@\n"
                " def factorial(n):\n"
                "+    if n < 0: raise ValueError\n"
                "     return n * factorial(n-1)"
            ),
            change_description="添加参数校验",
            change_type="modify",
        )
        assert patch.diff.startswith("@@")

    def test_security_result_approval_trigger(self):
        """SecurityResult 有 critical 级别问题时应触发审批。"""
        result = SecurityResult(
            passed=False,
            issues=[
                {
                    "vulnerability_type": "sql_injection",
                    "severity": "critical",
                    "file_path": "db.py",
                    "description": "直接拼接 SQL",
                    "remediation": "使用参数化查询",
                    "cwe_id": "CWE-89",
                }
            ],
            summary="发现严重安全问题",
            requires_approval=True,
        )
        assert result.requires_approval
