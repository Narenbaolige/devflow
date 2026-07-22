"""
DevFlow Contracts — 项目宪法。

本模块包含四个核心数据结构，所有模块共同依赖。
P0 阶段冻结，修改需四人评审。

- TeamState:   LangGraph 全局状态
- AgentResult: Agent 输入输出契约
- SandboxResult: 沙箱执行结果
- TaskEvent:   统一事件模型（SSE 推送）
"""

from contracts.agent_result import (
    AgentInvocation,
    AgentResult,
    AgentRole,
    PatchResult,
    PlanResult,
    PlanStep,
    RequirementResult,
    ReviewIssue,
    ReviewResult,
    SecurityIssue,
    SecurityResult,
)
from contracts.event import EventType, TaskEvent
from contracts.sandbox_result import (
    SandboxResult,
    TestFailure,
    TestSummary,
)
from contracts.state import ErrorRecord, TaskMeta, TeamState

__all__ = [
    # State
    "TeamState",
    "TaskMeta",
    "ErrorRecord",
    # Agent
    "AgentRole",
    "AgentResult",
    "AgentInvocation",
    "RequirementResult",
    "PlanResult",
    "PlanStep",
    "PatchResult",
    "ReviewResult",
    "ReviewIssue",
    "SecurityResult",
    "SecurityIssue",
    # Sandbox
    "SandboxResult",
    "TestSummary",
    "TestFailure",
    # Event
    "TaskEvent",
    "EventType",
]
