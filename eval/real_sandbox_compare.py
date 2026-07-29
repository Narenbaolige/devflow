r"""
真实沙箱对比评测（P19 — 单 Agent vs 多 Agent 管道）。

对 devflow-test-repo 中的真实 bug，分别在真实沙箱中运行：
  - SingleAgent：生成 patch → 沙箱 apply + pytest
  - MultiAgent：完整管道（含 Reviewer + 返工）→ 沙箱 apply + pytest

用法：python -m eval.real_sandbox_compare [--tasks N] [--output results.csv]
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv(_project_root / ".env")


# ── 10 条代表性评测任务 ──
EVAL_TASKS = [
    {"id": "cmp-001", "category": "simple_fix", "difficulty": 1,
     "requirement": "给 math_utils.py 中的 factorial 函数添加参数校验：负数抛 ValueError，非整数抛 TypeError"},
    {"id": "cmp-002", "category": "simple_fix", "difficulty": 1,
     "requirement": "给 math_utils.py 中的 divide 函数添加除零保护：除数为 0 时返回 None"},
    {"id": "cmp-003", "category": "bug_fix", "difficulty": 2,
     "requirement": "修复 search.py 中 binary_search 的 off-by-one 错误：查找最后一个元素和单元素数组时应正确返回索引"},
    {"id": "cmp-004", "category": "bug_fix", "difficulty": 2,
     "requirement": "修复 config_loader.py 中 parse_config 函数：文件不存在时应返回 {} 而非抛 FileNotFoundError"},
    {"id": "cmp-005", "category": "bug_fix", "difficulty": 2,
     "requirement": "修复 item_processor.py 中 process_items 函数：传入空列表[]应返回[]，不抛 IndexError"},
    {"id": "cmp-006", "category": "refactor", "difficulty": 3,
     "requirement": "将 user_service.py 中 create()和 update()的重复校验逻辑提取到 validators.py 的 validate_user_data 函数中"},
    {"id": "cmp-007", "category": "feature", "difficulty": 3,
     "requirement": "为 calculator.py 的 Calculator 类添加 power(a,b)方法：计算 a 的 b 次方，支持 b=0 和 b<0"},
    {"id": "cmp-008", "category": "edge_case", "difficulty": 2,
     "requirement": "确保 file_handler.py 的 read_file/write_file 正确处理包含中文和特殊字符的文件名"},
    # Additional tasks for broader coverage
    {"id": "cmp-009", "category": "simple_fix", "difficulty": 1,
     "requirement": "给 math_utils.py 中的 fibonacci 函数添加 docstring，含参数和返回值说明"},
    {"id": "cmp-010", "category": "refactor", "difficulty": 2,
     "requirement": "简化 item_processor.py 中 process_items 函数的实现，使用更简洁的方式处理空列表"},
]


@dataclass
class TaskResult:
    task_id: str
    category: str
    difficulty: int
    # Single Agent
    sa_success: bool = False
    sa_passed: int = 0
    sa_failed: int = 0
    sa_cost: float = 0.0
    sa_time: float = 0.0
    sa_iterations: int = 0
    # Multi Agent
    ma_success: bool = False
    ma_passed: int = 0
    ma_failed: int = 0
    ma_cost: float = 0.0
    ma_time: float = 0.0
    ma_iterations: int = 0
    # Derived
    ma_fixed_sa_failed: bool = False  # Multi-agent fixed what single couldn't
    rework_helped: bool = False  # Multi-agent needed rework but succeeded


class RealSandboxComparator:
    """真实沙箱对比评测器。"""

    def __init__(self, repo_url: str, output: str = ""):
        self.repo_url = repo_url
        self.output = output or f"real-compare-{datetime.now():%Y%m%d-%H%M%S}.csv"
        self.results: list[TaskResult] = []

    async def run(self, tasks: list[dict] | None = None, limit: int = 0):
        tasks = tasks or EVAL_TASKS
        if limit > 0:
            tasks = tasks[:limit]

        total = len(tasks)
        print(f"[RealCompare] tasks={total} repo={self.repo_url}")
        print()

        for i, task in enumerate(tasks):
            tid = task["id"]
            cat = task.get("category", "?")
            diff = task.get("difficulty", 0)
            req = task["requirement"][:80]
            print(f"[{i+1}/{total}] {tid} ({cat}, diff={diff})")
            print(f"  Req: {req}")

            r = TaskResult(task_id=tid, category=cat, difficulty=diff)

            # ── Single Agent ──
            print("  SingleAgent...", end=" ", flush=True)
            sa = await self._run_single(task)
            r.sa_success = sa["test_passed"]
            r.sa_passed = sa["passed"]
            r.sa_failed = sa["failed"]
            r.sa_cost = sa["cost"]
            r.sa_time = sa["time"]
            r.sa_iterations = sa["iterations"]
            status = f"{sa['passed']}/{sa['passed']+sa['failed']} passed" if not sa["test_passed"] else "OK"
            print(f"{status} ({sa['time']:.1f}s, ${sa['cost']:.6f})")

            # ── Multi Agent ──
            print("  MultiAgent...", end=" ", flush=True)
            ma = await self._run_multi(task)
            r.ma_success = ma["test_passed"]
            r.ma_passed = ma["passed"]
            r.ma_failed = ma["failed"]
            r.ma_cost = ma["cost"]
            r.ma_time = ma["time"]
            r.ma_iterations = ma["iterations"]
            status = f"{ma['passed']}/{ma['passed']+ma['failed']} passed" if not ma["test_passed"] else "OK"
            print(f"{status} ({ma['time']:.1f}s, iter={ma['iterations']}, ${ma['cost']:.6f})")

            # Derived metrics
            r.ma_fixed_sa_failed = r.ma_success and not r.sa_success
            r.rework_helped = r.ma_success and r.ma_iterations > 1

            if r.ma_fixed_sa_failed:
                print("  >>> Multi-agent FIXED what SingleAgent could not!")
            elif r.rework_helped:
                print(f"  >>> Rework loop helped (iter={r.ma_iterations})")

            self.results.append(r)
            print()

        return self.results

    async def _run_single(self, task: dict) -> dict:
        """用 SingleAgent 图 + 真实沙箱执行。"""
        os.environ["DEVFLOW_USE_MOCK"] = "false"
        os.environ["DEVFLOW_USE_SANDBOX"] = "false"

        from app.graph import build_single_agent_graph
        from contracts.state import create_initial_state

        task_id = f"sa-{task['id']}-{int(time.time())}"
        state = create_initial_state(
            task_id=task_id, repo_url=self.repo_url, branch="main",
            requirement=task["requirement"], max_iterations=1,
            execution_timeout_seconds=300,
        )
        graph = build_single_agent_graph()
        config = {"configurable": {"thread_id": task_id}}

        t0 = time.time()
        try:
            # SingleAgent graph doesn't include sandbox nodes, so we need to apply + test manually
            result = await graph.ainvoke(state, config)
            elapsed = time.time() - t0
            return await self._apply_and_test(task_id, result, elapsed)
        except Exception as e:
            elapsed = time.time() - t0
            return {"test_passed": False, "passed": 0, "failed": 1,
                    "cost": 0, "time": elapsed, "iterations": 0, "error": str(e)}

    async def _run_multi(self, task: dict) -> dict:
        """用多 Agent 管道图 + 真实沙箱执行。"""
        os.environ["DEVFLOW_USE_MOCK"] = "false"
        os.environ["DEVFLOW_USE_SANDBOX"] = "false"

        from app.graph import build_graph
        from contracts.state import create_initial_state

        task_id = f"ma-{task['id']}-{int(time.time())}"
        state = create_initial_state(
            task_id=task_id, repo_url=self.repo_url, branch="main",
            requirement=task["requirement"], max_iterations=3,
            execution_timeout_seconds=600,
        )
        graph = build_graph()
        config = {"configurable": {"thread_id": task_id}}

        t0 = time.time()
        try:
            result = await graph.ainvoke(state, config)
            elapsed = time.time() - t0

            sr = result.get("sandbox_results", [])
            last = sr[-1] if sr else {}
            ts = last.get("test_summary") or {}

            return {
                "test_passed": ts.get("failed", 1) == 0 and ts.get("passed", 0) > 0,
                "passed": ts.get("passed", 0),
                "failed": ts.get("failed", 0),
                "cost": result.get("budget_used_usd", 0),
                "time": elapsed,
                "iterations": result.get("iteration", 0),
            }
        except Exception as e:
            elapsed = time.time() - t0
            return {"test_passed": False, "passed": 0, "failed": 1,
                    "cost": 0, "time": elapsed, "iterations": 0, "error": str(e)}

    async def _apply_and_test(self, task_id: str, pipeline_result: dict, time_sec: float) -> dict:
        """对于 SingleAgent 结果，在真实沙箱中 apply patch + run pytest。"""
        from app.graph import _sandbox_call
        from app.tools.sandbox_ops import cleanup_sandbox, get_sandbox

        sandbox = None
        try:
            sandbox = get_sandbox(task_id)

            # Clone
            r = await _sandbox_call(
                sandbox, f"git clone --depth 1 --branch main {self.repo_url} repo", timeout=120,
            )
            if r.exit_code != 0:
                return {"test_passed": False, "passed": 0, "failed": 1,
                        "cost": 0, "time": time_sec, "iterations": 0}

            # Extract patches from SingleAgent result (stored in review field)
            review = pipeline_result.get("review", {})
            review_result = review.get("result", {}) if isinstance(review, dict) else {}
            patches = review_result.get("patches", [])

            if not patches:
                # Try the regular patches field
                patches = pipeline_result.get("patches", [])

            # Apply patches
            import json as _json
            import tempfile as _tempfile
            _Path = type(Path())  # noqa: N806
            for i, p in enumerate(patches):
                pdict = p if isinstance(p, dict) else {}
                diff = pdict.get("diff", "")
                fp = pdict.get("file_path", "")
                orig = pdict.get("original_snippet", "")
                patched = pdict.get("patched_snippet", "")

                if not diff and not (orig and patched):
                    continue

                # Normalize file_path
                if ":" in fp:
                    fp = fp.rsplit(":", 1)[-1]
                fp = fp.lstrip("\\").lstrip("/")

                # Try git apply
                pf = _Path(_tempfile.gettempdir()) / f"cmp-patch-{task_id}-{i}.diff"
                pf.write_text(diff, encoding="utf-8")
                r = await _sandbox_call(sandbox, f"git apply --verbose {pf}", cwd="repo")
                pf.unlink(missing_ok=True)

                if r.exit_code != 0 and orig and patched and fp:
                    # Fallback: string replacement
                    target = f"repo/{fp}"
                    orig_f = _Path(_tempfile.gettempdir()) / f"cmp-orig-{task_id}-{i}.txt"
                    patch_f = _Path(_tempfile.gettempdir()) / f"cmp-patched-{task_id}-{i}.txt"
                    script = _Path(_tempfile.gettempdir()) / f"cmp-apply-{task_id}-{i}.py"

                    orig_f.write_text(orig, encoding="utf-8")
                    patch_f.write_text(patched, encoding="utf-8")
                    script.write_text(f'''\
import sys, re
target = {_json.dumps(target)}
with open({_json.dumps(str(orig_f))}, encoding="utf-8") as f: orig = f.read()
with open({_json.dumps(str(patch_f))}, encoding="utf-8") as f: patched = f.read()
with open(target, encoding="utf-8") as f: content = f.read()
if orig in content:
    content = content.replace(orig, patched, 1)
    with open(target, "w", encoding="utf-8") as f: f.write(content)
    print("OK_EXACT")
else:
    func_name = re.search(r"def\\s+(\\w+)", orig)
    if func_name:
        fn = func_name.group(1)
        lines = content.split("\\n")
        for li, line in enumerate(lines):
            if f"def {{fn}}(" in line:
                end = len(lines)
                for k in range(li+1, len(lines)):
                    if lines[k] and not lines[k].startswith(" ") and not lines[k].startswith("\\t"):
                        if lines[k].startswith("def ") or lines[k].startswith("class "):
                            end = k; break
                lines = lines[:li] + patched.strip().split("\\n") + lines[end:]
                with open(target, "w", encoding="utf-8") as f: f.write("\\n".join(lines))
                print("OK_FUNC")
                break
        else:
            print("NOT_FOUND")
''', encoding="utf-8")
                    r = await _sandbox_call(sandbox, f"python {script}", timeout=30)
                    orig_f.unlink(missing_ok=True)
                    patch_f.unlink(missing_ok=True)
                    script.unlink(missing_ok=True)

            # Install deps + run pytest
            r = await _sandbox_call(sandbox, "pip install -q -e . 2>&1 || pip install -q pytest 2>&1", cwd="repo", timeout=180)
            r = await _sandbox_call(sandbox, "python -m pytest --tb=short -v 2>&1 | tail -40", cwd="repo", timeout=300)

            import re
            _passed = len(re.findall(r"(\d+)\s+passed", r.stdout))
            _failed = len(re.findall(r"(\d+)\s+failed", r.stdout))
            # Fallback: count PASSED/FAILED
            if not _passed and not _failed:
                _passed = r.stdout.count("PASSED")
                _failed = r.stdout.count("FAILED")

            return {
                "test_passed": _failed == 0 and _passed > 0,
                "passed": _passed,
                "failed": _failed,
                "cost": pipeline_result.get("budget_used_usd", 0),
                "time": time_sec,
                "iterations": pipeline_result.get("iteration", 0),
            }
        finally:
            if sandbox:
                cleanup_sandbox(task_id)

    def export_csv(self, path: str = ""):
        output = path or self.output
        if not self.results:
            return output
        with open(output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "task_id", "category", "difficulty",
                "sa_success", "sa_passed", "sa_failed", "sa_cost", "sa_time",
                "ma_success", "ma_passed", "ma_failed", "ma_cost", "ma_time", "ma_iterations",
                "ma_fixed_sa_failed", "rework_helped",
            ])
            w.writeheader()
            for r in self.results:
                w.writerow({
                    "task_id": r.task_id, "category": r.category, "difficulty": r.difficulty,
                    "sa_success": r.sa_success, "sa_passed": r.sa_passed, "sa_failed": r.sa_failed,
                    "sa_cost": round(r.sa_cost, 6), "sa_time": round(r.sa_time, 1),
                    "ma_success": r.ma_success, "ma_passed": r.ma_passed, "ma_failed": r.ma_failed,
                    "ma_cost": round(r.ma_cost, 6), "ma_time": round(r.ma_time, 1),
                    "ma_iterations": r.ma_iterations,
                    "ma_fixed_sa_failed": r.ma_fixed_sa_failed, "rework_helped": r.rework_helped,
                })
        print(f"[RealCompare] Exported {len(self.results)} records -> {output}")
        return output

    def print_summary(self):
        if not self.results:
            return
        sa_ok = sum(1 for r in self.results if r.sa_success)
        ma_ok = sum(1 for r in self.results if r.ma_success)
        fixed = sum(1 for r in self.results if r.ma_fixed_sa_failed)
        rework = sum(1 for r in self.results if r.rework_helped)
        total = len(self.results)

        print()
        print("=" * 65)
        print("  Real Sandbox Comparison Results")
        print("=" * 65)
        print(f"  Tasks:                {total}")
        print(f"  SingleAgent success:  {sa_ok}/{total} ({sa_ok/total:.0%})")
        print(f"  MultiAgent success:   {ma_ok}/{total} ({ma_ok/total:.0%})")
        print(f"  MA fixed SA failures: {fixed}")
        print(f"  Rework helped:        {rework}")
        print(f"  Avg SA cost:          ${sum(r.sa_cost for r in self.results)/total:.6f}")
        print(f"  Avg MA cost:          ${sum(r.ma_cost for r in self.results)/total:.6f}")
        print(f"  Avg SA time:          {sum(r.sa_time for r in self.results)/total:.1f}s")
        print(f"  Avg MA time:          {sum(r.ma_time for r in self.results)/total:.1f}s")
        print()

        # Per category
        cats = {}
        for r in self.results:
            c = r.category
            if c not in cats:
                cats[c] = {"total": 0, "sa": 0, "ma": 0}
            cats[c]["total"] += 1
            if r.sa_success: cats[c]["sa"] += 1
            if r.ma_success: cats[c]["ma"] += 1
        print("  By category:")
        for c, s in sorted(cats.items()):
            print(f"    {c:15s}  SA={s['sa']}/{s['total']}  MA={s['ma']}/{s['total']}")
        print()

        # Verdict
        if ma_ok > sa_ok:
            print(f"  VERDICT: Multi-agent pipeline outperforms SingleAgent by {ma_ok-sa_ok} tasks")
            if fixed:
                print(f"           Rework loop fixed {fixed} tasks that SingleAgent couldn't solve")
        elif ma_ok == sa_ok:
            print(f"  VERDICT: Both approaches tied at {ma_ok}/{total}")
        else:
            print("  VERDICT: SingleAgent outperformed — investigate why")
        print()


# ── CLI ──
def _parse_args():
    p = argparse.ArgumentParser(description="Real sandbox comparison")
    p.add_argument("--tasks", type=int, default=0, help="Run first N tasks (0=all)")
    p.add_argument("--output", default="", help="CSV output path")
    p.add_argument("--repo", default="D:/Dev/devflow-test-repo", help="Target repo path")
    return p.parse_args()


def main():
    args = _parse_args()
    comparator = RealSandboxComparator(repo_url=args.repo, output=args.output)
    asyncio.run(comparator.run(tasks=EVAL_TASKS, limit=args.tasks))
    comparator.export_csv()
    comparator.print_summary()


if __name__ == "__main__":
    main()
