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

# =============================================================================
# 节点实现（Day 1-2: 先用 Mock，Day 3-5: 替换为真实调用）
# =============================================================================


async def init_task(state: TeamState) -> TeamState:
    """初始化任务节点。记录任务开始。"""
    state["phase"] = "analyzing"
    return state


async def analyze_requirement(state: TeamState) -> TeamState:
    """需求分析节点 → 调用 Requirement Agent [B]"""
    # TODO Day 3: 替换为真实的 Requirement Agent 调用
    from contracts.agent_result import AgentResult, AgentRole

    state["phase"] = "analyzing"
    # Mock 输出
    state["requirement_analysis"] = AgentResult(
        agent_role=AgentRole.REQUIREMENT,
        success=True,
        result={
            "summary": f"需求分析: {state['task_meta']['requirement'][:50]}...",
            "affected_modules": ["待分析"],
            "acceptance_criteria": ["验收条件待 Agent 生成"],
            "ambiguity_flags": [],
            "confidence": 0.85,
        },
        reasoning="Mock: 需求分析完成",
    ).model_dump()
    state["phase"] = "planning"
    return state


async def plan_solution(state: TeamState) -> TeamState:
    """方案规划节点 → 调用 Planner Agent [B]"""
    from contracts.agent_result import AgentResult, AgentRole

    state["phase"] = "planning"
    state["plan"] = AgentResult(
        agent_role=AgentRole.PLANNER,
        success=True,
        result={
            "approach": "Mock: 方案规划",
            "steps": [],
            "risk_points": [],
            "estimated_changed_files": 1,
            "confidence": 0.8,
        },
        reasoning="Mock: 方案规划完成",
    ).model_dump()
    state["phase"] = "developing"
    return state


async def develop_changes(state: TeamState) -> TeamState:
    """代码开发节点 → 调用 Developer Agent [B]"""
    from contracts.agent_result import AgentResult, AgentRole

    state["phase"] = "developing"
    state["patches"] = [AgentResult(
        agent_role=AgentRole.DEVELOPER,
        success=True,
        result={
            "file_path": "mock/file.py",
            "original_snippet": "# mock original",
            "patched_snippet": "# mock patched",
            "diff": "@@ -0,0 +1 @@\n+# mock change",
            "change_description": "Mock: 代码修改",
            "change_type": "modify",
        },
        reasoning="Mock: 代码开发完成",
    ).model_dump()]
    state["phase"] = "testing"
    return state


async def apply_patches(state: TeamState) -> TeamState:
    """应用 Patch 节点 → 沙箱操作 [C]"""
    # TODO Day 3: Docker 沙箱中 clone + apply patches
    state["phase"] = "testing"
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
    return state


async def review_code(state: TeamState) -> TeamState:
    """代码审查节点 → 调用 Reviewer Agent [B]"""
    from contracts.agent_result import AgentResult, AgentRole

    state["phase"] = "reviewing"
    state["review"] = AgentResult(
        agent_role=AgentRole.REVIEWER,
        success=True,
        result={
            "passed": True,
            "risk_level": "low",
            "issues": [],
            "summary": "Mock: 代码审查通过",
            "actionable_feedback": "",
        },
        reasoning="Mock: 代码审查完成",
    ).model_dump()
    state["phase"] = "security_check"
    return state


async def security_check(state: TeamState) -> TeamState:
    """安全审查节点 → 调用 Security Agent [B]（两周版：集成入 Reviewer）"""
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
    else:
        state["phase"] = "done"
    return state


async def await_approval(state: TeamState) -> TeamState:
    """人工审批节点 → 暂停等待 [A]（两周版：自动通过）"""
    # 两周版简化：默认自动通过
    state["approval_granted"] = True
    state["phase"] = "done"
    return state


async def handle_error(state: TeamState) -> TeamState:
    """错误处理节点 → 分类 + 重试决策 [A]"""
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
    return state


async def finalize(state: TeamState) -> TeamState:
    """完成节点 → 汇总结果 [A]"""
    state["phase"] = "done"
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
    results = state.get("sandbox_results", [])
    if not results:
        return "handle_error"
    last = results[-1]
    if last.get("status") == "success" and last.get("test_summary", {}).get("failed", 0) == 0:
        return "review_code"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    return "develop_changes"


ReviewRoute = Literal["security_check", "develop_changes", "handle_error"]


def route_after_review(state: TeamState) -> ReviewRoute:
    """审查后的路由。"""
    review = state.get("review", {})
    if review.get("result", {}).get("passed", False):
        return "security_check"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    return "develop_changes"


def route_after_security(state: TeamState) -> Literal["done", "await_approval"]:
    """安全审查后的路由。"""
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
    builder.add_edge("await_approval", "finalize")
    builder.add_edge("finalize", END)
    builder.add_edge("handle_error", END)

    return builder.compile(checkpointer=checkpointer)


# =============================================================================
# 全局图实例（模块加载时编译）
# =============================================================================

graph = build_graph()
