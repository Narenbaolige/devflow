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
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import graph as workflow
from app.config import settings
from contracts.state import create_initial_state

router = APIRouter()

# =============================================================================
# 内存缓存只用于当前进程加速。任务列表的真实来源是 LangGraph Checkpointer，
# 因而 PostgreSQL 模式在服务重启后仍可列出历史任务。
# =============================================================================

_tasks_store: dict[str, dict] = {}
_running_tasks: dict[str, asyncio.Task] = {}


def _normalize_repository_reference(repo_url: str, branch: str) -> tuple[str, str]:
    """Convert a GitHub /tree/<branch> webpage URL into a cloneable URL."""
    parsed = urlparse(repo_url.strip())
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return repo_url, branch
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 4 and parts[2] == "tree":
        owner, repository = parts[0], parts[1]
        selected_branch = "/".join(parts[3:])
        if owner and repository and selected_branch:
            return f"https://github.com/{owner}/{repository}.git", selected_branch
    return repo_url, branch


async def _checkpoint_state(task_id: str) -> dict | None:
    """优先从 LangGraph checkpoint 读取，内存缓存只用于兼容当前开发模式。"""
    config = {"configurable": {"thread_id": task_id}}
    snapshot = await workflow.graph.aget_state(config)
    if snapshot and snapshot.values:
        state = dict(snapshot.values)
        _tasks_store[task_id] = state
        return state
    return _tasks_store.get(task_id)


async def _checkpoint_task_states() -> list[dict]:
    """读取每个任务线程的最新 checkpoint 状态。

    ``alist(None)`` 返回所有 checkpoint（按新到旧排序）。同一任务会有多个
    checkpoint，因此仅保留首次遇到的 thread_id。内存缓存仅作为不支持枚举的
    Checkpointer 的兼容后备。
    """
    checkpointer = getattr(workflow.graph, "checkpointer", None)
    if checkpointer is None or not hasattr(checkpointer, "alist"):
        return list(_tasks_store.values())

    states: list[dict] = []
    seen_task_ids: set[str] = set()
    try:
        async for checkpoint in checkpointer.alist(None):
            values = checkpoint.checkpoint.get("channel_values", {})
            meta = values.get("task_meta")
            if not isinstance(meta, dict):
                continue
            task_id = meta.get("task_id")
            if not task_id or task_id in seen_task_ids:
                continue
            seen_task_ids.add(task_id)
            state = dict(values)
            _tasks_store[task_id] = state
            states.append(state)
    except (AttributeError, TypeError):
        # 自定义 checkpointer 未实现全量枚举时，仍保持本地开发可用。
        return list(_tasks_store.values())

    return states


# =============================================================================
# 请求/响应模型
# =============================================================================

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    requirement: str = Field(description="用户需求描述")
    repo_url: str = Field(description="代码仓库 URL")
    branch: str = Field(default="main", description="目标分支")
    max_iterations: int = Field(default=5, ge=1, le=10, description="最大迭代次数")
    timeout_seconds: int | None = Field(
        default=settings.TASK_TIMEOUT_SECONDS, ge=0, description="任务总超时秒数；0 表示不限时"
    )
    budget_limit_usd: float | None = Field(
        default=None, ge=0, description="LLM 成本上限（美元）；不传则使用全局配置"
    )
    publish_to_remote: bool = Field(default=False)


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
    deadline_at: str | None = None
    budget_limit_usd: float | None = None
    budget_used_usd: float = 0.0
    publication: dict | None = None
    artifact: dict | None = None


class ApproveRequest(BaseModel):
    """审批请求"""
    feedback: str = Field(default="", description="审批意见")


class TaskListResponse(BaseModel):
    """任务列表"""
    tasks: list[TaskResponse]
    total: int


class TaskStatsResponse(BaseModel):
    """任务运行统计，数据来源为 Checkpointer 中的最新任务状态。"""
    total_tasks: int
    phase_counts: dict[str, int]
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    awaiting_approval_tasks: int
    average_iterations: float
    average_duration_ms: float
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float


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
        deadline_at=state.get("deadline_at"),
        budget_limit_usd=state.get("budget_limit_usd"),
        budget_used_usd=state.get("budget_used_usd", 0.0),
        publication=state.get("publication"),
        artifact=state.get("artifact"),
    )


