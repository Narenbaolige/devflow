r"""
D5 里程碑验证：真实 LLM + 真实沙箱端到端 Bug 修复流程。

关闭所有 Mock，用 DeepSeek + LocalSandbox 跑通完整的 bug 修复管道。

用法：
    cd D:\Dev\devflow
    python -m pytest tests/test_d5_real_pipeline.py -v -s

或直接运行：
    python tests/test_d5_real_pipeline.py
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ═══════════════════════════════════════════════════════════════════
# 关闭所有 Mock 开关
# ═══════════════════════════════════════════════════════════════════
os.environ["DEVFLOW_USE_MOCK"] = "false"
os.environ["DEVFLOW_USE_SANDBOX"] = "false"

# 现在导入 — base.py 和 graph.py 会读取新的环境变量值
from app.graph import build_graph, _USE_MOCK_SANDBOX
from app.agents.base import AgentBase
from contracts.state import create_initial_state


def check_prerequisites():
    """检查真实运行的前置条件。"""
    issues = []

    if AgentBase.USE_MOCK:
        issues.append("❌ DEVFLOW_USE_MOCK 仍为 True（环境变量未生效？）")
    else:
        print("✅ DEVFLOW_USE_MOCK = False（Agent 将使用真实 LLM）")

    if _USE_MOCK_SANDBOX:
        issues.append("❌ _USE_MOCK_SANDBOX 仍为 True（环境变量未生效？）")
    else:
        print("✅ _USE_MOCK_SANDBOX = False（将使用真实沙箱）")

    # 检查 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        issues.append("❌ DEEPSEEK_API_KEY 未设置或是示例值")
    else:
        print(f"✅ DEEPSEEK_API_KEY 已设置 (长度={len(api_key)})")

    # 检查目标仓库
    test_repo = Path("D:/Dev/devflow-test-repo")
    if not test_repo.exists() or not (test_repo / ".git").exists():
        issues.append(f"❌ 测试仓库不存在: {test_repo}")
    else:
        print(f"✅ 测试仓库存在: {test_repo}")

    # 检查 git 可用性
    import subprocess
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Git 可用: {result.stdout.strip()}")
        else:
            issues.append("❌ Git 命令不可用")
    except Exception as e:
        issues.append(f"❌ Git 检查失败: {e}")

    return issues


async def run_d5_pipeline():
    """
    运行 D5 管道：真实 LLM + 真实沙箱修复 factorial 参数校验 bug。

    测试仓库 devflow-test-repo：
      - math_utils.py: factorial 函数缺少负数/非整数校验
      - test_math_utils.py: 期望 factorial(-1) 抛出 ValueError（当前失败）

    管道需生成并应用 patch，使 factorial(-1) 抛出 ValueError。
    """
    print("\n" + "=" * 70)
    print("  D5 Pipeline: 真实 LLM + 真实沙箱端到端测试")
    print("=" * 70)
    print(f"  开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print()

    task_id = f"d5-test-{datetime.now().strftime('%H%M%S')}"
    repo_url = "D:/Dev/devflow-test-repo"  # Git for Windows 能识别此路径

    state = create_initial_state(
        task_id=task_id,
        repo_url=repo_url,
        branch="main",
        requirement=(
            "给 math_utils.py 中的 factorial 函数添加输入参数校验："
            "输入为负数时抛出 ValueError('Input must be non-negative')，"
            "输入不是整数时抛出 TypeError('Input must be an integer')。"
        ),
        max_iterations=3,
        execution_timeout_seconds=600,  # 10 分钟总超时
    )

    config = {"configurable": {"thread_id": task_id}}

    # 重新构建 graph（确保读取了更新后的环境变量）
    graph = build_graph()

    print("  开始执行管道...")
    print(f"  Task ID: {task_id}")
    print(f"  Repo: {repo_url}")
    print()

    t_start = time.time()

    try:
        result = await graph.ainvoke(state, config)
        elapsed = time.time() - t_start
    except Exception as e:
        elapsed = time.time() - t_start
        print(f"\n❌ 管道执行异常 ({elapsed:.1f}s): {type(e).__name__}: {e}")
        return False

    # ── 分析结果 ──
    print(f"\n  管道执行完成 ({elapsed:.1f}s)")
    print(f"  最终 phase: {result.get('phase')}")
    print(f"  迭代次数: {result.get('iteration')}")

    # 沙箱结果
    sandbox_results = result.get("sandbox_results", [])
    if sandbox_results:
        last = sandbox_results[-1]
        print(f"  沙箱状态: {last.get('status')}")
        if "test_summary" in last:
            ts = last["test_summary"]
            print(f"  测试结果: {ts.get('total')} total, "
                  f"{ts.get('passed')} passed, "
                  f"{ts.get('failed')} failed")

    # 成本
    budget_used = result.get("budget_used_usd", 0)
    print(f"  总成本: ${budget_used:.6f}")

    # 事件统计
    events = result.get("events", [])
    print(f"  事件数: {len(events)}")
    for evt in events:
        etype = evt.get("event_type", "?")
        msg = evt.get("message", "")
        if len(msg) > 100:
            msg = msg[:100] + "..."
        print(f"    [{etype}] {msg}")

    # 错误
    errors = result.get("errors", [])
    if errors:
        print(f"  ❌ 错误数: {len(errors)}")
        for err in errors:
            print(f"    - {err.get('message', '?')}")
    else:
        print("  ✅ 无错误")

    # ── 判断成功 ──
    phase = result.get("phase", "")
    success = phase == "done"

    if success and sandbox_results:
        last = sandbox_results[-1]
        ts = last.get("test_summary", {})
        tests_passed = ts.get("failed", 0) == 0 and ts.get("passed", 0) > 0
        if not tests_passed:
            success = False
            print(f"\n  ⚠️  管道完成但测试未全部通过")

    if success:
        print(f"\n  🎉 D5 里程碑达成！真实管道端到端成功")
    else:
        print(f"\n  ⚠️  D5 里程碑未达成 (phase={phase})")

    # ── 打印 patch 详情 ──
    patches = result.get("patches", [])
    if patches:
        print(f"\n  生成的 Patches ({len(patches)}):")
        for i, patch in enumerate(patches):
            p = patch if isinstance(patch, dict) else {}
            print(f"    [{i}] {p.get('file_path', '?')}: {p.get('change_description', '?')}")
            diff = p.get("diff", "")
            if diff:
                print(f"        diff: {diff[:200]}...")

    return success


# =============================================================================
# 主入口
# =============================================================================

def main():
    issues = check_prerequisites()
    if issues:
        print("\n前置条件检查失败:")
        for issue in issues:
            print(f"  {issue}")
        print("\n请修复后再运行。")
        return False

    print("\n前置条件全部通过，开始 D5 管道...")
    success = asyncio.run(run_d5_pipeline())

    if success:
        print("\n" + "=" * 70)
        print("  ✅ D5 验证通过")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("  ❌ D5 验证未通过")
        print("=" * 70)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
