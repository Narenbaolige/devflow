"""
contracts/sandbox_result.py — 沙箱执行结果。

沙箱执行引擎（C 负责）对外的唯一数据结构。
所有字段均为确定性结果，不依赖 LLM。
前后端、Agent 均依赖此结构的字段约定。

P0 冻结，修改需四人评审。
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# 测试结果子结构
# =============================================================================

class TestSummary(BaseModel):
    """测试结果汇总"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_ms: int = 0


class TestFailure(BaseModel):
    """单个测试失败详情"""

    test_name: str
    test_file: str
    failure_type: Literal[
        "assertion",
        "error",
        "timeout",
        "import_error",
        "other",
    ]
    message: str = Field(description="失败消息摘要")
    traceback: str = Field(description="完整 traceback")
    is_new_failure: bool = Field(
        description="是否为本次修改引入的新失败（与 baseline 对比）",
    )


# =============================================================================
# SandboxResult — 沙箱执行结果
# =============================================================================

class SandboxResult(BaseModel):
    """
    沙箱执行结果。

    确定性原则：相同输入必须产生相同结构输出。
    不依赖 LLM，不包含非确定性字段。

    示例（测试全部通过）：
        SandboxResult(
            execution_id="exec-001",
            task_id="task-001",
            sandbox_type="test",
            status="success",
            exit_code=0,
            timed_out=False,
            duration_ms=3812,
            test_summary=TestSummary(total=42, passed=42, failed=0),
            ...
        )
    """

    # --- 基本信息 ---
    execution_id: str
    task_id: str
    sandbox_type: Literal["test", "lint", "type_check", "custom"]

    # --- 执行结果 ---
    status: Literal["success", "failure", "timeout", "error"]
    exit_code: int
    timed_out: bool
    duration_ms: int

    # --- 输出（截断保护） ---
    stdout: str = Field(default="", max_length=100_000)
    stderr: str = Field(default="", max_length=100_000)

    # --- 测试结果（sandbox_type="test" 时必填） ---
    test_summary: TestSummary | None = None
    test_failures: list[TestFailure] = Field(default_factory=list)

    # --- 资源使用 ---
    max_memory_mb: float | None = None
    max_cpu_percent: float | None = None

    # --- 时间戳 ---
    started_at: str = ""               # ISO 8601
    finished_at: str = ""              # ISO 8601


# =============================================================================
# 沙箱能力描述（供 Agent 查询）
# =============================================================================

class SandboxCapabilities(BaseModel):
    """沙箱能力描述 — API 返回，告诉 Agent 沙箱能做什么"""

    python_version: str = "3.11"
    preinstalled_packages: list[str] = Field(
        default_factory=lambda: ["pytest", "pip"]
    )
    max_timeout_seconds: int = 300
    max_memory_mb: int = 512
    allow_network: bool = False
    working_dir: str = "/workspace"
    available_commands: list[str] = Field(
        default_factory=lambda: [
            "python",
            "pytest",
            "pip",
            "git",
            "ls",
            "cat",
            "echo",
        ]
    )
