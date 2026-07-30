"""
DevFlow Application — 基于 LangGraph 的多 Agent 协同智能体系统。
"""

# Load .env BEFORE any class attribute evaluation — AgentBase.USE_MOCK and
# ENABLE_TOOL_CALLING are evaluated at class-definition time and will read
# stale defaults if load_dotenv() runs later.
from dotenv import load_dotenv as _load_dotenv  # noqa: E402

_load_dotenv()

__version__ = "0.1.0"
