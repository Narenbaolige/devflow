"""
LangGraph 工作流定义。

DevFlow 的核心编排引擎。定义所有节点、条件边和 Checkpointer。
"""

import uuid
from datetime import datetime
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from contracts.state import TeamState


def _record_event(state: TeamState, event_type: str, message: str, node_name: str) -> None:
    """在状态中记录可被 API/SSE 消费的轻量事件。"""
    state.setdefault("events", []).append({
        "event_id": str(uuid.uuid4()),
        "task_id": state["task_meta"]["task_id"],
        "event_type": event_type,
        "node_name": node_name,
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "data": {"phase": state.get("phase")},
    })
    state["current_node"] = node_name


def _cancelled(state: TeamState, node_name: str) -> bool:
    """节点边界的协作式取消检查，避免取消后继续产生副作用。"""
    if state.get("cancel_requested", False):
        state["phase"] = "cancelled"
        _record_event(state, "progress", "任务已取消，跳过后续节点", node_name)
        return True
    return False

# =============================================================================
# 节点实现（Day 1-2: 先用 Mock，Day 3-5: 替换为真实调用）
# =============================================================================


async def init_task(state: TeamState) -> TeamState:
    """初始化任务节点。记录任务开始。"""
    state["phase"] = "analyzing"
    _record_event(state, "node_complete", "任务已初始化", "init_task")
    return state


async def analyze_requirement(state: TeamState) -> TeamState:
    """需求分析节点 → 调用 Requirement Agent [B]"""
    if _cancelled(state, "analyze_requirement"):
        return state
    from app.agents import RequirementAgent, agent_node

    state["phase"] = "analyzing"
    state = await agent_node(state, RequirementAgent())
    state["phase"] = "planning"
    _record_event(state, "node_complete", "需求分析完成", "analyze_requirement")
    return state


async def plan_solution(state: TeamState) -> TeamState:
    """方案规划节点 → 调用 Planner Agent [B]"""
    if _cancelled(state, "plan_solution"):
        return state
    from app.agents import PlannerAgent, agent_node

    state["phase"] = "planning"
    state = await agent_node(state, PlannerAgent())
    state["phase"] = "developing"
    _record_event(state, "node_complete", "方案规划完成", "plan_solution")
    return state


async def develop_changes(state: TeamState) -> TeamState:
    """代码开发节点 → 调用 Developer Agent [B]"""
    if _cancelled(state, "develop_changes"):
        return state
    from app.agents import DeveloperAgent, agent_node

    state["phase"] = "developing"
    state = await agent_node(state, DeveloperAgent())
    state["phase"] = "testing"
    _record_event(state, "node_complete", "代码修改完成", "develop_changes")
    return state


async def apply_patches(state: TeamState) -> TeamState:
    """应用 Patch 节点 → 沙箱操作 [C]"""
    if _cancelled(state, "apply_patches"):
        return state
    # TODO Day 3: 由 C 的沙箱模块提供 clone + apply patches 实现。
    state["phase"] = "testing"
    _record_event(state, "node_complete", "Patch 应用步骤完成", "apply_patches")
    return state


async def run_tests(state: TeamState) -> TeamState:
    """测试执行节点 → 沙箱操作 [C]"""
    # TODO Day 3: 切换为 Agent 驱动的沙箱调用。
    #
    # 沙箱只提供 execute(command)，Agent 决定测试策略：
    #   sandbox = create_sandbox()
    #   sandbox.execute("git clone --depth 1 --branch main URL repo")
    #   sandbox.execute("pip install -e .", cwd="repo", timeout=180)
    #   r = sandbox.execute("python -m pytest -v", cwd="repo")
    #   # Agent 自行解读 r.stdout，决定下一步
    #   # 遇到 C++ 项目就调 MSBuild，遇到 Rust 就调 cargo test

    if _cancelled(state, "run_tests"):
        return state
    from contracts.sandbox_result import SandboxResult, TestSummary

    state["sandbox_results"].append(
        SandboxResult(
            execution_id=str(uuid.uuid4()),
            task_id=state["task_meta"]["task_id"],
            sandbox_type="test",
            status="success",
            exit_code=0,
            timed_out=False,
            duration_ms=1500,
            test_summary=TestSummary(total=10, passed=10, failed=0),
            started_at=datetime.now().isoformat(),
            finished_at=datetime.now().isoformat(),
        ).model_dump()
    )
    state["phase"] = "reviewing"
    _record_event(state, "test_result", "测试执行完成", "run_tests")
    return state


