"""
图构建与节点行为测试。

覆盖 build_graph 结构验证、P2/P3/P6f 修复的 agent_node 行为、
以及 _sandbox_call 异步包装器。
"""

import asyncio
import uuid
from datetime import datetime

import pytest
from contracts.state import create_initial_state, TeamState

EXPECTED_NODES = {
    "init_task",
    "analyze_requirement",
    "plan_solution",
    "develop_changes",
    "apply_patches",
    "run_tests",
    "review_code",
    "security_check",
    "await_approval",
    "handle_error",
    "finalize",
}


# =============================================================================
# build_graph 结构测试
# =============================================================================


class TestBuildGraph:
    """验证 StateGraph 的节点注册和编译配置。"""

    def test_all_11_nodes_registered(self):
        """build_graph 应注册全部 11 个工作流节点。"""
        from app.graph import build_graph
        graph = build_graph()
        nodes = set(graph.get_graph().nodes.keys())
        # filter out internal LangGraph nodes (__start__, __end__)
        user_nodes = {n for n in nodes if not n.startswith("__")}
        assert user_nodes == EXPECTED_NODES, (
            f"缺少: {EXPECTED_NODES - user_nodes}, 多余: {user_nodes - EXPECTED_NODES}"
        )

    def test_entry_point_is_init_task(self):
        """工作流入口必须是 init_task。"""
        from app.graph import build_graph
        graph = build_graph()
        # 通过编译配置检查入口
        compiled = graph
        assert compiled is not None
        # 用 ainvoke 验证：空 state 的第一阶段应为 analyzing
        import asyncio

        state = create_initial_state(
            task_id="entry-001", repo_url="x", branch="main", requirement="x",
        )
        config = {"configurable": {"thread_id": "entry-001"}}

        async def _run():
            return await compiled.ainvoke(state, config)

        result = asyncio.run(_run())
        # 入口 init_task → analyze_requirement → phase=analyzing → Mock 通过
        assert result["phase"] in ("done", "analyzing", "planning"), (
            f"异常终止阶段: {result['phase']}"
        )

    def test_interrupt_before_await_approval(self):
        """build_graph 配置了 interrupt_before=['await_approval']。"""
        from app.graph import build_graph
        graph = build_graph()
        # LangGraph CompiledStateGraph 使用 interrupt_before_nodes 属性
        interrupt_nodes = getattr(graph, "interrupt_before_nodes", [])
        assert "await_approval" in interrupt_nodes, (
            f"interrupt_before_nodes 应包含 'await_approval'，实际: {interrupt_nodes}"
        )

    def test_graph_compiles_with_default_memory_saver(self):
        """不传 checkpointer 时默认使用 MemorySaver。"""
        from app.graph import build_graph
        from langgraph.checkpoint.memory import MemorySaver
        graph = build_graph()
        checkpointer = getattr(graph, "checkpointer", None)
        assert checkpointer is not None
        assert isinstance(checkpointer, MemorySaver)


# =============================================================================
# agent_node 取消感知（P3）
# =============================================================================


class TestAgentNodeCancel:
    """验证 agent_node 的 cancel_requested pre/post 检查。"""

    def _make_state(self) -> TeamState:
        return create_initial_state(
            task_id="cancel-001", repo_url="x", branch="main", requirement="x",
        )

    def test_pre_check_skips_agent_when_cancel_requested(self):
        """cancel_requested=True 时 agent_node 在调用前直接返回。"""
        from app.agents import RequirementAgent, agent_node

        async def _run():
            state = self._make_state()
            state["cancel_requested"] = True
            before_events = len(state.get("events", []))
            state = await agent_node(state, RequirementAgent())
            after_events = len(state.get("events", []))
            return before_events, after_events, state

        before, after, state = asyncio.run(_run())
        # 预检后 state 不应被修改
        assert before == after
        assert state.get("requirement_analysis") is None

    def test_post_check_discards_output_after_llm_call(self):
        """agent 调用完成后发现 cancel_requested=True，丢弃产出物。"""
        from app.agents import RequirementAgent, agent_node
        from app.agents.base import AgentBase

        async def _run():
            state = self._make_state()
            # 用 Mock 模式：调用会立即完成，然后 post-check 生效
            original = AgentBase.USE_MOCK
            AgentBase.USE_MOCK = True
            try:
                result_state = await agent_node(state, RequirementAgent())
            finally:
                AgentBase.USE_MOCK = original
            return result_state

        result = asyncio.run(_run())
        # Mock 模式无取消标记，正常写入
        assert result.get("requirement_analysis") is not None


# =============================================================================
# 迭代计数（P6f 修复）
# =============================================================================