def _build_task_stats(states: list[dict]) -> TaskStatsResponse:
    """从任务状态及 Agent 事件汇总统计数据。"""
    phase_counts: dict[str, int] = {}
    total_iterations = 0
    durations: list[float] = []
    input_tokens = output_tokens = 0
    total_cost = 0.0

    for state in states:
        phase = state.get("phase", "unknown")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        total_iterations += state.get("iteration", 0)
        total_cost += float(state.get("budget_used_usd", 0.0) or 0.0)

        created_at = state.get("task_meta", {}).get("created_at")
        event_times = []
        for event in state.get("events", []):
            data = event.get("data") or {}
            if event.get("event_type") == "agent_complete":
                input_tokens += int(data.get("input_tokens", 0) or 0)
                output_tokens += int(data.get("output_tokens", 0) or 0)
            if event.get("timestamp"):
                try:
                    event_times.append(datetime.fromisoformat(event["timestamp"]))
                except ValueError:
                    pass
        if created_at and event_times:
            try:
                duration = (max(event_times) - datetime.fromisoformat(created_at)).total_seconds() * 1000
                durations.append(max(duration, 0.0))
            except ValueError:
                pass

    total = len(states)
    terminal = {"done", "failed", "cancelled"}
    return TaskStatsResponse(
        total_tasks=total,
        phase_counts=phase_counts,
        running_tasks=sum(
            count for phase, count in phase_counts.items()
            if phase not in terminal | {"awaiting_approval"}
        ),
        completed_tasks=phase_counts.get("done", 0),
        failed_tasks=phase_counts.get("failed", 0),
        cancelled_tasks=phase_counts.get("cancelled", 0),
        awaiting_approval_tasks=phase_counts.get("awaiting_approval", 0),
        average_iterations=round(total_iterations / total, 2) if total else 0.0,
        average_duration_ms=round(sum(durations) / len(durations), 2) if durations else 0.0,
        total_input_tokens=input_tokens,
        total_output_tokens=output_tokens,
        total_cost_usd=round(total_cost, 6),
    )


async def _execute_task_pipeline(task_id: str, state: dict) -> dict:
    """Run the workflow nodes sequentially for API-created tasks.

    This avoids a LangGraph scheduler hang observed after requirement analysis
    while retaining the same real agents, sandbox, tests and review nodes.

    Each node's output is persisted both in the in-memory store and in the
    LangGraph checkpointer so that task listings survive memory-cache clears.
    """
    for node in (workflow.init_task, workflow.setup_workspace, workflow.analyze_requirement, workflow.plan_solution):
        state = await node(state)
        _tasks_store[task_id] = state
        if state.get("phase") in {"failed", "cancelled", "awaiting_approval"}:
            return state

    while True:
        for node in (workflow.develop_changes, workflow.apply_patches, workflow.run_tests):
            state = await node(state)
            _tasks_store[task_id] = state
            if state.get("phase") in {"failed", "cancelled", "awaiting_approval"}:
                return state

        if workflow.route_after_test(state) == "develop_changes":
            continue
        if workflow.route_after_test(state) != "review_code":
            state = await workflow.handle_error(state)
            _tasks_store[task_id] = state
            return state

        state = await workflow.review_code(state)
        _tasks_store[task_id] = state
        if workflow.route_after_review(state) == "develop_changes":
            continue
        if workflow.route_after_review(state) != "security_check":
            state = await workflow.handle_error(state)
            _tasks_store[task_id] = state
            return state

        state = await workflow.security_check(state)
        _tasks_store[task_id] = state
        if state.get("phase") == "awaiting_approval":
            return state
        if state.get("phase") != "done":
            return state
        state = await workflow.finalize(state)
        _tasks_store[task_id] = state
        return state


