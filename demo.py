#!/usr/bin/env python
r"""
DevFlow Demo Script (P23).

展示 DevFlow 多 Agent 软件工程平台的核心能力。

用法：
    # 1. 快速 Demo（Mock 模式，秒级，无需 API Key）
    python demo.py --mode mock

    # 2. 真实 LLM Demo（需要 DEEPSEEK_API_KEY）
    python demo.py --mode real

    # 3. 单 Agent vs 多 Agent 对比
    python demo.py --mode compare

    # 4. D5 验证：真实管道修复 Bug
    python demo.py --mode d5

    # 5. 交互模式
    python demo.py --mode interactive
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


# =============================================================================
# Demo 1: Mock 模式快速展示
# =============================================================================


def demo_mock():
    """Mock 模式：展示管道结构和输出格式（无需 API Key，秒级完成）。"""
    print("=" * 60)
    print("  DevFlow Demo — Mock Mode")
    print("=" * 60)
    print()
    print("Mode: Agent Mock + Sandbox Mock")
    print("All agents return predefined mock results.")
    print("No API key required. Completes in seconds.")
    print()

    os.environ["DEVFLOW_USE_MOCK"] = "true"
    from app.graph import build_graph
    from contracts.state import create_initial_state

    async def run():
        task_id = "demo-mock-001"
        state = create_initial_state(
            task_id=task_id,
            repo_url="https://github.com/example/demo-repo",
            branch="main",
            requirement="Fix: Add input validation to factorial() function",
            max_iterations=3,
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": task_id}}

        print("Pipeline: init -> analyze -> plan -> develop -> apply -> test -> review -> security")
        print()

        t0 = time.time()
        result = await graph.ainvoke(state, config)
        elapsed = time.time() - t0

        print(f"Done in {elapsed:.1f}s")
        print(f"  Phase: {result.get('phase')}")
        print(f"  Iterations: {result.get('iteration')}")
        print(f"  Events: {len(result.get('events', []))}")
        print(f"  Cost: ${result.get('budget_used_usd', 0):.6f}")

        # Show event timeline
        print()
        print("Event Timeline:")
        for evt in result.get("events", []):
            node = evt.get("node_name", "?")
            etype = evt.get("event_type", "?")
            msg = evt.get("message", "")[:100]
            if "Mock" in msg or "mock" in msg.lower():
                print(f"  [{etype}] {node}: {msg} (MOCK)")

        print()
        print("Mock mode completed successfully.")
        print("Run with --mode real to see actual LLM-powered execution.")

    asyncio.run(run())


# =============================================================================
# Demo 2: 真实 LLM 模式
# =============================================================================


def demo_real():
    """真实 LLM 模式：使用 DeepSeek 运行完整管道。"""
    print("=" * 60)
    print("  DevFlow Demo — Real LLM Mode")
    print("=" * 60)
    print()

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        print("ERROR: DEEPSEEK_API_KEY not set.")
        print("Set it in .env or run with --mode mock instead.")
        return

    print(f"Provider: {os.getenv('LLM_PROVIDER', 'deepseek')}")
    print(f"Model: {os.getenv('LLM_MODEL', 'deepseek-chat')}")
    print()

    os.environ["DEVFLOW_USE_MOCK"] = "false"
    os.environ["DEVFLOW_USE_SANDBOX"] = "true"  # real agents, mock sandbox

    from app.graph import build_graph
    from contracts.state import create_initial_state

    async def run():
        task_id = f"demo-real-{datetime.now().strftime('%H%M%S')}"
        state = create_initial_state(
            task_id=task_id,
            repo_url="https://github.com/example/demo-repo",
            branch="main",
            requirement="Fix: Add input validation to user registration — email must contain '@', username must be 3-20 chars",
            max_iterations=3,
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": task_id}}

        print("Running pipeline with real DeepSeek LLM...")
        print()

        t0 = time.time()
        result = await graph.ainvoke(state, config)
        elapsed = time.time() - t0

        print(f"Done in {elapsed:.1f}s")
        print(f"  Phase: {result.get('phase')}")
        print(f"  Iterations: {result.get('iteration')}")
        print(f"  Cost: ${result.get('budget_used_usd', 0):.6f}")
        print()

        # Show each agent's output
        print("Agent Outputs:")
        print("-" * 40)

        req = result.get("requirement_analysis", {})
        if req:
            r = req.get("result", {})
            print(f"[Requirement Agent]")
            print(f"  Summary: {r.get('summary', 'N/A')[:80]}")
            print(f"  Confidence: {r.get('confidence', 0)}")
            print()

        plan = result.get("plan", {})
        if plan:
            p = plan.get("result", {})
            print(f"[Planner Agent]")
            print(f"  Approach: {p.get('approach', 'N/A')[:100]}")
            print(f"  Steps: {len(p.get('steps', []))}")
            print(f"  Confidence: {p.get('confidence', 0)}")
            print()

        patches = result.get("patches", [])
        if patches:
            print(f"[Developer Agent] — {len(patches)} patch(es)")
            for i, patch in enumerate(patches):
                pdict = patch if isinstance(patch, dict) else {}
                print(f"  [{i}] {pdict.get('file_path', '?')}: {pdict.get('change_description', '?')}")
                diff = pdict.get("diff", "")
                if diff:
                    first_line = diff.split("\n")[0] if "\n" in diff else diff[:60]
                    print(f"      diff header: {first_line}")
            print()

        review = result.get("review", {})
        if review:
            r = review.get("result", {})
            print(f"[Reviewer Agent]")
            print(f"  Passed: {r.get('passed', False)}")
            print(f"  Risk: {r.get('risk_level', 'unknown')}")
            print(f"  Issues: {len(r.get('issues', []))}")
            print()

        # Cost breakdown
        print("-" * 40)
        print(f"Total cost: ${result.get('budget_used_usd', 0):.6f}")

        # Events with token info
        print()
        print("Token/Cost per Agent:")
        for evt in result.get("events", []):
            if evt.get("event_type") == "agent_complete":
                d = evt.get("data", {})
                print(f"  {d.get('agent', '?'):12s}  "
                      f"tokens={d.get('input_tokens', 0)}+{d.get('output_tokens', 0)}  "
                      f"cost=${d.get('cost_usd', 0):.6f}  "
                      f"time={d.get('duration_ms', 0)}ms")

    asyncio.run(run())


# =============================================================================
# Demo 3: 单 Agent vs 多 Agent 对比
# =============================================================================


def demo_compare():
    """对比模式：测量单 Agent 和多 Agent 管道的效率差异。"""
    print("=" * 60)
    print("  DevFlow Demo — Single vs Multi-Agent Comparison")
    print("=" * 60)
    print()

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        print("No API key. Running comparison report from saved data...")
        print()
        # Run the saved comparison report
        exec(open("eval/compare_report.py").read())
        return

    # Quick comparison on 3 tasks
    tasks = [
        {
            "id": "cmp-001",
            "category": "simple_fix",
            "difficulty": 1,
            "requirement": "Add input validation: negative numbers should raise ValueError",
            "acceptance_criteria": ["ValueError for negative", "normal case works"],
        },
        {
            "id": "cmp-002",
            "category": "bug_fix",
            "difficulty": 2,
            "requirement": "Fix divide by zero: return None instead of raising ZeroDivisionError",
            "acceptance_criteria": ["divide(x,0) returns None", "normal division works"],
        },
        {
            "id": "cmp-003",
            "category": "refactor",
            "difficulty": 3,
            "requirement": "Extract validation logic into a separate validate_user_data() function",
            "acceptance_criteria": ["validation function exists", "original code uses it"],
        },
    ]

    print(f"Running comparison on {len(tasks)} tasks...")
    print()

    # Single Agent
    print("--- Single Agent ---")
    os.environ["DEVFLOW_USE_MOCK"] = "false"
    from app.graph import build_single_agent_graph
    from contracts.state import create_initial_state

    async def run_single():
        graph = build_single_agent_graph()
        times = []
        costs = []
        for t in tasks:
            tid = t["id"]
            state = create_initial_state(
                task_id=f"sa-{tid}",
                repo_url="https://github.com/example/demo-repo",
                branch="main",
                requirement=t["requirement"],
                max_iterations=1,
            )
            t0 = time.time()
            result = await graph.ainvoke(state, {"configurable": {"thread_id": f"sa-{tid}"}})
            elapsed = time.time() - t0
            cost = result.get("budget_used_usd", 0)
            times.append(elapsed)
            costs.append(cost)
            review = result.get("review", {})
            r = review.get("result", {}) if isinstance(review, dict) else {}
            print(f"  {tid}: {elapsed:.1f}s  ${cost:.6f}  self_review={r.get('self_review_passed', False)}")
        return sum(times) / len(times), sum(costs) / len(costs)

    sa_avg_time, sa_avg_cost = asyncio.run(run_single())
    print(f"  Avg: {sa_avg_time:.1f}s  ${sa_avg_cost:.6f}")
    print()

    # Multi Agent
    print("--- Multi-Agent Pipeline ---")
    os.environ["DEVFLOW_USE_SANDBOX"] = "true"  # keep sandbox mock
    from app.graph import build_graph as build_multi_graph

    async def run_multi():
        graph = build_multi_graph()
        times = []
        costs = []
        for t in tasks:
            tid = t["id"]
            state = create_initial_state(
                task_id=f"ma-{tid}",
                repo_url="https://github.com/example/demo-repo",
                branch="main",
                requirement=t["requirement"],
                max_iterations=3,
            )
            t0 = time.time()
            result = await graph.ainvoke(state, {"configurable": {"thread_id": f"ma-{tid}"}})
            elapsed = time.time() - t0
            cost = result.get("budget_used_usd", 0)
            times.append(elapsed)
            costs.append(cost)
            review = result.get("review", {})
            r = review.get("result", {}) if isinstance(review, dict) else {}
            print(f"  {tid}: {elapsed:.1f}s  ${cost:.6f}  passed={r.get('passed', False)}")
        return sum(times) / len(times), sum(costs) / len(costs)

    ma_avg_time, ma_avg_cost = asyncio.run(run_multi())
    print(f"  Avg: {ma_avg_time:.1f}s  ${ma_avg_cost:.6f}")
    print()

    # Summary
    print("-" * 40)
    print(f"{'Metric':<25} {'SingleAgent':>12} {'Multi-Agent':>12}")
    print("-" * 40)
    print(f"{'Avg Time':<25} {f'{sa_avg_time:.1f}s':>12} {f'{ma_avg_time:.1f}s':>12}")
    print(f"{'Avg Cost':<25} {f'${sa_avg_cost:.6f}':>12} {f'${ma_avg_cost:.6f}':>12}")
    print(f"{'Time Ratio':<25} {'1x':>12} {f'{ma_avg_time/sa_avg_time:.1f}x':>12}")
    print(f"{'Cost Ratio':<25} {'1x':>12} {f'{ma_avg_cost/sa_avg_cost:.1f}x':>12}")


# =============================================================================
# Demo 4: D5 验证
# =============================================================================


def demo_d5():
    """D5 验证：真实管道修复 devflow-test-repo 中的 factorial bug。"""
    print("=" * 60)
    print("  DevFlow Demo — D5 Verification")
    print("=" * 60)
    print()
    print("Bug: factorial() function missing input validation")
    print("Repo: D:/Dev/devflow-test-repo")
    print("Expected: Add ValueError for negative input, TypeError for non-integer")
    print()

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        print("ERROR: DEEPSEEK_API_KEY required for D5 verification.")
        return

    test_repo = Path("D:/Dev/devflow-test-repo")
    if not (test_repo / ".git").exists():
        print("ERROR: devflow-test-repo not found. Create it first with a buggy factorial().")
        return

    os.environ["DEVFLOW_USE_MOCK"] = "false"
    os.environ["DEVFLOW_USE_SANDBOX"] = "false"

    from app.graph import build_graph
    from contracts.state import create_initial_state

    async def run():
        task_id = f"d5-demo-{datetime.now().strftime('%H%M%S')}"
        state = create_initial_state(
            task_id=task_id,
            repo_url="D:/Dev/devflow-test-repo",
            branch="main",
            requirement="Fix: Add input validation to factorial() in math_utils.py. "
                        "Negative input should raise ValueError. Non-integer should raise TypeError.",
            max_iterations=3,
            execution_timeout_seconds=300,
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": task_id}}

        print("Running D5 pipeline with real DeepSeek LLM + real sandbox...")
        print("(This clones the repo, applies patches, and runs pytest)")
        print()

        t0 = time.time()
        result = await graph.ainvoke(state, config)
        elapsed = time.time() - t0

        phase = result.get("phase", "?")
        iteration = result.get("iteration", 0)
        cost = result.get("budget_used_usd", 0)

        print(f"Done in {elapsed:.1f}s")
        print(f"  Phase: {phase}")
        print(f"  Iterations: {iteration}")
        print(f"  Cost: ${cost:.6f}")
        print()

        sandbox_results = result.get("sandbox_results", [])
        if sandbox_results:
            last = sandbox_results[-1]
            ts = last.get("test_summary", {})
            print(f"Sandbox Result:")
            print(f"  Status: {last.get('status')}")
            print(f"  Tests: {ts.get('total', 0)} total, "
                  f"{ts.get('passed', 0)} passed, {ts.get('failed', 0)} failed")
            print()

        patches = result.get("patches", [])
        if patches:
            print("Patches Generated:")
            for p in patches:
                pdict = p if isinstance(p, dict) else {}
                print(f"  File: {pdict.get('file_path', '?')}")
                print(f"  Type: {pdict.get('change_type', '?')}")
                print(f"  Description: {pdict.get('change_description', '?')}")
            print()

        # Verify result
        if phase == "done" and sandbox_results:
            ts = sandbox_results[-1].get("test_summary", {})
            if ts.get("failed", 1) == 0 and ts.get("passed", 0) > 0:
                print("=" * 40)
                print("  D5 VERIFICATION: SUCCESS")
                print(f"  All {ts['passed']} tests passed in {elapsed:.1f}s")
                print(f"  Real bug fixed by AI pipeline!")
                print("=" * 40)
            else:
                print(f"D5: Pipeline completed but {ts.get('failed', '?')} tests failed.")
        else:
            print(f"D5: Pipeline ended with phase={phase}")

    asyncio.run(run())


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="DevFlow Demo Script")
    parser.add_argument(
        "--mode",
        choices=["mock", "real", "compare", "d5", "interactive"],
        default="mock",
        help="Demo mode (default: mock)",
    )
    args = parser.parse_args()

    if args.mode == "mock":
        demo_mock()
    elif args.mode == "real":
        demo_real()
    elif args.mode == "compare":
        demo_compare()
    elif args.mode == "d5":
        demo_d5()
    elif args.mode == "interactive":
        print("Interactive mode:")
        print("  1. Mock demo")
        print("  2. Real LLM demo")
        print("  3. Single vs Multi-Agent comparison")
        print("  4. D5 verification")
        choice = input("Select (1-4): ").strip()
        modes = {"1": demo_mock, "2": demo_real, "3": demo_compare, "4": demo_d5}
        func = modes.get(choice, demo_mock)
        func()


if __name__ == "__main__":
    main()
