"""
Agent 质量评测。

对单次 Agent 调用或多 Agent Pipeline 输出进行多维度自动打分。
不依赖真实 LLM——可处理 Mock 和 Real 两种模式的输出。

用法：
    from eval.agent_quality import AgentQualityEvaluator, QualityMetrics

    evaluator = AgentQualityEvaluator()
    metrics = evaluator.evaluate(task, agent_result, sandbox_result)
    print(metrics.model_dump())
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class QualityMetrics:
    """单次评测任务的 Agent 质量指标。"""

    # 任务标识
    task_id: str = ""
    category: str = ""
    difficulty: int = 0

    # 结构化输出质量
    structured_output_valid: bool = False
    required_fields_filled: int = 0      # 填了多少个必填字段
    total_required_fields: int = 0       # 总共多少必填字段
    output_completeness: float = 0.0     # required / total

    # 开发结果质量
    patch_count: int = 0                 # 生成的 patch 数量
    patch_applicable: bool = False       # diff 是否看起来有效（含 @@ 标记）
    diff_lines: int = 0                  # diff 总行数

    # 测试结果
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_pass_rate: float = 0.0         # passed / total

    # 迭代与效率
    iteration_count: int = 0             # 实际迭代次数
    first_attempt_success: bool = False  # 是否首次通过
    phase: str = "unknown"               # 最终阶段

    # Token 与成本
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0

    # 审查结果
    review_passed: bool = False
    review_risk_level: str = "unknown"
    review_issue_count: int = 0

    # 计算字段
    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def success(self) -> bool:
        """任务是否成功完成（phase=done 且 review_passed）。"""
        return self.phase == "done" and self.review_passed


class AgentQualityEvaluator:
    """
    Agent 质量评测器。

    对单条任务的 Agent 输出进行多维度评分。
    同时支持 4-Agent Pipeline 和 SingleAgent 两种模式。
    """

    def evaluate(
        self,
        task: dict[str, Any],
        pipeline_result: dict[str, Any],
    ) -> QualityMetrics:
        """
        从评测任务定义和 Pipeline 最终状态中提取质量指标。

        Args:
            task: 评测任务 dict（来自 tasks_20.py 的 EVAL_TASKS）
            pipeline_result: graph.ainvoke 返回的最终 TeamState

        Returns:
            QualityMetrics 实例
        """
        m = QualityMetrics()

        # ── 任务元信息 ──
        m.task_id = task.get("id", "")
        m.category = task.get("category", "")
        m.difficulty = task.get("difficulty", 0)

        # ── 最终状态 ──
        m.phase = pipeline_result.get("phase", "unknown")
        m.iteration_count = pipeline_result.get("iteration", 0)
        m.first_attempt_success = m.phase == "done" and m.iteration_count <= 1

        # ── 结构化输出质量 ──
        self._evaluate_output_quality(m, task, pipeline_result)

        # ── 开发结果 ──
        self._evaluate_patches(m, pipeline_result)

        # ── 测试结果 ──
        self._evaluate_tests(m, pipeline_result)

        # ── 审查结果 ──
        self._evaluate_review(m, pipeline_result)

        # ── Token / 成本 ──
        self._evaluate_tokens(m, pipeline_result)

        return m

    # ------------------------------------------------------------------
    # 各维度子评估
    # ------------------------------------------------------------------

    def _evaluate_output_quality(self, m: QualityMetrics, task, result):
        """评估结构化输出的字段填充率。兼容多 Agent Pipeline 和 SingleAgent。"""
        ac = task.get("acceptance_criteria", [])
        m.total_required_fields = 1 + len(ac)  # summary + acceptance_criteria
        m.required_fields_filled = 0

        # 检查 requirement_analysis（多 Agent Pipeline）
        req = result.get("requirement_analysis", {})
        req_result = req.get("result", {}) if isinstance(req, dict) else {}
        summary = req_result.get("summary", "")
        criteria = req_result.get("acceptance_criteria", [])

        # 若无 requirement_analysis，检查 review（SingleAgent 输出在此字段）
        if not summary:
            review = result.get("review", {})
            review_result = review.get("result", {}) if isinstance(review, dict) else {}
            summary = review_result.get("summary", "")
            criteria = review_result.get("acceptance_criteria", [])

        if summary:
            m.required_fields_filled += 1
        if criteria:
            m.required_fields_filled += len(criteria)

        m.structured_output_valid = m.required_fields_filled > 0
        m.output_completeness = (
            m.required_fields_filled / max(m.total_required_fields, 1)
        )

    def _evaluate_patches(self, m: QualityMetrics, result):
        """评估生成的 patch 质量。兼容多 Agent Pipeline 和 SingleAgent。"""
        patches = result.get("patches", []) or []
        # SingleAgent 的 patches 藏在 review.result.patches 中
        if not patches:
            review = result.get("review", {}) or {}
            review_result = review.get("result", {}) or {}
            patches = review_result.get("patches", []) or []

        m.patch_count = len(patches)
        m.patch_applicable = False
        m.diff_lines = 0

        for p in patches:
            diff = p.get("diff", "")
            m.diff_lines += len(diff.splitlines())
            # 检查 diff 是否包含 unified diff 标记
            if diff.startswith("@@") or "@@ " in diff:
                m.patch_applicable = True

    def _evaluate_tests(self, m: QualityMetrics, result):
        """从 sandbox_results 提取测试指标。"""
        sandbox = result.get("sandbox_results", []) or []
        if sandbox:
            last = sandbox[-1]
            ts = last.get("test_summary", {}) or {}
            m.tests_total = ts.get("total", 0)
            m.tests_passed = ts.get("passed", 0)
            m.tests_failed = ts.get("failed", 0)
            m.tests_pass_rate = (
                m.tests_passed / max(m.tests_total, 1)
            )

    def _evaluate_review(self, m: QualityMetrics, result):
        """从 review 字段提取审查结果。兼容多 Agent Pipeline 和 SingleAgent。"""
        review = result.get("review", {}) or {}
        r = review.get("result", {}) or {}
        # 多 Agent Pipeline 使用 passed；SingleAgent 使用 self_review_passed
        m.review_passed = r.get("passed", r.get("self_review_passed", False))
        m.review_risk_level = r.get("risk_level", "unknown")
        # SingleAgent 使用 self_review_issues
        issues = r.get("issues", r.get("self_review_issues", [])) or []
        m.review_issue_count = len(issues)

    def _evaluate_tokens(self, m: QualityMetrics, result):
        """从 events 中累加各 Agent 的 Token 消耗。"""
        events = result.get("events", []) or []
        for evt in events:
            if evt.get("event_type") != "agent_complete":
                continue
            data = evt.get("data", {}) or {}
            m.total_input_tokens += data.get("input_tokens", 0)
            m.total_output_tokens += data.get("output_tokens", 0)
            m.total_cost_usd += data.get("cost_usd", 0)
            m.total_duration_ms += data.get("duration_ms", 0)

    # ------------------------------------------------------------------
    # 批量汇总
    # ------------------------------------------------------------------

    def summary(self, metrics_list: list[QualityMetrics]) -> dict:
        """
        对一批 QualityMetrics 进行汇总统计。

        Returns:
            {
                "total": int,
                "success_count": int,
                "success_rate": float,
                "avg_iterations": float,
                "avg_cost_usd": float,
                "avg_duration_ms": float,
                "total_tokens": int,
                "by_category": {category: {success_rate, count, ...}},
                "by_difficulty": {difficulty: {success_rate, count, ...}},
            }
        """
        total = len(metrics_list)
        if total == 0:
            return {"total": 0}

        successes = [m for m in metrics_list if m.success]
        costs = [m.total_cost_usd for m in metrics_list]
        durations = [m.total_duration_ms for m in metrics_list]
        tokens = [m.total_tokens for m in metrics_list]

        # 按 category 分组
        by_category = {}
        for m in metrics_list:
            cat = m.category or "unknown"
            if cat not in by_category:
                by_category[cat] = {"total": 0, "success": 0}
            by_category[cat]["total"] += 1
            if m.success:
                by_category[cat]["success"] += 1
        for cat in by_category:
            by_category[cat]["success_rate"] = round(
                by_category[cat]["success"] / max(by_category[cat]["total"], 1), 3
            )

        # 按 difficulty 分组
        by_difficulty = {}
        for m in metrics_list:
            diff = str(m.difficulty)
            if diff not in by_difficulty:
                by_difficulty[diff] = {"total": 0, "success": 0}
            by_difficulty[diff]["total"] += 1
            if m.success:
                by_difficulty[diff]["success"] += 1
        for diff in by_difficulty:
            by_difficulty[diff]["success_rate"] = round(
                by_difficulty[diff]["success"] / max(by_difficulty[diff]["total"], 1), 3
            )

        return {
            "total": total,
            "success_count": len(successes),
            "success_rate": round(len(successes) / total, 3),
            "avg_iterations": round(sum(m.iteration_count for m in metrics_list) / total, 2),
            "avg_cost_usd": round(sum(costs) / total, 6),
            "avg_duration_ms": int(sum(durations) / total),
            "total_tokens": sum(tokens),
            "by_category": by_category,
            "by_difficulty": by_difficulty,
        }