async def review_code(state: TeamState) -> TeamState:
    """代码审查节点 → 调用 Reviewer Agent [B]"""
    if _cancelled(state, "review_code"):
        return state
    from app.agents import ReviewerAgent, agent_node

    state["phase"] = "reviewing"
    state = await agent_node(state, ReviewerAgent())
    state["phase"] = "security_check"
    _record_event(state, "node_complete", "代码审查完成", "review_code")
    return state


async def security_check(state: TeamState) -> TeamState:
    """安全审查节点 → 调用 Security Agent [B]（两周版：集成入 Reviewer）"""
    if _cancelled(state, "security_check"):
        return state
    from contracts.agent_result import AgentResult, AgentRole

    state["phase"] = "security_check"
    state["security_review"] = AgentResult(
        agent_role=AgentRole.SECURITY,
        success=True,
        result={
            "passed": True,
            "issues": [],
            "summary": "Mock: 安全审查通过",
            "requires_approval": False,
        },
        reasoning="Mock: 安全审查完成",
    ).model_dump()

    # 判断是否需要审批
    if state["security_review"].get("result", {}).get("requires_approval", False):
        state["approval_required"] = True
        state["phase"] = "awaiting_approval"
        _record_event(state, "approval_required", "任务等待人工审批", "security_check")
    else:
        state["phase"] = "done"
        _record_event(state, "node_complete", "安全审查完成", "security_check")
    return state


async def await_approval(state: TeamState) -> TeamState:
    """人工审批恢复点。图在本节点之前中断，由 approve/reject API 恢复。"""
    if _cancelled(state, "await_approval"):
        return state
    if state.get("approval_granted"):
        state["approval_required"] = False
        state["phase"] = "done"
        _record_event(state, "progress", "审批已通过", "await_approval")
    else:
        state["iteration"] = state.get("iteration", 0) + 1
        state["approval_required"] = False
        state["phase"] = "developing"
        _record_event(state, "progress", "审批被拒绝，开始返工", "await_approval")
    return state


async def handle_error(state: TeamState) -> TeamState:
    """错误处理节点 → 分类 + 重试决策 [A]"""
    if state.get("phase") == "cancelled":
        return state
    state["errors"].append({
        "node": "unknown",
        "error_type": "unknown",
        "message": "Mock error handler",
        "timestamp": datetime.now().isoformat(),
        "recoverable": False,
        "retry_count": 0,
    })
    if state["iteration"] >= state["max_iterations"]:
        state["phase"] = "failed"
    else:
        state["iteration"] = state.get("iteration", 0) + 1
        state["phase"] = "developing"  # 返工
    _record_event(state, "error", "工作流发生错误", "handle_error")
    return state


async def finalize(state: TeamState) -> TeamState:
    """完成节点 → 汇总结果 [A]"""
    if not state.get("cancel_requested", False):
        state["phase"] = "done"
        _record_event(state, "task_complete", "任务已完成", "finalize")
    return state


# =============================================================================
# 条件路由
# =============================================================================

AnalyzeRoute = Literal["plan_solution", "await_approval", "handle_error"]


def route_after_analyze(state: TeamState) -> AnalyzeRoute:
    """需求分析后的路由。"""
    req = state.get("requirement_analysis")
    if req is None:
        return "handle_error"
    result = req.get("result", {})
    if result.get("confidence", 0) < 0.6:
        return "await_approval"
    return "plan_solution"


