"""
任务管理 API。

端点：
    POST   /tasks              — 创建任务
    GET    /tasks/{task_id}    — 查询任务状态
    POST   /tasks/{task_id}/approve   — 审批通过
    POST   /tasks/{task_id}/reject    — 审批拒绝
    POST   /tasks/{task_id}/cancel    — 取消任务
    GET    /tasks/{task_id}/events    — 任务事件（SSE）
"""

import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.graph import graph
from contracts.state import create_initial_state

router = APIRouter()

# =============================================================================
# 内存存储（Day 1-7: 内存字典；Day 8: 切换为 SQLite）
# =============================================================================

_tasks_store: dict[str, dict] = {}


# =============================================================================
# 请求/响应模型
# =============================================================================

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    requirement: str = Field(description="用户需求描述")
    repo_url: str = Field(description="代码仓库 URL")
    branch: str = Field(default="main", description="目标分支")
    max_iterations: int = Field(default=3, ge=1, le=10, description="最大迭代次数")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    phase: str
    requirement: str
    repo_url: str
    iteration: int
    errors: list = Field(default_factory=list)
    created_at: str
    approval_required: bool = False
    approval_granted: bool = False


class ApproveRequest(BaseModel):
    """审批请求"""
    feedback: str = Field(default="", description="审批意见")


class TaskListResponse(BaseModel):
    """任务列表"""
    tasks: list[TaskResponse]
    total: int


# =============================================================================
# 端点实现
# =============================================================================

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest):
    """
    创建新任务。

    提交一个软件需求，系统将自动启动多 Agent 协同开发流程。
    """
    task_id = str(uuid.uuid4())[:8]

    # 构建初始状态
    initial_state = create_initial_state(
        task_id=task_id,
        repo_url=req.repo_url,
        branch=req.branch,
        requirement=req.requirement,
        max_iterations=req.max_iterations,
    )

    # 运行 LangGraph
    config = {"configurable": {"thread_id": task_id}}
    result = await graph.ainvoke(initial_state, config)

    # 缓存最新状态
    _tasks_store[task_id] = result

    return TaskResponse(
        task_id=task_id,
        phase=result.get("phase", "init"),
        requirement=req.requirement,
        repo_url=req.repo_url,
        iteration=result.get("iteration", 0),
        errors=result.get("errors", []),
        created_at=result["task_meta"]["created_at"],
        approval_required=result.get("approval_required", False),
        approval_granted=result.get("approval_granted", False),
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """查询任务状态。"""
    state = _tasks_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return TaskResponse(
        task_id=task_id,
        phase=state.get("phase", "unknown"),
        requirement=state["task_meta"]["requirement"],
        repo_url=state["task_meta"]["repo_url"],
        iteration=state.get("iteration", 0),
        errors=state.get("errors", []),
        created_at=state["task_meta"]["created_at"],
        approval_required=state.get("approval_required", False),
        approval_granted=state.get("approval_granted", False),
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """列出所有任务。"""
    all_tasks = list(_tasks_store.values())
    page = all_tasks[offset:offset + limit]

    tasks = [
        TaskResponse(
            task_id=s["task_meta"]["task_id"],
            phase=s.get("phase", "unknown"),
            requirement=s["task_meta"]["requirement"],
            repo_url=s["task_meta"]["repo_url"],
            iteration=s.get("iteration", 0),
            errors=s.get("errors", []),
            created_at=s["task_meta"]["created_at"],
        )
        for s in page
    ]

    return TaskListResponse(tasks=tasks, total=len(all_tasks))


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_task(task_id: str, req: ApproveRequest = ApproveRequest()):
    """
    审批通过。

    仅当任务处于 awaiting_approval 状态时有效。
    两周版：审批后自动继续执行。
    """
    state = _tasks_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if state.get("phase") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="任务不在等待审批状态")

    state["approval_granted"] = True
    state["approval_feedback"] = req.feedback

    # 继续执行（从审批节点到 finalize）
    config = {"configurable": {"thread_id": task_id}}
    result = await graph.ainvoke(state, config)
    _tasks_store[task_id] = result

    return TaskResponse(
        task_id=task_id,
        phase=result.get("phase", "done"),
        requirement=state["task_meta"]["requirement"],
        repo_url=state["task_meta"]["repo_url"],
        iteration=state.get("iteration", 0),
        errors=state.get("errors", []),
        created_at=state["task_meta"]["created_at"],
        approval_required=False,
        approval_granted=True,
    )


@router.post("/{task_id}/reject", response_model=TaskResponse)
async def reject_task(task_id: str, req: ApproveRequest = ApproveRequest()):
    """
    审批拒绝。

    任务将返回 develop_changes 节点，Developer Agent 根据反馈重新修改。
    """
    state = _tasks_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if state.get("phase") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="任务不在等待审批状态")

    state["approval_granted"] = False
    state["approval_feedback"] = req.feedback
    state["phase"] = "developing"
    state["iteration"] = state.get("iteration", 0) + 1

    config = {"configurable": {"thread_id": task_id}}
    result = await graph.ainvoke(state, config)
    _tasks_store[task_id] = result

    return TaskResponse(
        task_id=task_id,
        phase=result.get("phase", "developing"),
        requirement=state["task_meta"]["requirement"],
        repo_url=state["task_meta"]["repo_url"],
        iteration=state.get("iteration", 0),
        errors=state.get("errors", []),
        created_at=state["task_meta"]["created_at"],
        approval_required=False,
        approval_granted=False,
    )


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    """取消任务。"""
    state = _tasks_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    state["phase"] = "cancelled"
    _tasks_store[task_id] = state

    return TaskResponse(
        task_id=task_id,
        phase="cancelled",
        requirement=state["task_meta"]["requirement"],
        repo_url=state["task_meta"]["repo_url"],
        iteration=state.get("iteration", 0),
        errors=state.get("errors", []),
        created_at=state["task_meta"]["created_at"],
    )
