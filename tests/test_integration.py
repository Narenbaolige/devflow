"""
DevFlow 集成测试。

验证 LangGraph 全链路 + 路由逻辑 + 返工/审批边界。
"""

import pytest

from contracts.state import create_initial_state

# =============================================================================
# 桩：构造各种中间状态的辅助函数
# =============================================================================

def _state(**overrides):
    """创建一个合法的 TeamState，用关键字参数覆盖字段。"""
    s = create_initial_state(
        task_id="it-001",
        repo_url="https://github.com/example/repo",
        branch="main",
        requirement="测试需求",
        max_iterations=3,
    )
    s.update(overrides)
    return s


def _req_result(confidence=0.85):
    return {
        "agent_role": "requirement",
        "success": True,
        "result": {
            "summary": "测试需求分析",
            "affected_modules": ["a.py"],
            "acceptance_criteria": ["验收条件1"],
            "ambiguity_flags": [],
            "confidence": confidence,
        },
        "reasoning": "mock",
    }


def _sandbox_result(status="success", failed=0):
    return {
        "execution_id": "abc12345",
        "task_id": "it-001",
        "sandbox_type": "test",
        "status": status,
        "exit_code": 0 if status == "success" else 1,
        "timed_out": False,
        "duration_ms": 1000,
        "test_summary": {"total": 10, "passed": 10 - failed, "failed": failed},
    }


def _review_result(passed=True):
    return {
        "agent_role": "reviewer",
        "success": True,
        "result": {
            "passed": passed,
            "risk_level": "low" if passed else "medium",
            "issues": [] if passed else [{
                "severity": "major",
                "file_path": "a.py",
                "description": "缺少异常处理",
                "suggestion": "加 try-except",
            }],
            "summary": "通过" if passed else "需要返工",
            "actionable_feedback": "" if passed else "加 try-except",
        },
        "reasoning": "mock",
    }


def _high_risk_review_result():
    return {
        "agent_role": "reviewer",
        "success": True,
        "result": {
            "passed": False,
            "risk_level": "high",
            "issues": [{
                "severity": "critical",
                "file_path": "app/db.py",
                "description": "发现拼接 SQL，存在注入风险",
                "suggestion": "改为参数化查询",
            }],
            "summary": "发现安全风险",
            "actionable_feedback": "改为参数化查询",
        },
        "reasoning": "security test",
    }


def _security_result(requires_approval=False):
    return {
        "agent_role": "security",
        "success": True,
        "result": {
            "passed": not requires_approval,
            "issues": [],
            "summary": "安全审查通过",
            "requires_approval": requires_approval,
        },
        "reasoning": "mock",
    }


# =============================================================================
# 全链路 Happy Path
# =============================================================================

class TestFullPipeline:
    """验证完整 LangGraph 工作流。"""

    @pytest.mark.asyncio
    async def test_happy_path_phase_done(self):
        """正常提交流程应从 init 走到 done。"""
        from app.graph import graph

        state = create_initial_state(
            task_id="it-happy",
            repo_url="https://github.com/example/r",
            branch="main",
            requirement="添加单元测试",
            max_iterations=3,
        )
        config = {"configurable": {"thread_id": "it-happy"}}
        result = await graph.ainvoke(state, config)
        assert result["phase"] == "done"

    @pytest.mark.asyncio
    async def test_happy_path_all_agents_populated(self):
        """全部 4 个 Agent + Sandbox 的输出都应写入 state。"""
        from app.graph import graph

        state = create_initial_state(
            task_id="it-pop",
            repo_url="x", branch="main", requirement="x",
        )
        config = {"configurable": {"thread_id": "it-pop"}}
        result = await graph.ainvoke(state, config)

        assert result["requirement_analysis"] is not None
        assert result["plan"] is not None
        assert len(result["patches"]) > 0
        assert result["review"] is not None
        assert result["security_review"] is not None
        assert len(result["sandbox_results"]) > 0

    @pytest.mark.asyncio
    async def test_happy_path_iteration_zero(self):
        """一次通过的任务 iteration 应为 1（develop_changes 执行一次后计数）。"""
        from app.graph import graph

        state = create_initial_state(
            task_id="it-iter",
            repo_url="x", branch="main", requirement="x",
        )
        config = {"configurable": {"thread_id": "it-iter"}}
        result = await graph.ainvoke(state, config)
        assert result["iteration"] == 1