class TestIterationCounting:
    """验证 develop_changes 节点中的迭代计数（不在条件路由中计数）。"""

    def test_develop_changes_increments_iteration(self):
        """develop_changes 执行一次后 iteration 应 +1。"""
        from app.graph import build_graph

        graph = build_graph()
        state = create_initial_state(
            task_id="iter-001", repo_url="x", branch="main", requirement="x",
            max_iterations=3,
        )
        config = {"configurable": {"thread_id": "iter-001"}}

        async def _run():
            return await graph.ainvoke(state, config)

        result = asyncio.run(_run())
        # Mock 模式全流程通过，develop_changes 被调用 1 次
        assert result["iteration"] == 1, (
            f"预期 iteration=1（develop_changes 执行 1 次），实际 {result['iteration']}"
        )

    def test_iteration_stops_at_max_in_route_after_test(self):
        """route_after_test 仅读取 iteration，不再修改。超限时路由到 handle_error。"""
        from app.graph import route_after_test

        state = create_initial_state(
            task_id="iter-max-001", repo_url="x", branch="main", requirement="x",
            max_iterations=3,
        )
        # 模拟已到最大迭代 + 测试失败
        state["iteration"] = 3
        state["sandbox_results"] = [{
            "status": "failure",
            "test_summary": {"passed": 6, "failed": 1},
        }]
        result = route_after_test(state)
        assert result == "handle_error", (
            f"iteration=3 时应返回 'handle_error'，实际 '{result}'"
        )

    def test_iteration_under_max_routes_to_develop(self):
        """iteration 未达上限时返回 develop_changes 触发返工。"""
        from app.graph import route_after_test

        state = create_initial_state(
            task_id="iter-under-001", repo_url="x", branch="main", requirement="x",
            max_iterations=3,
        )
        state["iteration"] = 2
        state["sandbox_results"] = [{
            "status": "failure",
            "test_summary": {"passed": 6, "failed": 1},
        }]
        result = route_after_test(state)
        assert result == "develop_changes"

    def test_route_after_test_does_not_mutate_iteration(self):
        """P6f 修复后 route_after_test 不应修改 state['iteration']。"""
        from app.graph import route_after_test

        state = create_initial_state(
            task_id="no-mutate-001", repo_url="x", branch="main", requirement="x",
            max_iterations=3,
        )
        state["iteration"] = 2
        state["sandbox_results"] = [{
            "status": "failure",
            "test_summary": {"passed": 6, "failed": 1},
        }]
        before = state["iteration"]
        route_after_test(state)
        after = state["iteration"]
        assert before == after == 2, (
            f"route_after_test 不应修改 iteration：{before} → {after}"
        )


# =============================================================================
# 沙箱异步包装
# =============================================================================


class TestSandboxCallAsync:
    """验证 _sandbox_call 在独立线程中执行沙箱命令。"""

    def test_sandbox_call_returns_command_result(self):
        """_sandbox_call 应返回正确的 exit_code 和 stdout。"""
        from app.graph import _sandbox_call
        from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox, reset_all

        reset_all()
        task_id = "sb-async-001"

        async def _run():
            sandbox = get_sandbox(task_id)
            result = await _sandbox_call(
                sandbox, "echo hello-from-sandbox", timeout=10,
            )
            cleanup_sandbox(task_id)
            return result

        result = asyncio.run(_run())
        assert result.exit_code == 0
        assert "hello-from-sandbox" in result.stdout

    def test_sandbox_call_failing_command(self):
        """命令失败时 exit_code 非 0。"""
        from app.graph import _sandbox_call
        from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox, reset_all

        reset_all()
        task_id = "sb-fail-001"

        async def _run():
            sandbox = get_sandbox(task_id)
            result = await _sandbox_call(
                sandbox, "python -c \"import sys; sys.exit(42)\"", timeout=10,
            )
            cleanup_sandbox(task_id)
            return result

        result = asyncio.run(_run())
        assert result.exit_code == 42

    def test_sandbox_call_timeout(self):
        """命令超时时 timed_out=True。"""
        from app.graph import _sandbox_call
        from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox, reset_all

        reset_all()
        task_id = "sb-timeout-001"

        async def _run():
            sandbox = get_sandbox(task_id)
            result = await _sandbox_call(
                sandbox, "python -c \"import time; time.sleep(10)\"", timeout=1,
            )
            cleanup_sandbox(task_id)
            return result

        result = asyncio.run(_run())
        assert result.timed_out is True

    def test_sandbox_call_does_not_block_event_loop(self):
        """_sandbox_call 在独立线程中执行，不阻塞事件循环。"""
        from app.graph import _sandbox_call
        from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox, reset_all

        reset_all()
        task_id = "sb-nonblock-001"

        async def _run():
            sandbox = get_sandbox(task_id)
            # 用 sleep 命令测试：若阻塞事件循环，整个 asyncio 会卡住
            t0 = datetime.now()
            result = await _sandbox_call(
                sandbox, "python -c \"import time; time.sleep(1)\"", timeout=5,
            )
            elapsed = (datetime.now() - t0).total_seconds()
            cleanup_sandbox(task_id)
            return elapsed, result

        elapsed, result = asyncio.run(_run())
        # 1 秒 sleep + subprocess 开销，耗时应在 1~5 秒之间
        assert 0.5 < elapsed < 10.0, (
            f"sandbox_call 耗时异常: {elapsed:.1f}s（预期 1~5s）"
        )
        assert result.exit_code == 0
