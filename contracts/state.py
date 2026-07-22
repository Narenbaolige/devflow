"""
contracts/state.py — DevFlow 全局状态定义。

LangGraph StateGraph 的核心数据结构。
使用 Annotated 机制定义 reducer，控制状态合并行为。

字段 Owner 标注：
  [A] = 编排层写入    [B] = Agent 层写入    [C] = 沙箱层写入

P0 冻结，修改需四人评审。
"""

from datetime import datetime
from typing import Annotated, Literal, TypedDict

# =============================================================================
# 子结构
# =============================================================================

class TaskMeta(TypedDict):
    """任务元数据 — [A] 写入，创建时确定，之后只读"""
    task_id: str
    repo_url: str
    branch: str
    requirement: str                 # 用户原始需求描述
    created_at: str                  # ISO 8601


class ErrorRecord(TypedDict):
    """错误记录 — [A/B/C] 均可写入，使用 append reducer"""
    node: str                        # 出错的节点名
    error_type: Literal[
        "llm_error",
        "sandbox_error",
        "timeout",
        "validation_error",
        "unknown",
    ]
    message: str
    timestamp: str                   # ISO 8601
    recoverable: bool
    retry_count: int


# =============================================================================
# TeamState — 全局状态
# =============================================================================

class TeamState(TypedDict):
    """
    DevFlow 全局状态。

    LangGraph 通过 Annotated 类型定义 reducer 行为：
      - add_messages: 消息列表追加（不覆盖）
      - append: 列表追加
      - merge_by_file: 按 file_path 去重合并 Patch 列表
    """

    # ========== 任务层 [A] ==========
    task_meta: TaskMeta
    phase: Literal[
        "init",
        "analyzing",
        "planning",
        "developing",
        "testing",
        "reviewing",
        "security_check",
        "awaiting_approval",
        "done",
        "failed",
        "cancelled",
    ]
    iteration: int                   # 当前迭代次数（返工计数，默认 0）
    max_iterations: int              # 最大返工次数，默认 3

    # ========== 控制层 [A] ==========
    approval_required: bool          # 是否需要人工审批
    approval_granted: bool           # 审批是否通过
    approval_feedback: str           # 审批拒绝时的反馈文本
    errors: Annotated[list[ErrorRecord], "append"]

    # ========== Agent 产出物层 [B 产生，C 消费] ==========
    # 注意：dict 是 Pydantic 模型的 .model_dump() 结果
    requirement_analysis: dict | None
    plan: dict | None
    patches: Annotated[list[dict], "merge_by_file"]  # 按 file_path 去重
    review: dict | None
    security_review: dict | None

    # ========== 沙箱层 [C] ==========
    sandbox_results: Annotated[list[dict], "append"]


# =============================================================================
# Reducer 函数（供 LangGraph 使用）
# =============================================================================

def reducer_append(existing: list, new: list) -> list:
    """追加 reducer：将新元素追加到已有列表。"""
    return (existing or []) + (new or [])


def reducer_merge_by_file(existing: list, new: list) -> list:
    """按 file_path 去重合并 reducer：同文件的新 Patch 覆盖旧 Patch。"""
    merged = {p.get("file_path", ""): p for p in (existing or [])}
    for p in (new or []):
        merged[p.get("file_path", "")] = p
    return list(merged.values())


def create_initial_state(
    task_id: str,
    repo_url: str,
    branch: str,
    requirement: str,
    max_iterations: int = 3,
) -> TeamState:
    """创建初始 TeamState。"""
    return TeamState(
        task_meta=TaskMeta(
            task_id=task_id,
            repo_url=repo_url,
            branch=branch,
            requirement=requirement,
            created_at=datetime.now().isoformat(),
        ),
        phase="init",
        iteration=0,
        max_iterations=max_iterations,
        approval_required=False,
        approval_granted=False,
        approval_feedback="",
        errors=[],
        requirement_analysis=None,
        plan=None,
        patches=[],
        review=None,
        security_review=None,
        sandbox_results=[],
    )