def route_after_test(state: TeamState) -> Literal["review_code", "develop_changes", "handle_error"]:
    """测试后的路由：全部通过 → 审查，失败 → 返工，超迭代 → 错误。"""
    if state.get("cancel_requested"):
        return "handle_error"
    results = state.get("sandbox_results", [])
    if not results:
        return "handle_error"
    last = results[-1]
    if last.get("status") == "success" and last.get("test_summary", {}).get("failed", 0) == 0:
        return "review_code"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    # 条件边是返工的唯一入口；在此处计数，避免测试失败时无限循环。
    state["iteration"] = state.get("iteration", 0) + 1
    _record_event(state, "progress", "测试失败，进入返工", "run_tests")
    return "develop_changes"


ReviewRoute = Literal["security_check", "develop_changes", "handle_error"]


def route_after_review(state: TeamState) -> ReviewRoute:
    """审查后的路由。"""
    if state.get("cancel_requested"):
        return "handle_error"
    review = state.get("review", {})
    if review.get("result", {}).get("passed", False):
        return "security_check"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    state["iteration"] = state.get("iteration", 0) + 1
    _record_event(state, "progress", "审查未通过，进入返工", "review_code")
    return "develop_changes"


def route_after_security(state: TeamState) -> Literal["done", "await_approval"]:
    """安全审查后的路由。"""
    if state.get("cancel_requested"):
        return "done"
    sec = state.get("security_review", {})
    if sec.get("result", {}).get("requires_approval", False):
        return "await_approval"
    return "done"


# =============================================================================
# 构建 StateGraph
# =============================================================================

def build_graph(checkpointer=None):
    """
    构建 DevFlow LangGraph 工作流。

    Args:
        checkpointer: LangGraph Checkpointer 实例。
                      开发期用 MemorySaver()，
                      生产期用 SqliteSaver / PostgresSaver。
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(TeamState)

    # --- 注册节点 ---
    builder.add_node("init_task", init_task)
    builder.add_node("analyze_requirement", analyze_requirement)
    builder.add_node("plan_solution", plan_solution)
    builder.add_node("develop_changes", develop_changes)
    builder.add_node("apply_patches", apply_patches)
    builder.add_node("run_tests", run_tests)
    builder.add_node("review_code", review_code)
    builder.add_node("security_check", security_check)
    builder.add_node("await_approval", await_approval)
    builder.add_node("handle_error", handle_error)
    builder.add_node("finalize", finalize)

    # --- 注册边 ---
    builder.set_entry_point("init_task")
    builder.add_edge("init_task", "analyze_requirement")

    # 条件路由
    builder.add_conditional_edges(
        "analyze_requirement",
        route_after_analyze,
        {
            "plan_solution": "plan_solution",
            "await_approval": "await_approval",
            "handle_error": "handle_error",
        },
    )
    builder.add_edge("plan_solution", "develop_changes")
    builder.add_edge("develop_changes", "apply_patches")
    builder.add_edge("apply_patches", "run_tests")

    builder.add_conditional_edges(
        "run_tests",
        route_after_test,
        {
            "review_code": "review_code",
            "develop_changes": "develop_changes",
            "handle_error": "handle_error",
        },
    )

    builder.add_conditional_edges(
        "review_code",
        route_after_review,
        {
            "security_check": "security_check",
            "develop_changes": "develop_changes",
            "handle_error": "handle_error",
        },
    )

    builder.add_conditional_edges(
        "security_check",
        route_after_security,
        {
            "done": "finalize",
            "await_approval": "await_approval",
        },
    )

    # 终端节点
    builder.add_conditional_edges(
        "await_approval",
        lambda state: "finalize" if state.get("approval_granted") else "develop_changes",
        {"finalize": "finalize", "develop_changes": "develop_changes"},
    )
    builder.add_edge("finalize", END)
    builder.add_edge("handle_error", END)

    # 在审批节点执行前停止。API 用 aupdate_state + ainvoke(None) 从此处恢复。
    return builder.compile(checkpointer=checkpointer, interrupt_before=["await_approval"])


# =============================================================================
# 全局图实例（模块加载时编译）
# =============================================================================

graph = build_graph()
