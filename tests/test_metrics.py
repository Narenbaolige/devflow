"""Token 统计与费用估算测试。"""

import pytest

from app.metrics import (
    TokenUsage,
    estimate_cost,
    estimate_pipeline_cost,
    estimate_experiment_cost,
)


class TestTokenUsage:
    """TokenUsage 模型。"""

    def test_create_usage(self):
        u = TokenUsage(input_tokens=500, output_tokens=200, total_tokens=700, cost_usd=0.0003)
        assert u.input_tokens == 500
        assert u.output_tokens == 200
        assert u.total_tokens == 700
        assert u.cost_usd == 0.0003

    def test_from_invocation(self):
        u = TokenUsage.from_invocation(
            model="gpt-4o-mini", input_tokens=1000, output_tokens=500,
        )
        assert u.total_tokens == 1500
        assert u.cost_usd > 0  # 已知模型应有费用

    def test_from_invocation_unknown_model(self):
        u = TokenUsage.from_invocation(
            model="nonexistent-model", input_tokens=1000, output_tokens=500,
        )
        assert u.cost_usd == 0.0  # 未知模型返回 0

    def test_total_auto_computed(self):
        u = TokenUsage.from_invocation(model="unknown", input_tokens=300, output_tokens=200)
        assert u.total_tokens == 500


class TestCostEstimation:
    """费用估算函数。"""

    def test_estimate_known_model(self):
        cost = estimate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == pytest.approx(0.75)  # 0.15 + 0.60

    def test_estimate_deepseek(self):
        cost = estimate_cost("deepseek-chat", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == pytest.approx(0.42)  # 0.14 + 0.28

    def test_estimate_unknown_model_zero(self):
        cost = estimate_cost("random-model", input_tokens=1000, output_tokens=1000)
        assert cost == 0.0

    def test_estimate_zero_tokens(self):
        cost = estimate_cost("gpt-4o-mini", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_estimate_chatanywhere_free(self):
        cost = estimate_cost("chatanywhere", input_tokens=1000, output_tokens=1000)
        assert cost == 0.0  # 免费中转


class TestPipelineCost:
    """Pipeline 汇总费用。"""

    def test_pipeline_sum(self):
        usages = [
            TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150, cost_usd=0.0001),
            TokenUsage(input_tokens=200, output_tokens=100, total_tokens=300, cost_usd=0.0002),
            TokenUsage(input_tokens=300, output_tokens=150, total_tokens=450, cost_usd=0.0003),
        ]
        total = estimate_pipeline_cost(usages)
        assert total.input_tokens == 600
        assert total.output_tokens == 300
        assert total.total_tokens == 900
        assert total.cost_usd == pytest.approx(0.0006)

    def test_experiment_cost(self):
        cost = estimate_experiment_cost(pipeline_cost=0.001, num_tasks=20)
        assert cost == 0.02

    def test_experiment_cost_zero(self):
        cost = estimate_experiment_cost(pipeline_cost=0.0, num_tasks=50)
        assert cost == 0.0