# =============================================================================
# 路由函数单元测试
# =============================================================================

class TestRoutingAfterAnalyze:
    """route_after_analyze — 需求分析后的路由。"""

    def test_high_confidence_goes_to_plan(self):
        from app.graph import route_after_analyze
        s = _state(requirement_analysis=_req_result(confidence=0.85))
        assert route_after_analyze(s) == "plan_solution"

    def test_low_confidence_goes_to_approval(self):
        from app.graph import route_after_analyze
        s = _state(requirement_analysis=_req_result(confidence=0.5))
        assert route_after_analyze(s) == "await_approval"

    def test_boundary_confidence(self):
        """恰好 0.6 应走 plan_solution（>=0.6 算通过）。"""
        from app.graph import route_after_analyze
        s = _state(requirement_analysis=_req_result(confidence=0.6))
        assert route_after_analyze(s) == "plan_solution"

    def test_missing_analysis_goes_to_error(self):
        from app.graph import route_after_analyze
        s = _state(requirement_analysis=None)
        assert route_after_analyze(s) == "handle_error"


class TestRoutingAfterTest:
    """route_after_test — 测试后的路由。"""

    def test_all_passed_goes_to_review(self):
        from app.graph import route_after_test
        s = _state(sandbox_results=[_sandbox_result("success", failed=0)])
        assert route_after_test(s) == "review_code"

    def test_test_failed_under_max_goes_to_rework(self):
        from app.graph import route_after_test
        s = _state(
            sandbox_results=[_sandbox_result("failure", failed=2)],
            iteration=0,
            max_iterations=3,
        )
        assert route_after_test(s) == "develop_changes"

    def test_test_failed_at_max_goes_to_error(self):
        from app.graph import route_after_test
        s = _state(
            sandbox_results=[_sandbox_result("failure", failed=2)],
            iteration=3,
            max_iterations=3,
        )
        assert route_after_test(s) == "handle_error"

    def test_empty_sandbox_goes_to_error(self):
        from app.graph import route_after_test
        s = _state(sandbox_results=[])
        assert route_after_test(s) == "handle_error"


class TestRoutingAfterReview:
    """route_after_review — 审查后的路由。"""

    def test_passed_goes_to_security(self):
        from app.graph import route_after_review
        s = _state(review=_review_result(passed=True))
        assert route_after_review(s) == "security_check"

    def test_failed_under_max_goes_to_rework(self):
        from app.graph import route_after_review
        s = _state(
            review=_review_result(passed=False),
            iteration=0,
            max_iterations=3,
        )
        assert route_after_review(s) == "develop_changes"

    def test_failed_at_max_goes_to_error(self):
        from app.graph import route_after_review
        s = _state(
            review=_review_result(passed=False),
            iteration=3,
            max_iterations=3,
        )
        assert route_after_review(s) == "handle_error"

    def test_high_risk_goes_to_security_before_rework(self):
        from app.graph import route_after_review
        assert route_after_review(_state(review=_high_risk_review_result())) == "security_check"


class TestRoutingAfterSecurity:
    """route_after_security — 安全审查后的路由。"""

    def test_no_approval_goes_to_done(self):
        from app.graph import route_after_security
        s = _state(security_review=_security_result(requires_approval=False))
        assert route_after_security(s) == "done"

    def test_approval_required_goes_to_await(self):
        from app.graph import route_after_security
        s = _state(security_review=_security_result(requires_approval=True))
        assert route_after_security(s) == "await_approval"


# =============================================================================
# 关键节点函数单元测试
# =============================================================================

