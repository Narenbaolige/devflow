"""
contracts/event.py — 统一事件模型。

SSE 推送的事件结构。前端通过 EventSource 消费。
A 和 D 共同依赖此模型。

P0 冻结，修改需四人评审。
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """事件类型枚举"""

    # 节点生命周期
    NODE_START = "node_start"              # 节点开始执行
    NODE_COMPLETE = "node_complete"        # 节点执行完成

    # Agent 相关
    AGENT_THINKING = "agent_thinking"      # Agent 推理中（流式文本片段）
    TOOL_CALL = "tool_call"                # 工具调用开始
    TOOL_RESULT = "tool_result"            # 工具调用返回

    # 产出物
    PATCH_GENERATED = "patch_generated"    # 代码 Patch 已生成
    TEST_RESULT = "test_result"            # 测试结果（SandboxResult）

    # 控制
    APPROVAL_REQUIRED = "approval_required"  # 需要人工审批
    ERROR = "error"                        # 错误发生
    PROGRESS = "progress"                  # 进度更新
    TASK_COMPLETE = "task_complete"        # 任务完成


class TaskEvent(BaseModel):
    """
    统一事件模型。

    所有节点通过此模型向 SSE 通道推送事件。
    前端统一消费，无需区分事件来源。
    """

    event_id: str
    task_id: str
    event_type: EventType
    node_name: str | None = Field(
        default=None,
        description="来源节点名称，如 analyze_requirement",
    )
    agent_role: str | None = Field(
        default=None,
        description="来源 Agent 角色，如 requirement",
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict | None = Field(
        default=None,
        description="事件携带的结构化数据",
    )
    message: str = Field(
        default="",
        description="人类可读的事件描述",
    )
