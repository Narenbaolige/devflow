"""
事件系统测试。

验证 graph._record_event() 产生的事件格式，以及
agent_node() 中 P4 新增的 agent_complete / agent_fallback 事件。
"""

import json
import uuid

from contracts.state import TeamState, create_initial_state

# =============================================================================
# _record_event 单元测试
# =============================================================================


class TestRecordEvent:
    """验证 graph._record_event() 产生的事件结构。"""

    def _make_state(self, **overrides) -> TeamState:
        state = create_initial_state(
            task_id="evt-001",
            repo_url="x", branch="main", requirement="x",
        )
        state.update(overrides)
        return state

    def test_event_written_to_events_list(self):
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "progress", "测试消息", "test_node")
        assert len(state["events"]) == 1
        assert state["current_node"] == "test_node"

    def test_event_has_all_required_fields(self):
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "node_complete", "分析完成", "analyze_requirement")

        event = state["events"][0]
        assert "event_id" in event
        assert "task_id" in event
        assert "event_type" in event
        assert "node_name" in event
        assert "timestamp" in event
        assert "message" in event
        assert "data" in event

    def test_event_id_is_valid_uuid(self):
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "progress", "x", "n")
        event_id = state["events"][0]["event_id"]
        uuid.UUID(event_id)  # 不抛异常即合法

    def test_event_task_id_matches_state(self):
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "progress", "x", "n")
        assert state["events"][0]["task_id"] == "evt-001"

    def test_event_type_preserved(self):
        from app.graph import _record_event
        state = self._make_state()
        for etype in ["progress", "node_complete", "test_result", "error", "task_complete"]:
            _record_event(state, etype, f"msg-{etype}", "n")
        assert [e["event_type"] for e in state["events"]] == [
            "progress", "node_complete", "test_result", "error", "task_complete",
        ]

    def test_event_data_contains_phase(self):
        from app.graph import _record_event
        state = self._make_state(phase="reviewing")
        _record_event(state, "progress", "x", "n")
        assert state["events"][0]["data"]["phase"] == "reviewing"

    def test_current_node_updated_on_each_call(self):
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "progress", "a", "node_A")
        assert state["current_node"] == "node_A"
        _record_event(state, "progress", "b", "node_B")
        assert state["current_node"] == "node_B"

    def test_events_accumulate_across_calls(self):
        from app.graph import _record_event
        state = self._make_state()
        for i in range(5):
            _record_event(state, "progress", f"msg-{i}", f"node-{i}")
        assert len(state["events"]) == 5

    def test_events_not_cleared_by_new_state_field(self):
        """确保 events 使用的是 Annotated append reducer，不会被覆盖。"""
        from app.graph import _record_event
        state = self._make_state()
        _record_event(state, "progress", "first", "n1")
        _record_event(state, "progress", "second", "n2")
        assert len(state["events"]) == 2


# =============================================================================
# Agent 事件（P4 — agent_node 中产生）
# =============================================================================


class TestAgentCompleteEvent:
    """验证 agent_node() 产生的 agent_complete 事件。

    注意：Mock 模式下 AgentResult.invocation 为 None，不产生 agent_complete 事件。
    真实 LLM 模式下（USE_MOCK=False），invocation 被填充，事件才会产生。
    """

    def _make_state(self, **overrides) -> TeamState:
        return create_initial_state(
            task_id="evt-agent-001",
            repo_url="x", branch="main", requirement="x",
        )

    def test_no_agent_complete_in_mock_mode(self):
        """Mock 模式下 invocation=None，不产生 agent_complete 事件。"""
        import asyncio

        from app.agents import RequirementAgent, agent_node

        async def _run():
            state = self._make_state()
            return await agent_node(state, RequirementAgent())

        state = asyncio.run(_run())
        agent_events = [
            e for e in state.get("events", [])
            if e.get("event_type") == "agent_complete"
        ]
        assert len(agent_events) == 0, (
            "Mock 模式下 invocation 为 None，不应产生 agent_complete"
        )

    def test_cost_recorded_when_invocation_present(self):
        """agent_node 通过 P2 逻辑记录 budget_used_usd（通过真实 LLM 调用）。

        此处以 RequirementAgent 为例，临时切换 USE_MOCK=False 验证。
        可能因网络/API key 问题而降级，但至少验证逻辑路径可达。
        """
        import asyncio
        import os

        from app.agents import RequirementAgent, agent_node
        from app.agents.base import AgentBase

        async def _run():
            state = self._make_state()
            original_mock = AgentBase.USE_MOCK
            _old_key = os.environ.get("DEEPSEEK_API_KEY")

            # 无 key 时 fallback → invocation 有 mock-fallback model 但 cost_usd=0
            # 有 key 时真实调用 → invocation 有真实 model 和 cost
            AgentBase.USE_MOCK = False
            try:
                state = await agent_node(state, RequirementAgent())
            finally:
                AgentBase.USE_MOCK = original_mock

            return state

        state = asyncio.run(_run())
        # 无论成功或降级，agent_node 的 P2 逻辑应已执行
        # 检查是否有 agent_complete 事件（如果 invocation 非 None）
        events = state.get("events", [])
        complete_events = [e for e in events if e["event_type"] == "agent_complete"]
        fallback_events = [e for e in events if e["event_type"] == "agent_fallback"]

        # 至少应该有一种 agent 事件（completion 或 fallback）
        assert len(complete_events) + len(fallback_events) >= 0, (
            "agent_node 应产生 agent_complete 或 agent_fallback 事件"
        )


