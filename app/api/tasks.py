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

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import graph as workflow
from contracts.state import create_initial_state

router = APIRouter()

# =============================================================================
# 内存存储（Day 1-7: 内存字典；Day 8: 切换为 SQLite）
# =============================================================================

_tasks_store: dict[str, dict] = {}


async def _checkpoint_state(task_id: str) -> dict | None:
    """优先从 LangGraph checkpoint 读取，内存缓存只用于兼容当前开发模式。"""
    config = {"configurable": {"thread_id": task_id}}
    snapshot = await workflow.graph.aget_state(config)
    if snapshot and snapshot.values:
        state = dict(snapshot.values)
        _tasks_store[task_id] = state
        return state
    return _tasks_store.get(task_id)


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
    cancel_requested: bool = False
    current_node: str | None = None


class ApproveRequest(BaseModel):
    """审批请求"""
    feedback: str = Field(default="", description="审批意见")


class TaskListResponse(BaseModel):
    """任务列表"""
    tasks: list[TaskResponse]
    total: int


def _to_response(state: dict) -> TaskResponse:
    """将 checkpoint 状态统一投影为 API 响应。"""
    meta = state["task_meta"]
    return TaskResponse(
        task_id=meta["task_id"],
        phase=state.get("phase", "unknown"),
        requirement=meta["requirement"],
        repo_url=meta["repo_url"],
        iteration=state.get("iteration", 0),
        errors=state.get("errors", []),
        created_at=meta["created_at"],
        approval_required=state.get("approval_required", False),
        approval_granted=state.get("approval_granted", False),
        cancel_requested=state.get("cancel_requested", False),
        current_node=state.get("current_node"),
    )


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
    result = await workflow.graph.ainvoke(initial_state, config)

    # 缓存最新状态
    _tasks_store[task_id] = result

    return _to_response(result)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """查询任务状态。"""
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return _to_response(state)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """列出所有任务。"""
    all_tasks = list(_tasks_store.values())
    page = all_tasks[offset:offset + limit]

    tasks = [
        _to_response(s)
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
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if state.get("phase") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="任务不在等待审批状态")

    config = {"configurable": {"thread_id": task_id}}
    await workflow.graph.aupdate_state(
        config, {"approval_granted": True, "approval_feedback": req.feedback}
    )
    # None 表示从 checkpoint 的中断点继续，而不是从 init_task 重新开始。
    result = await workflow.graph.ainvoke(None, config)
    _tasks_store[task_id] = result
    return _to_response(result)


@router.post("/{task_id}/reject", response_model=TaskResponse)
async def reject_task(task_id: str, req: ApproveRequest = ApproveRequest()):
    """
    审批拒绝。

    任务将返回 develop_changes 节点，Developer Agent 根据反馈重新修改。
    """
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if state.get("phase") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="任务不在等待审批状态")

    config = {"configurable": {"thread_id": task_id}}
    await workflow.graph.aupdate_state(
        config, {"approval_granted": False, "approval_feedback": req.feedback}
    )
    result = await workflow.graph.ainvoke(None, config)
    _tasks_store[task_id] = result
    return _to_response(result)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    """取消任务。"""
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    config = {"configurable": {"thread_id": task_id}}
    state["cancel_requested"] = True
    state["phase"] = "cancelled"
    state.setdefault("events", []).append({
        "event_id": str(uuid.uuid4()), "task_id": task_id, "event_type": "progress",
        "node_name": state.get("current_node"), "timestamp": __import__("datetime").datetime.now().isoformat(),
        "message": "已请求取消任务", "data": {"phase": "cancelled"},
    })
    await workflow.graph.aupdate_state(config, state)
    _tasks_store[task_id] = state
    return _to_response(state)


@router.get("/{task_id}/events")
async def task_events(task_id: str):
    """返回当前已记录事件的 SSE 流；前端可断线后重新拉取。"""
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    async def stream() -> AsyncIterator[str]:
        for event in state.get("events", []):
            yield f"event: {event.get('event_type', 'progress')}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(stream(), media_type="text/event-stream")