async def _run_task(task_id: str, initial_state: dict, timeout_seconds: int) -> None:
    """后台运行图，使查询和取消 API 在任务执行期间仍可响应。"""
    config = {"configurable": {"thread_id": task_id}}
    try:
        pipeline = _execute_task_pipeline(task_id, initial_state)
        result = await asyncio.wait_for(pipeline, timeout=timeout_seconds) if timeout_seconds else await pipeline
        _tasks_store[task_id] = result
    except TimeoutError:
        state = await _checkpoint_state(task_id) or initial_state
        state["phase"] = "failed"
        state.setdefault("errors", []).append({
            "node": state.get("current_node") or "runtime",
            "error_type": "timeout",
            "message": "任务总超时，后台执行已终止",
            "timestamp": datetime.now().isoformat(),
            "recoverable": False,
            "retry_count": state.get("iteration", 0),
        })
        _tasks_store[task_id] = state
        try:
            await workflow.graph.aupdate_state(config, state)
        except Exception:
            pass
    except asyncio.CancelledError:
        # cancel_task 已写入 cancelled 状态；避免后台协程覆盖该状态。
        raise
    except Exception as exc:
        # A graph error used to terminate this background task silently, leaving
        # the last checkpoint displayed forever as an in-progress phase.
        state = await _checkpoint_state(task_id) or initial_state
        state["phase"] = "failed"
        state.setdefault("errors", []).append({
            "node": state.get("current_node") or "runtime",
            "error_type": "unknown",
            "message": f"工作流异常: {type(exc).__name__}: {exc}",
            "timestamp": datetime.now().isoformat(),
            "recoverable": False,
            "retry_count": state.get("iteration", 0),
        })
        state.setdefault("events", []).append({
            "event_id": str(uuid.uuid4()), "task_id": task_id,
            "event_type": "error", "node_name": state.get("current_node") or "runtime",
            "timestamp": datetime.now().isoformat(),
            "message": state["errors"][-1]["message"], "data": {"phase": "failed"},
        })
        _tasks_store[task_id] = state
        try:
            await workflow.graph.aupdate_state(config, state)
        except Exception:
            pass
    finally:
        _running_tasks.pop(task_id, None)


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
    repo_url, branch = _normalize_repository_reference(req.repo_url, req.branch)

    # 构建初始状态
    budget_limit = req.budget_limit_usd
    if budget_limit is None and settings.TASK_BUDGET_USD > 0:
        budget_limit = settings.TASK_BUDGET_USD
    initial_state = create_initial_state(
        task_id=task_id,
        repo_url=repo_url,
        branch=branch,
        requirement=req.requirement,
        max_iterations=req.max_iterations,
        execution_timeout_seconds=req.timeout_seconds,
        budget_limit_usd=budget_limit,
        publish_to_remote=req.publish_to_remote,
    )
    initial_state["events"].append({
        "event_id": str(uuid.uuid4()),
        "task_id": task_id,
        "event_type": "progress",
        "node_name": "init_task",
        "timestamp": datetime.now().isoformat(),
        "message": "任务已创建，等待后台执行",
        "data": {"phase": "init"},
    })

    _tasks_store[task_id] = initial_state
    _running_tasks[task_id] = asyncio.create_task(
        _run_task(task_id, initial_state, req.timeout_seconds), name=f"devflow-{task_id}"
    )
    return _to_response(initial_state)


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats():
    """获取所有任务的状态、耗时、迭代与模型用量汇总。"""
    return _build_task_stats(await _checkpoint_task_states())


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """查询任务状态。"""
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return _to_response(state)


@router.get("/{task_id}/artifact")
async def download_artifact(task_id: str):
    """Download the exported project archive for a completed local task."""
    state = await _checkpoint_state(task_id)
    artifact = (state or {}).get("artifact") or {}
    path = artifact.get("path")
    if not path:
        raise HTTPException(status_code=404, detail="该任务没有可下载的项目产物")
    from pathlib import Path
    archive = Path(path)
    if not archive.is_file():
        raise HTTPException(status_code=404, detail="项目产物已不存在")
    return FileResponse(archive, filename=artifact.get("name") or archive.name)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """列出任务；PostgreSQL 模式下服务重启后仍返回历史任务。"""
    all_tasks = await _checkpoint_task_states()
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

    # API tasks run through the sequential executor, so there is no LangGraph
    # interrupt checkpoint to resume. Continue from the in-memory task state.
    state["approval_granted"] = True
    state["approval_feedback"] = req.feedback
    state = await workflow.await_approval(state)
    if state.get("phase") == "done":
        state = await workflow.finalize(state)
    _tasks_store[task_id] = state
    return _to_response(state)


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

    state["approval_granted"] = False
    state["approval_feedback"] = req.feedback
    state = await workflow.await_approval(state)
    _tasks_store[task_id] = state
    if state.get("phase") == "developing":
        _running_tasks[task_id] = asyncio.create_task(
            _execute_task_pipeline(task_id, state), name=f"devflow-rework-{task_id}"
        )
    return _to_response(state)


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
    running_task = _running_tasks.get(task_id)
    if running_task and not running_task.done():
        running_task.cancel()
    try:
        await workflow.graph.aupdate_state(config, state)
    except Exception:
        # 若任务尚未来得及写入首个 checkpoint，本地状态仍可被立即查询。
        pass
    _tasks_store[task_id] = state
    return _to_response(state)


@router.get("/{task_id}/events")
async def task_events(task_id: str):
    """实时 SSE：先回放历史事件，再推送 checkpoint 中新增的事件。"""
    state = await _checkpoint_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    async def stream() -> AsyncIterator[str]:
        seen_event_ids: set[str] = set()
        terminal_phases = {"done", "failed", "cancelled"}

        while True:
            latest_state = await _checkpoint_state(task_id)
            if latest_state is None:
                yield "event: error\ndata: {\"message\": \"任务不存在\"}\n\n"
                return

            for event in latest_state.get("events", []):
                event_id = event.get("event_id")
                if event_id and event_id in seen_event_ids:
                    continue
                if event_id:
                    seen_event_ids.add(event_id)
                yield (
                    f"id: {event_id or ''}\n"
                    f"event: {event.get('event_type', 'progress')}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )

            if latest_state.get("phase") in terminal_phases:
                return

            # 保持代理和浏览器连接活跃；下一轮读取 checkpoint 中的新增事件。
            yield ": keep-alive\n\n"
            await asyncio.sleep(settings.SSE_POLL_INTERVAL_MS / 1000)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
