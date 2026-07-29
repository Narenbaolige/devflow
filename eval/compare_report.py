r"""
P19 Comparison: Multi-Agent Pipeline vs Single Agent baseline.
Based on 20 eval tasks (5 categories x 4 difficulties), real DeepSeek LLM, Mock sandbox.
"""

multi = {
    "success": "20/20 (100%)",
    "avg_cost": 0.001306,
    "avg_duration_ms": 18535,
    "total_tokens": 158500,
    "total_time_s": 374.1,
    "avg_iterations": 1.0,
    "agent_calls": 4,
}

single = {
    "success": "20/20 (100%)",
    "avg_cost": 0.000416,
    "avg_duration_ms": 8069,
    "total_tokens": 42605,
    "total_time_s": 164.4,
    "avg_iterations": 0.0,
    "agent_calls": 1,
}

# Pre-compute formatted strings to avoid f-string backslash issue
m_cost = f"${multi['avg_cost']:.6f}"
s_cost = f"${single['avg_cost']:.6f}"
m_time = f"{multi['avg_duration_ms']}ms"
s_time = f"{single['avg_duration_ms']}ms"
m_tok = f"{multi['total_tokens']:,}"
s_tok = f"{single['total_tokens']:,}"
m_total = f"{multi['total_time_s']}s"
s_total = f"{single['total_time_s']}s"

cost_ratio = multi["avg_cost"] / single["avg_cost"]
time_ratio = multi["avg_duration_ms"] / single["avg_duration_ms"]
token_ratio = multi["total_tokens"] / single["total_tokens"]

print("=" * 65)
print("  P19: Multi-Agent Pipeline vs Single Agent Comparison")
print("=" * 65)
print()
print(f"{'Metric':<32} {'Multi-Agent':>15} {'SingleAgent':>15}")
print("-" * 65)
print(f"{'Success Rate':<32} {multi['success']:>15} {single['success']:>15}")
print(f"{'Avg Cost/Task':<32} {m_cost:>15} {s_cost:>15}")
print(f"{'Avg Duration/Task':<32} {m_time:>15} {s_time:>15}")
print(f"{'Total Tokens':<32} {m_tok:>15} {s_tok:>15}")
print(f"{'Total Time':<32} {m_total:>15} {s_total:>15}")
print(f"{'LLM Calls/Task':<32} {multi['agent_calls']:>15} {single['agent_calls']:>15}")
print()

ratio_cost = f"{cost_ratio:.1f}x cost"
ratio_time = f"{time_ratio:.1f}x slower"
ratio_tok = f"{token_ratio:.1f}x tokens"
print("-" * 65)
print(f"{'Multi/Single Ratio':<32} {ratio_cost:>15} {ratio_time:>15}")
print(f"{'':<32} {ratio_tok:>15}")
print()

print("Key Findings:")
print("  1. Output quality: Both achieve 100% structured output rate")
print(f"  2. Efficiency: SingleAgent costs {s_cost}/task; multi-agent is {cost_ratio:.1f}x more")
print(f"  3. Tokens: Multi-agent uses {token_ratio:.1f}x tokens (4 agents each with system prompts)")
print("  4. Real value: Multi-agent pipeline's advantage is the sandbox feedback loop")
print("     (test failure -> review -> rework). Not captured in mock sandbox mode.")
print("  5. Recommendation: SingleAgent for simple fixes; multi-agent for complex bugs")
print("     requiring iterative repair with test validation.")
print()
print("Note: This comparison uses mock sandbox (always returns 10/10 passed).")
print("In D5 real sandbox verification, the pipeline fixed the bug in 1 iteration.")
print("Multi-agent pipeline value manifests in real execution with test feedback.")
