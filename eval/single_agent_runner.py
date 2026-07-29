r"""
Single Agent 基线评测运行器（P18）。

使用单 Agent（不经过多 Agent 管道）批量运行评测任务，
收集输出质量指标，用于与多 Agent 管道对比。

用法：
    python -m eval.single_agent_runner --mode mock --tasks 5
    python -m eval.single_agent_runner --mode real --tasks 5 --output single_baseline.csv
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv(_project_root / ".env")

from app.graph import build_single_agent_graph
from contracts.state import create_initial_state
from eval.agent_quality import AgentQualityEvaluator, QualityMetrics
from eval.tasks.tasks_20 import EVAL_TASKS


class SingleAgentEvalRunner:
    """
    单 Agent 基线评测运行器。

    使用简化的单 Agent 图（无沙箱、无多 Agent 管道），
    收集输出质量指标用于消融实验对比。
    """

    def __init__(self, mode: str = "mock", output: str = ""):
        self.mode = mode
        self.output = output or f"single-agent-{mode}-{datetime.now():%Y%m%d-%H%M%S}.csv"
        self.evaluator = AgentQualityEvaluator()
        self.records: list[QualityMetrics] = []

        if mode == "real":
            os.environ["DEVFLOW_USE_MOCK"] = "false"
        else:
            os.environ["DEVFLOW_USE_MOCK"] = "true"

    async def run_all(
        self,
        tasks: list[dict[str, Any]] | None = None,
        repo_url: str = "",
    ) -> list[QualityMetrics]:
        if tasks is None:
            tasks = EVAL_TASKS

        graph = build_single_agent_graph()
        total = len(tasks)
        self.records = []

        print(f"[SingleAgentEval] mode={self.mode}  tasks={total}")
        print(f"[SingleAgentEval] output={self.output}")
        print()

        t_start = time.time()

        for i, task in enumerate(tasks):
            tid = task["id"]
            cat = task.get("category", "?")
            diff = task.get("difficulty", 0)
            print(f"  [{i+1:2d}/{total}] {tid}  {cat:12s}  diff={diff}  ", end="", flush=True)

            task_t0 = time.time()
            try:
                result = await self._run_one(graph, task, repo_url)
                metrics = self.evaluator.evaluate(task, result)
                task_elapsed = time.time() - task_t0
                status = "OK" if metrics.success else ("FAIL" if metrics.phase == "failed" else metrics.phase)
                print(f"-> {status:6s}  {task_elapsed:.1f}s", flush=True)
            except Exception as e:
                task_elapsed = time.time() - task_t0
                metrics = QualityMetrics(
                    task_id=tid, category=cat, difficulty=diff, phase="error",
                )
                print(f"-> ERROR  {task_elapsed:.1f}s  {type(e).__name__}: {str(e)[:60]}", flush=True)

            self.records.append(metrics)

        total_elapsed = time.time() - t_start
        print(f"\n[SingleAgentEval] Done - {total} tasks in {total_elapsed:.1f}s")

        return self.records

    async def _run_one(self, graph, task, repo_url):
        task_id = task["id"].replace("-", "")[:8]
        config = {"configurable": {"thread_id": f"sa-{task_id}"}}

        state = create_initial_state(
            task_id=f"sa-{task_id}",
            repo_url=repo_url or "https://github.com/example/demo-repo",
            branch="main",
            requirement=task["requirement"],
            max_iterations=1,  # 单 Agent 无返工
        )

        return await graph.ainvoke(state, config)

    def export_csv(self, path: str = "") -> str:
        output_path = path or self.output
        if not self.records:
            print("[SingleAgentEval] No records to export.")
            return output_path

        fieldnames = [
            "task_id", "category", "difficulty",
            "phase", "success", "iteration_count", "first_attempt_success",
            "structured_output_valid", "output_completeness",
            "patch_count", "patch_applicable", "diff_lines",
            "tests_total", "tests_passed", "tests_failed", "tests_pass_rate",
            "review_passed", "review_risk_level", "review_issue_count",
            "total_input_tokens", "total_output_tokens", "total_tokens",
            "total_cost_usd", "total_duration_ms",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for record in self.records:
                row = {fn: getattr(record, fn, "") for fn in fieldnames}
                row["success"] = record.success
                row["total_tokens"] = record.total_tokens
                writer.writerow(row)

        print(f"[SingleAgentEval] Exported {len(self.records)} records -> {output_path}")
        return output_path

    def print_summary(self) -> dict:
        summary = self.evaluator.summary(self.records)
        if summary.get("total", 0) == 0:
            print("[SingleAgentEval] No data to summarize.")
            return summary

        print()
        print("=" * 55)
        print("  Single Agent Baseline Summary")
        print("=" * 55)
        print(f"  Total:          {summary['total']}")
        print(f"  Success:        {summary['success_count']} ({summary['success_rate']:.0%})")
        print(f"  Avg iterations: {summary['avg_iterations']}")
        print(f"  Avg cost:       ${summary['avg_cost_usd']:.6f}")
        print(f"  Avg duration:   {summary['avg_duration_ms']}ms")
        print(f"  Total tokens:   {summary['total_tokens']}")
        print()

        # 按类别
        if summary.get("by_category"):
            print("  By category:")
            for cat, stats in sorted(summary.get("by_category", {}).items()):
                print(f"    {cat:15s}  {stats['success']}/{stats['total']}  ({stats['success_rate']:.0%})")
            print()

        # 按难度
        if summary.get("by_difficulty"):
            print("  By difficulty:")
            for diff, stats in sorted(summary.get("by_difficulty", {}).items()):
                print(f"    diff={diff}      {stats['success']}/{stats['total']}  ({stats['success_rate']:.0%})")
            print()

        return summary


# =============================================================================
# CLI
# =============================================================================


def _parse_args():
    parser = argparse.ArgumentParser(description="DevFlow Single Agent Eval Runner")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock",
                        help="Run mode (default mock)")
    parser.add_argument("--output", default="",
                        help="CSV output path")
    parser.add_argument("--repo", default="",
                        help="Target repo URL")
    parser.add_argument("--tasks", type=int, default=0,
                        help="Run only first N tasks (0=all)")
    return parser.parse_args()


def main():
    args = _parse_args()

    tasks = EVAL_TASKS
    if args.tasks > 0:
        tasks = EVAL_TASKS[:args.tasks]

    runner = SingleAgentEvalRunner(mode=args.mode, output=args.output)

    _records = asyncio.run(runner.run_all(tasks=tasks, repo_url=args.repo))
    runner.export_csv()
    runner.print_summary()


if __name__ == "__main__":
    main()
