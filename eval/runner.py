"""
评测运行器。

批量运行 20 条评测任务，收集 QualityMetrics，导出 CSV。

用法：
    # Mock 模式（秒级完成，无需 API Key）
    python -m eval.runner --mode mock

    # Real 模式（需要 DEVFLOW_USE_MOCK=false + API Key）
    python -m eval.runner --mode real

    # 指定输出文件
    python -m eval.runner --mode mock --output results.csv
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

# 确保项目根目录在 sys.path 中（直接运行时需要）
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv(_project_root / ".env")

from app.graph import build_graph
from contracts.state import create_initial_state
from eval.agent_quality import AgentQualityEvaluator, QualityMetrics
from eval.tasks.tasks_20 import EVAL_TASKS


class EvalRunner:
    """
    评测运行器。

    对每条任务：
      1. 构建初始 TeamState
      2. 调用 graph.ainvoke() 执行完整流程
      3. 提取 QualityMetrics
      4. 汇总并导出
    """

    def __init__(self, mode: str = "mock", output: str = ""):
        """
        Args:
            mode: "mock"（默认）或 "real"
            output: CSV 输出路径，默认为 results-{timestamp}.csv
        """
        self.mode = mode
        self.output = output or f"results-{mode}-{datetime.now():%Y%m%d-%H%M%S}.csv"
        self.evaluator = AgentQualityEvaluator()
        self.records: list[QualityMetrics] = []

        # 根据 mode 设置环境变量
        if mode == "real":
            os.environ["DEVFLOW_USE_MOCK"] = "false"
        else:
            os.environ["DEVFLOW_USE_MOCK"] = "true"

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def run_all(
        self,
        tasks: list[dict[str, Any]] | None = None,
        repo_url: str = "",
    ) -> list[QualityMetrics]:
        """
        批量运行所有评测任务。

        Args:
            tasks: 任务列表，默认使用 EVAL_TASKS
            repo_url: 目标仓库 URL（Mock 模式下可省略）

        Returns:
            QualityMetrics 列表
        """
        if tasks is None:
            tasks = EVAL_TASKS

        graph = build_graph()
        total = len(tasks)
        self.records = []

        print(f"[EvalRunner] mode={self.mode}  tasks={total}")
        print(f"[EvalRunner] output={self.output}")
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
                print(f"→ {status:6s}  iter={metrics.iteration_count}  {task_elapsed:.1f}s", flush=True)
            except Exception as e:
                task_elapsed = time.time() - task_t0
                metrics = QualityMetrics(
                    task_id=tid, category=cat, difficulty=diff, phase="error",
                )
                print(f"→ ERROR  {task_elapsed:.1f}s  {type(e).__name__}: {str(e)[:60]}", flush=True)

            self.records.append(metrics)

        total_elapsed = time.time() - t_start
        print(f"\n[EvalRunner] Done — {total} tasks in {total_elapsed:.1f}s")

        return self.records

    async def _run_one(self, graph, task, repo_url):
        """运行单条任务，返回 pipeline 最终状态。"""
        task_id = task["id"].replace("-", "")[:8]
        config = {"configurable": {"thread_id": task_id}}

        state = create_initial_state(
            task_id=task_id,
            repo_url=repo_url or "https://github.com/example/demo-repo",
            branch="main",
            requirement=task["requirement"],
            max_iterations=3,
        )

        return await graph.ainvoke(state, config)

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------

    def export_csv(self, path: str = "") -> str:
        """将 QualityMetrics 导出为 CSV 文件。"""
        output_path = path or self.output
        if not self.records:
            print("[EvalRunner] No records to export.")
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

        print(f"[EvalRunner] Exported {len(self.records)} records → {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------

    def print_summary(self) -> dict:
        """打印汇总统计并返回。"""
        summary = self.evaluator.summary(self.records)
        if summary.get("total", 0) == 0:
            print("[EvalRunner] No data to summarize.")
            return summary

        print()
        print("=" * 55)
        print("  Evaluation Summary")
        print("=" * 55)
        print(f"  Total:          {summary['total']}")
        print(f"  Success:        {summary['success_count']} ({summary['success_rate']:.0%})")
        print(f"  Avg iterations: {summary['avg_iterations']}")
        print(f"  Avg cost:       ${summary['avg_cost_usd']:.6f}")
        print(f"  Avg duration:   {summary['avg_duration_ms']}ms")
        print(f"  Total tokens:   {summary['total_tokens']}")
        print()
        print("  By category:")
        for cat, stats in sorted(summary.get("by_category", {}).items()):
            print(f"    {cat:15s}  {stats['success']}/{stats['total']}  ({stats['success_rate']:.0%})")
        print()
        print("  By difficulty:")
        for diff, stats in sorted(summary.get("by_difficulty", {}).items()):
            print(f"    diff={diff}      {stats['success']}/{stats['total']}  ({stats['success_rate']:.0%})")
        print()

        return summary


# =============================================================================
# CLI
# =============================================================================


def _parse_args():
    parser = argparse.ArgumentParser(description="DevFlow Eval Runner")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock",
                        help="运行模式（默认 mock）")
    parser.add_argument("--output", default="",
                        help="CSV 输出路径")
    parser.add_argument("--repo", default="",
                        help="目标仓库 URL（Mock 模式可省略）")
    parser.add_argument("--tasks", type=int, default=0,
                        help="仅运行前 N 条任务（0=全部）")
    return parser.parse_args()


def main():
    args = _parse_args()

    tasks = EVAL_TASKS
    if args.tasks > 0:
        tasks = EVAL_TASKS[:args.tasks]

    runner = EvalRunner(mode=args.mode, output=args.output)

    _records = asyncio.run(runner.run_all(tasks=tasks, repo_url=args.repo))
    runner.export_csv()
    runner.print_summary()


if __name__ == "__main__":
    main()