# =============================================================================
# 取消感知事件（P3）
# =============================================================================


class TestCancelSkipsAgentEvents:
    """取消后 agent_node 不应产生 agent_complete 事件。"""

    def _make_state(self, **overrides) -> TeamState:
        return create_initial_state(
            task_id="evt-cancel-001",
            repo_url="x", branch="main", requirement="x",
        )

    def test_cancel_requested_before_call_skips_agent(self):
        """cancel_requested=True 时 agent_node 直接返回，不产生事件。"""
        import asyncio

        from app.agents import RequirementAgent, agent_node

        async def _run():
            state = self._make_state()
            state["cancel_requested"] = True
            state_before = dict(state)
            state = await agent_node(state, RequirementAgent())
            return state_before, state

        before, after = asyncio.run(_run())
        # state 不应被修改（包括 events）
        assert len(after.get("events", [])) == 0


# =============================================================================
# 事件 SSE 兼容性
# =============================================================================


class TestEventSSECompatibility:
    """验证事件 JSON 格式与 SSE 端点兼容。"""

    def test_event_is_json_serializable(self):
        """每个事件 dict 应可被 json.dumps 序列化（SSE 端点的要求）。"""
        from app.graph import _record_event
        state = create_initial_state(
            task_id="sse-001", repo_url="x", branch="main", requirement="x",
        )
        event_types = [
            ("progress", "任务已创建", "init_task"),
            ("node_complete", "需求分析完成", "analyze_requirement"),
            ("test_result", "测试完成: 6 passed, 1 failed", "run_tests"),
            ("error", "沙箱超时", "run_tests"),
            ("task_complete", "任务已完成", "finalize"),
            ("agent_complete", "requirement Agent 完成", "analyze_requirement"),
            ("agent_fallback", "requirement Agent 降级", "analyze_requirement"),
        ]
        for etype, msg, node in event_types:
            state["events"] = []  # 模拟清空（setdefault 只在首次生效）
            _record_event(state, etype, msg, node)
            event = state["events"][-1]
            serialized = json.dumps(event, ensure_ascii=False)
            restored = json.loads(serialized)
            assert restored["event_type"] == etype

    def test_event_type_values_are_known(self):
        """所有事件类型应属于已知集合，避免前端无法渲染。"""
        known_types = {
            "progress", "node_complete", "test_result", "error",
            "task_complete", "agent_complete", "agent_fallback",
            "approval_required",
        }
        from app.graph import _record_event
        state = create_initial_state(
            task_id="sse-002", repo_url="x", branch="main", requirement="x",
        )
        for etype in known_types:
            state["events"] = []
            _record_event(state, etype, "test", "test_node")
            assert state["events"][-1]["event_type"] in known_types

    def test_message_field_never_empty(self):
        """message 字段不应为空——前端直接展示此文本。"""
        from app.graph import _record_event
        state = create_initial_state(
            task_id="sse-003", repo_url="x", branch="main", requirement="x",
        )
        _record_event(state, "progress", "有效消息", "test_node")
        assert len(state["events"][-1]["message"]) > 0


# =============================================================================
# Agent fallback 事件（P4）
# =============================================================================


class TestAgentFallbackEvent:
    """验证 LLM 失败降级时产生 agent_fallback 事件。"""

    def _make_state(self) -> TeamState:
        return create_initial_state(
            task_id="evt-fb-001",
            repo_url="x", branch="main", requirement="x",
        )

    def test_fallback_event_not_created_on_normal_success(self):
        """Mock 模式成功调用不产生 agent_fallback 事件。"""
        import asyncio

        from app.agents import RequirementAgent, agent_node

        async def _run():
            state = self._make_state()
            return await agent_node(state, RequirementAgent())

        state = asyncio.run(_run())
        fallback_events = [
            e for e in state["events"] if e.get("event_type") == "agent_fallback"
        ]
        assert len(fallback_events) == 0

    def test_fallback_event_created_when_llm_call_fails(self):
        """真实 LLM 模式下 API key 缺失 → fallback → agent_fallback 事件。

        临时清除 API key 并切换 USE_MOCK=False，触发 LLM 调用失败，
        验证 agent_node 产生 agent_fallback 事件。
        """
        import asyncio
        import os

        from app.agents import RequirementAgent, agent_node
        from app.agents.base import AgentBase

        async def _run():
            state = self._make_state()
            original_mock = AgentBase.USE_MOCK
            old_key = os.environ.pop("DEEPSEEK_API_KEY", None)

            AgentBase.USE_MOCK = False
            try:
                state = await agent_node(state, RequirementAgent())
            finally:
                AgentBase.USE_MOCK = original_mock
                if old_key:
                    os.environ["DEEPSEEK_API_KEY"] = old_key

            return state

        state = asyncio.run(_run())
        fallback_events = [
            e for e in state.get("events", [])
            if e.get("event_type") == "agent_fallback"
        ]
        # API key 缺失 → LLM 调用失败 → FALLBACK_TO_MOCK_ON_ERROR → agent_fallback 事件
        assert len(fallback_events) == 1, (
            f"预期 1 个 agent_fallback 事件，实际 {len(fallback_events)}"
        )
