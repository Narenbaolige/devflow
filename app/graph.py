"""
LangGraph 工作流定义。

DevFlow 的核心编排引擎。定义所有节点、条件边和 Checkpointer。
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from contracts.state import TeamState


# =============================================================================
# 沙箱 Mock 开关：通过环境变量 DEVFLOW_USE_MOCK 控制，默认 true
# 注意：沙箱和 Agent 可以独立控制。设置 DEVFLOW_USE_SANDBOX=false 单独启用真实沙箱
# =============================================================================
_USE_MOCK_SANDBOX = os.getenv("DEVFLOW_USE_SANDBOX", os.getenv("DEVFLOW_USE_MOCK", "true")).lower() == "true"


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


def _limits_exceeded(state: TeamState, node_name: str) -> bool:
    """在节点边界强制执行任务总超时与 LLM 预算上限。"""
    deadline_at = state.get("deadline_at")
    timed_out = bool(deadline_at and datetime.now() >= datetime.fromisoformat(deadline_at))
    budget_limit = state.get("budget_limit_usd")
    budget_exceeded = budget_limit is not None and state.get("budget_used_usd", 0.0) >= budget_limit
    if not (timed_out or budget_exceeded):
        return False

    error_type = "timeout" if timed_out else "budget_exceeded"
    message = "任务总超时，已停止执行" if timed_out else "任务预算已耗尽，已停止执行"
    state["phase"] = "failed"
    state.setdefault("errors", []).append({
        "node": node_name,
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "recoverable": False,
        "retry_count": state.get("iteration", 0),
    })
    _record_event(state, "error", message, node_name)
    return True


def _blocked(state: TeamState, node_name: str) -> bool:
    return _cancelled(state, node_name) or _limits_exceeded(state, node_name)


async def _sandbox_call(sandbox, command: str, *, cwd: str = "/workspace", timeout: int = 60):
    """在独立线程中调用沙箱命令，避免阻塞事件循环。"""
    return await asyncio.to_thread(sandbox.execute, command, cwd=cwd, timeout=timeout)


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
    if _blocked(state, "analyze_requirement"):
        return state
    from app.agents import RequirementAgent, agent_node

    state["phase"] = "analyzing"
    state = await agent_node(state, RequirementAgent())
    state["phase"] = "planning"
    _record_event(state, "node_complete", "需求分析完成", "analyze_requirement")
    return state


async def plan_solution(state: TeamState) -> TeamState:
    """方案规划节点 → 调用 Planner Agent [B]"""
    if _blocked(state, "plan_solution"):
        return state
    from app.agents import PlannerAgent, agent_node

    state["phase"] = "planning"
    state = await agent_node(state, PlannerAgent())
    state["phase"] = "developing"
    _record_event(state, "node_complete", "方案规划完成", "plan_solution")
    return state


async def develop_changes(state: TeamState) -> TeamState:
    """代码开发节点 → 调用 Developer Agent [B]"""
    if _blocked(state, "develop_changes"):
        return state
    from app.agents import DeveloperAgent, agent_node

    # 在节点中计数迭代（不在条件路由中修改 state，LangGraph 才会持久化）
    state["phase"] = "developing"
    state = await agent_node(state, DeveloperAgent())
    state["iteration"] = state.get("iteration", 0) + 1
    state["phase"] = "testing"
    _record_event(state, "node_complete", "代码修改完成", "develop_changes")
    return state


async def apply_patches(state: TeamState) -> TeamState:
    """应用 Patch 节点 → 沙箱操作 [C]

    使用沙箱 clone 目标仓库并应用 Developer Agent 生成的 patch。
    同一任务的沙箱实例会被后续 run_tests 节点复用。
    """
    if _blocked(state, "apply_patches"):
        return state

    if _USE_MOCK_SANDBOX:
        state["phase"] = "testing"
        _record_event(state, "node_complete", "Patch 应用步骤完成 (Mock)", "apply_patches")
        return state

    from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox

    task_id = state["task_meta"]["task_id"]
    meta = state["task_meta"]
    patches = state.get("patches") or []

    try:
        sandbox = get_sandbox(task_id)

        # Step 1: clone 仓库
        r = await _sandbox_call(
            sandbox,
            f"git clone --depth 1 --branch {meta['branch']} {meta['repo_url']} repo",
            timeout=120,
        )
        if r.exit_code != 0:
            _record_event(state, "error", f"git clone 失败: {r.stderr or r.stdout[:200]}", "apply_patches")
            cleanup_sandbox(task_id)
            state["phase"] = "failed"
            return state

        # Step 2: 应用 patches
        if patches:
            import json as _json
            import tempfile as _tempfile
            from pathlib import Path as _Path
            for i, patch in enumerate(patches):
                result = patch if isinstance(patch, dict) else {}
                diff = result.get("diff", "")
                file_path = result.get("file_path", "")
                orig_snippet = result.get("original_snippet", "")
                patched_snippet = result.get("patched_snippet", "")

                if not diff and not (orig_snippet and patched_snippet and file_path):
                    continue

                # 规范化 file_path：去除 LLM 可能返回的绝对路径前缀，保留子目录结构
                # 处理：D:/path/to/repo/src/foo.py → src/foo.py；src/foo.py → src/foo.py
                if ":" in file_path:
                    # Windows 绝对路径 → 去掉盘符及之前的部分
                    file_path = file_path.rsplit(":", 1)[-1]
                # 去掉可能残留的前导斜杠/反斜杠
                file_path = file_path.lstrip("\\").lstrip("/")
                # 如果路径包含 repo 名等多余前缀，取最后看起来合理的部分
                # 保守策略：仅当路径以已知模式开头且后面是正常目录结构时保留全路径

                applied = False

                # Phase A: 尝试 git apply（严格模式，上下文必须精确匹配）
                patch_file = _Path(_tempfile.gettempdir()) / f"devflow-patch-{task_id}-{i}.diff"
                patch_file.write_text(diff, encoding="utf-8")
                r = await _sandbox_call(sandbox, f"git apply --verbose {patch_file}", cwd="repo")
                patch_file.unlink(missing_ok=True)
                if r.exit_code == 0:
                    applied = True
                    _record_event(state, "progress", f"Patch {i} ({file_path}) git apply 成功", "apply_patches")

                # Phase B: git apply 失败 → 字符串替换（容忍上下文漂移）
                if not applied and orig_snippet and patched_snippet and file_path:
                    target = f"repo/{file_path}"
                    # 将代码片段写入临时文件，避免 shell 转义问题
                    orig_file = _Path(_tempfile.gettempdir()) / f"devflow-orig-{task_id}-{i}.txt"
                    patch_file2 = _Path(_tempfile.gettempdir()) / f"devflow-patched-{task_id}-{i}.txt"
                    apply_script = _Path(_tempfile.gettempdir()) / f"devflow-apply-{task_id}-{i}.py"

                    orig_file.write_text(orig_snippet, encoding="utf-8")
                    patch_file2.write_text(patched_snippet, encoding="utf-8")

                    apply_script.write_text(f'''\
import sys, re
target = {_json.dumps(target)}
orig_f = {_json.dumps(str(orig_file))}
patch_f = {_json.dumps(str(patch_file2))}

with open(orig_f, "r", encoding="utf-8") as f:
    original = f.read()
with open(patch_f, "r", encoding="utf-8") as f:
    patched = f.read()

try:
    with open(target, "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print("MISSING_FILE")
    sys.exit(1)

def write_and_exit(new_content, method):
    with open(target, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("OK_" + method)
    sys.exit(0)

# Phase 1: 精确字符串匹配
if original in content:
    write_and_exit(content.replace(original, patched, 1), "EXACT")

# Phase 2: 按行模糊匹配（容忍 docstring 等中间行差异）
orig_stripped = [l.strip() for l in original.split("\\n") if l.strip()]
content_lines = content.split("\\n")
orig_raw_lines = original.strip().split("\\n")

# 用第一个有意义的原始行作为锚点
anchor = orig_stripped[0] if orig_stripped else ""
for line_idx, cl in enumerate(content_lines):
    if cl.strip() != anchor:
        continue
    # 在文件中找到锚点，检查从此处开始的匹配度
    matches = 0
    content_pos = line_idx
    for ol in orig_stripped:
        # 跳过原始内容中在文件中不连续的行（容忍插入的 docstring/注释）
        for _ in range(len(content_lines) - content_pos + 1):
            if content_pos >= len(content_lines):
                break
            if content_lines[content_pos].strip() == ol:
                matches += 1
                content_pos += 1
                break
            content_pos += 1
    if matches >= max(1, len(orig_stripped) * 0.6):
        # 找到锚定位置，替换从锚点到匹配置信区间的内容
        before = "\\n".join(content_lines[:line_idx])
        after_start = content_pos
        after = "\\n".join(content_lines[after_start:])
        new_content = before + "\\n" + patched.strip() + "\\n" + after
        while "\\n\\n\\n" in new_content:
            new_content = new_content.replace("\\n\\n\\n", "\\n\\n")
        write_and_exit(new_content, "FUZZY")

# Phase 3: 函数级替换 — 通过函数名定位并替换整个函数体
# 从 original_snippet 中提取第一个 def/class 行
func_match = re.search(r'^(\\s*)(?:def|class)\\s+(\\w+)', original, re.MULTILINE)
if func_match:
    indent = func_match.group(1)
    func_name = func_match.group(2)
    # 在目标文件中查找同名函数/类定义
    target_pattern = re.compile(
        r'^(' + re.escape(indent) + r'(?:def|class)\\s+' + re.escape(func_name) + r'\\b.*)$',
        re.MULTILINE
    )
    tm = target_pattern.search(content)
    if tm:
        func_start_line = content[:tm.start()].count("\\n")
        lines = content.split("\\n")
        # 找到函数结束位置（下一个同级 def/class 或 EOF）
        end_line = len(lines)
        for k in range(func_start_line + 1, len(lines)):
            if re.match(r'^' + re.escape(indent) + r'(?:def|class)\\s+\\w+', lines[k]):
                end_line = k
                break
            # 同级或更外层非空行（非缩进行）也结束
            if lines[k] and not lines[k].startswith(" ") and not lines[k].startswith("\\t"):
                if not lines[k].startswith(indent + " "):
                    end_line = k
                    break
        before = "\\n".join(lines[:func_start_line])
        after = "\\n".join(lines[end_line:])
        new_content = before + "\\n" + patched.strip() + "\\n" + after
        while "\\n\\n\\n" in new_content:
            new_content = new_content.replace("\\n\\n\\n", "\\n\\n")
        write_and_exit(new_content, "FUNCTION")

print("NOT_FOUND")
sys.exit(1)
''', encoding="utf-8")

                    r = await _sandbox_call(sandbox, f"python {apply_script}", timeout=30)
                    # 清理临时文件
                    orig_file.unlink(missing_ok=True)
                    patch_file2.unlink(missing_ok=True)
                    apply_script.unlink(missing_ok=True)

                    if r.exit_code == 0:
                        applied = True
                        _record_event(state, "progress",
                                      f"Patch {i} ({file_path}) 字符串替换成功 ({r.stdout.strip()})",
                                      "apply_patches")
                    else:
                        _record_event(state, "error",
                                      f"Patch {i} ({file_path}) 应用失败: git apply + 字符串替换均失败. "
                                      f"stdout=[{r.stdout.strip()[:200]}] stderr=[{r.stderr.strip()[:200]}]",
                                      "apply_patches")

                if not applied:
                    _record_event(state, "error",
                                  f"Patch {i} 应用失败: 所有方法均未能应用",
                                  "apply_patches")

        state["phase"] = "testing"
        _record_event(state, "node_complete", "仓库 clone 完成，patch 已应用", "apply_patches")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        _record_event(state, "error", f"apply_patches 异常: {e}", "apply_patches")
        cleanup_sandbox(task_id)
        state["phase"] = "failed"

    return state


async def run_tests(state: TeamState) -> TeamState:
    """测试执行节点 → 沙箱操作 [C]

    沙箱只提供 execute(command)，Agent 自行决定跑什么命令。
    当前 Agent 处于 Mock 模式时，由本节点代为执行 pytest（默认策略）。
    Agent 切换到真实模式后，由 Developer Agent 通过 sandbox_execute 工具自行控制。
    """
    if _blocked(state, "run_tests"):
        return state

    import sys
    _PY = sys.executable
    _PIP = f'"{_PY}" -m pip'

    if _USE_MOCK_SANDBOX:
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
        _record_event(state, "test_result", "测试执行完成 (Mock)", "run_tests")
        return state

    from app.tools.sandbox_ops import get_sandbox, cleanup_sandbox
    from contracts.sandbox_result import SandboxResult, TestSummary, TestFailure

    task_id = state["task_meta"]["task_id"]
    execution_id = str(uuid.uuid4())[:8]
    started_at = datetime.now()

    try:
        sandbox = get_sandbox(task_id)

        # 安装依赖：先尝试 pip install -e .，失败则检查 requirements.txt
        r = await _sandbox_call(sandbox, f"{_PIP} install -q -e .", cwd="repo", timeout=180)
        if r.exit_code != 0:
            # 检查 requirements.txt 是否存在
            check = await _sandbox_call(
                sandbox,
                f'{_PY} -c "import os; exit(0 if os.path.exists(\'requirements.txt\') else 1)"',
                cwd="repo",
            )
            if check.exit_code == 0:
                await _sandbox_call(sandbox, f"{_PIP} install -q -r requirements.txt", cwd="repo", timeout=180)

        # 运行 pytest
        import time
        start = time.time()
        r = await _sandbox_call(sandbox, f"{_PY} -m pytest --tb=short -v", cwd="repo", timeout=300)
        duration_ms = int((time.time() - start) * 1000)

        # 解析输出
        import re
        def _find(pattern, text):
            m = re.search(pattern, text)
            return int(m.group(1)) if m else 0
        passed = _find(r'(\d+)\s+passed', r.stdout)
        failed = _find(r'(\d+)\s+failed', r.stdout)
        errors = _find(r'(\d+)\s+errors?', r.stdout)
        skipped = _find(r'(\d+)\s+skipped', r.stdout)

        failures_list = []
        for match in re.finditer(r'FAILED\s+(.+)', r.stdout):
            full = match.group(1).strip()
            parts = full.split("::")
            failures_list.append(TestFailure(
                test_name=parts[-1] if parts else full,
                test_file=parts[0] if parts else "unknown",
                failure_type="assertion",
                message="测试失败",
                traceback="详见 stdout",
                is_new_failure=True,
            ).model_dump())

        result = SandboxResult(
            execution_id=execution_id,
            task_id=task_id,
            sandbox_type="test",
            status="success" if r.exit_code == 0 else "failure",
            exit_code=r.exit_code,
            timed_out=r.timed_out,
            duration_ms=duration_ms,
            stdout=r.stdout[-50000:],
            stderr=r.stderr[-10000:],
            test_summary=TestSummary(
                total=passed + failed + errors + skipped,
                passed=passed, failed=failed, errors=errors, skipped=skipped,
            ),
            test_failures=failures_list,
            started_at=started_at.isoformat(),
            finished_at=datetime.now().isoformat(),
        )
        state["sandbox_results"].append(result.model_dump())

        state["phase"] = "reviewing"
        _record_event(state, "test_result",
                      f"测试完成: {passed} passed, {failed} failed, {errors} errors",
                      "run_tests")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        state["sandbox_results"].append(
            SandboxResult(
                execution_id=execution_id, task_id=task_id,
                sandbox_type="test", status="error",
                exit_code=-1, timed_out=False, duration_ms=0,
                stdout=f"测试执行异常: {e}",
                test_summary=TestSummary(total=0, passed=0, failed=1, errors=1),
                started_at=started_at.isoformat(),
                finished_at=datetime.now().isoformat(),
            ).model_dump()
        )
        state["phase"] = "reviewing"
        _record_event(state, "error", f"run_tests 异常: {e}", "run_tests")
    finally:
        cleanup_sandbox(task_id)

    return state


async def review_code(state: TeamState) -> TeamState:
    """代码审查节点 → 调用 Reviewer Agent [B]"""
    if _blocked(state, "review_code"):
        return state
    from app.agents import ReviewerAgent, agent_node

    state["phase"] = "reviewing"
    state = await agent_node(state, ReviewerAgent())
    state["phase"] = "security_check"
    _record_event(state, "node_complete", "代码审查完成", "review_code")
    return state


async def security_check(state: TeamState) -> TeamState:
    """将 Reviewer 的安全风险转化为可审计的审批决策。"""
    if _blocked(state, "security_check"):
        return state
    from contracts.agent_result import AgentResult, AgentRole, SecurityIssue, SecurityResult

    state["phase"] = "security_check"
    review_result = (state.get("review") or {}).get("result") or {}
    security_issues = []
    for issue in review_result.get("issues") or []:
        severity = {"major": "medium", "minor": "low", "suggestion": "low"}.get(
            issue.get("severity", "low"), issue.get("severity", "low")
        )
        security_issues.append(SecurityIssue(
            vulnerability_type="reviewer_reported",
            severity=severity,
            file_path=issue.get("file_path", "unknown"),
            line_range=issue.get("line_range"),
            description=issue.get("description", "Reviewer 标记的安全风险"),
            remediation=issue.get("suggestion", "请人工确认并修复"),
        ))
    requires_approval = (
        review_result.get("risk_level") == "high"
        or any(issue.severity in {"critical", "high"} for issue in security_issues)
    )
    state["security_review"] = AgentResult(
        agent_role=AgentRole.SECURITY,
        success=True,
        result=SecurityResult(
            passed=not requires_approval,
            issues=security_issues,
            summary=("发现高风险安全问题，等待人工审批" if requires_approval else "安全审查通过"),
            requires_approval=requires_approval,
        ).model_dump(),
        reasoning="根据 Reviewer 安全风险结果生成审批决策",
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
    if _blocked(state, "await_approval"):
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
    if state.get("phase") in {"cancelled", "failed"}:
        return state

    # 尝试从最近的错误中提取上下文
    last_error_type = "unknown"
    last_error_msg = "工作流执行过程中发生错误"
    recent_node = state.get("current_node") or "unknown"
    recent_errors = state.get("errors", [])
    if recent_errors:
        last = recent_errors[-1]
        last_error_type = last.get("error_type", "unknown")
        last_error_msg = last.get("message", last_error_msg)

    state["errors"].append({
        "node": recent_node,
        "error_type": last_error_type,
        "message": last_error_msg,
        "timestamp": datetime.now().isoformat(),
        "recoverable": state.get("iteration", 0) < state.get("max_iterations", 3),
        "retry_count": state.get("iteration", 0),
    })
    if state["iteration"] >= state["max_iterations"]:
        state["phase"] = "failed"
    else:
        state["iteration"] = state.get("iteration", 0) + 1
        state["phase"] = "developing"  # 返工
    _record_event(state, "error", f"工作流错误 ({recent_node}): {last_error_msg[:80]}", "handle_error")
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
    if state.get("phase") == "failed":
        return "handle_error"
    req = state.get("requirement_analysis")
    if req is None:
        return "handle_error"
    result = req.get("result", {})
    if result.get("confidence", 0) < 0.6:
        return "await_approval"
    return "plan_solution"


def route_after_test(state: TeamState) -> Literal["review_code", "develop_changes", "handle_error"]:
    """测试后的路由：全部通过 → 审查，失败 → 返工，超迭代 → 错误。"""
    if state.get("cancel_requested") or state.get("phase") == "failed":
        return "handle_error"
    results = state.get("sandbox_results", [])
    if not results:
        return "handle_error"
    last = results[-1]
    ts = last.get("test_summary") or {}
    if last.get("status") == "success" and ts.get("failed", 0) == 0:
        return "review_code"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    return "develop_changes"


ReviewRoute = Literal["security_check", "develop_changes", "handle_error"]


def route_after_review(state: TeamState) -> ReviewRoute:
    """审查后的路由。"""
    if state.get("cancel_requested") or state.get("phase") == "failed":
        return "handle_error"
    review = state.get("review", {})
    result = review.get("result", {})
    issues = result.get("issues", []) or []
    if result.get("risk_level") == "high" or any(
        issue.get("severity") in {"critical", "high"} for issue in issues
    ):
        return "security_check"
    if result.get("passed", False):
        return "security_check"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "handle_error"
    return "develop_changes"


def route_after_security(state: TeamState) -> Literal["done", "await_approval", "handle_error"]:
    """安全审查后的路由。"""
    if state.get("phase") == "failed":
        return "handle_error"
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
            "handle_error": "handle_error",
        },
    )

    # 终端节点
    builder.add_conditional_edges(
        "await_approval",
        lambda state: (
            "handle_error" if state.get("phase") == "failed"
            else "finalize" if state.get("approval_granted") else "develop_changes"
        ),
        {"finalize": "finalize", "develop_changes": "develop_changes", "handle_error": "handle_error"},
    )
    builder.add_edge("finalize", END)
    builder.add_edge("handle_error", END)

    # 在审批节点执行前停止。API 用 aupdate_state + ainvoke(None) 从此处恢复。
    return builder.compile(checkpointer=checkpointer, interrupt_before=["await_approval"])


# =============================================================================
# 全局图实例（模块加载时编译）
# =============================================================================

graph = build_graph()


# =============================================================================
# Single Agent 图（用于消融实验基线）
# =============================================================================

async def run_single_agent(state: TeamState) -> TeamState:
    """单 Agent 节点 → 调用 SingleAgent 完成全部工作 [P18]"""
    if _blocked(state, "run_single_agent"):
        return state
    from app.agents import SingleAgent, agent_node

    state["phase"] = "analyzing"
    state = await agent_node(state, SingleAgent())
    state["phase"] = "done"
    _record_event(state, "node_complete", "Single Agent 全流程完成", "run_single_agent")
    return state


def build_single_agent_graph(checkpointer=None):
    """
    构建单 Agent 基线图（用于消融实验）。

    流程：init_task → run_single_agent → finalize → END

    与多 Agent Pipeline 对比，测量：
      - 输出质量（patch 正确性、完整性）
      - Token / 成本 / 耗时
      - 首次尝试成功率
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(TeamState)
    builder.add_node("init_task", init_task)
    builder.add_node("run_single_agent", run_single_agent)
    builder.add_node("handle_error", handle_error)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("init_task")
    builder.add_edge("init_task", "run_single_agent")
    builder.add_conditional_edges(
        "run_single_agent",
        lambda state: "handle_error" if state.get("phase") == "failed" else "finalize",
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    builder.add_edge("finalize", END)
    builder.add_edge("handle_error", END)

    return builder.compile(checkpointer=checkpointer)