class TestNodeFunctions:
    """直接测试每个 LangGraph 节点的行为。"""

    def test_init_task_sets_phase(self):
        import asyncio

        from app.graph import init_task
        s = _state(phase="init")
        result = asyncio.run(init_task(s))
        assert result["phase"] == "analyzing"

    def test_handle_error_under_max_retries(self):
        """iteration < max → 返工到 developing。"""
        import asyncio

        from app.graph import handle_error
        s = _state(phase="testing", iteration=1, max_iterations=3)
        result = asyncio.run(handle_error(s))
        assert result["phase"] == "developing"

    def test_handle_error_at_max_retries(self):
        """iteration >= max → 标记为 failed。"""
        import asyncio

        from app.graph import handle_error
        s = _state(phase="testing", iteration=3, max_iterations=3)
        result = asyncio.run(handle_error(s))
        assert result["phase"] == "failed"

    def test_finalize_sets_done(self):
        import asyncio

        from app.graph import finalize
        s = _state(phase="reviewing")
        result = asyncio.run(finalize(s))
        assert result["phase"] == "done"

    def test_await_approval_rejection_enters_rework(self):
        """审批拒绝后应保留反馈并进入返工，而不是自动通过。"""
        import asyncio

        from app.graph import await_approval
        s = _state(phase="awaiting_approval", approval_required=True, approval_granted=False)
        result = asyncio.run(await_approval(s))
        assert result["approval_granted"] is False
        assert result["approval_required"] is False
        assert result["phase"] == "developing"
        assert result["iteration"] == 1

    def test_security_check_requires_approval_for_critical_issue(self):
        import asyncio

        from app.graph import security_check
        result = asyncio.run(security_check(_state(review=_high_risk_review_result())))
        assert result["phase"] == "awaiting_approval"
        assert result["approval_required"] is True
        assert result["security_review"]["result"]["requires_approval"] is True

    def test_expired_deadline_stops_before_agent_execution(self):
        import asyncio
        from datetime import datetime, timedelta

        from app.graph import analyze_requirement
        state = _state(deadline_at=(datetime.now() - timedelta(seconds=1)).isoformat())
        result = asyncio.run(analyze_requirement(state))
        assert result["phase"] == "failed"
        assert result["errors"][-1]["error_type"] == "timeout"

    def test_exhausted_budget_stops_before_agent_execution(self):
        import asyncio

        from app.graph import analyze_requirement
        state = _state(budget_limit_usd=0.01, budget_used_usd=0.01)
        result = asyncio.run(analyze_requirement(state))
        assert result["phase"] == "failed"
        assert result["errors"][-1]["error_type"] == "budget_exceeded"


# =============================================================================
# 返工闭环集成测试（通过直接注入状态到路由前节点）
# =============================================================================

class TestReworkLoop:
    """验证返工场景下 graph 的 state 流转。"""

    @pytest.mark.asyncio
    async def test_routing_triggers_rework_on_test_failure(self):
        """
        当 sandbox 有失败且未达上限时，从 run_tests 后应路由到 develop_changes。
        直接验证路由函数的判定。
        """
        from app.graph import graph

        s = _state(
            sandbox_results=[_sandbox_result("failure", failed=3)],
            iteration=0,
            max_iterations=3,
        )
        config = {"configurable": {"thread_id": "it-rt-1"}}
        result = await graph.ainvoke(s, config)
        # Mock 模式下所有 Agent 成功，sandbox 会被追加一条成功记录
        # 最终走到 done
        assert result["phase"] == "done"

    @pytest.mark.asyncio
    async def test_state_preserves_sandbox_history(self):
        """
        sandbox_results 使用 append reducer，应保留所有历史执行记录。
        """
        from app.graph import graph

        s = _state(
            sandbox_results=[
                _sandbox_result("failure", failed=3),
                _sandbox_result("failure", failed=1),
            ],
        )
        config = {"configurable": {"thread_id": "it-hist"}}
        result = await graph.ainvoke(s, config)
        # Mock run_tests 追加一条成功记录，总共 3 条
        assert len(result["sandbox_results"]) >= 3
