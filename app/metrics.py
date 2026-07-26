"""
Token 使用统计与费用估算。

为消融实验提供成本对比数据：
  - 单 Agent vs 多 Agent 的 Token 消耗对比
  - 各 Provider 的费用估算
"""

from pydantic import BaseModel, Field

# =============================================================================
# 模型定价表（USD / 1M tokens）
# =============================================================================

PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini":        {"input": 0.15, "output": 0.60},
    "gpt-4o":             {"input": 2.50, "output": 10.00},
    "deepseek-chat":      {"input": 0.14, "output": 0.28},
    "deepseek-reasoner":  {"input": 0.55, "output": 2.19},
    "chatanywhere":       {"input": 0.00, "output": 0.00},   # 免费中转
    "unknown":            {"input": 0.00, "output": 0.00},
}


# =============================================================================
# TokenUsage
# =============================================================================

class TokenUsage(BaseModel):
    """单次 Agent 调用的 Token 用量。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @classmethod
    def from_invocation(
        cls,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> "TokenUsage":
        """从 AgentInvocation 的元信息创建 TokenUsage。"""
        total = input_tokens + output_tokens
        cost = estimate_cost(model, input_tokens, output_tokens)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost,
        )


# =============================================================================
# 费用估算
# =============================================================================

def estimate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """
    估算一次 LLM 调用的费用。

    基于 PRICING 表中的公开价格（USD / 1M tokens）。
    未知模型返回 0.0。
    """
    pricing = PRICING.get(model, PRICING["unknown"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def estimate_pipeline_cost(
    usages: list[TokenUsage],
) -> TokenUsage:
    """
    汇总一次完整 Pipeline 调用的总用量。

    Args:
        usages: 每个 Agent 的 TokenUsage 列表

    Returns:
        汇总后的 TokenUsage（input/output/total/cost 均为求和）
    """
    return TokenUsage(
        input_tokens=sum(u.input_tokens for u in usages),
        output_tokens=sum(u.output_tokens for u in usages),
        total_tokens=sum(u.total_tokens for u in usages),
        cost_usd=round(sum(u.cost_usd for u in usages), 6),
    )


def estimate_experiment_cost(
    pipeline_cost: float,
    num_tasks: int = 20,
) -> float:
    """
    估算完整实验的总费用。

    Args:
        pipeline_cost: 单次 Pipeline 调用的费用
        num_tasks: 评测任务数量

    Returns:
        实验总费用 (USD)
    """
    return round(pipeline_cost * num_tasks, 4)
