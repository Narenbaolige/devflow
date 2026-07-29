"""
LLM 工厂。

统一 LLM 创建入口，支持多 Provider 切换。
继承自 agentic-rag 项目的 llm_factory 模式。
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_llm():
    """
    获取全局 LLM 实例（单例缓存）。

    根据环境变量 LLM_PROVIDER 自动选择 Provider。
    支持的 Provider:
      - openai:       标准 OpenAI
      - deepseek:     DeepSeek API（兼容 OpenAI 接口）
      - chatanywhere: ChatAnywhere 中转（兼容 OpenAI 接口）
    """
    return create_llm(
        provider=settings.LLM_PROVIDER,
        model=settings.get_model_name(),
        timeout=settings.AGENT_TIMEOUT_SECONDS,
    )


def create_llm(
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> ChatOpenAI:
    """
    创建 LLM 实例。

    所有 Provider 通过兼容 OpenAI 接口的 ChatOpenAI 统一创建。
    差异仅在 api_key 和 base_url。

    Args:
        provider: Provider 名称 (openai / deepseek / chatanywhere)
        model: 模型名称
        temperature: 温度参数（Agent 场景建议 0.1，降低随机性）
        max_tokens: 最大输出 token
        timeout: 超时秒数
    """
    if provider == "deepseek":
        kwargs = dict(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com/v1",
        )
    elif provider == "chatanywhere":
        kwargs = dict(
            api_key=settings.CHATANYWHERE_API_KEY,
            base_url=settings.CHATANYWHERE_BASE_URL,
        )
    else:  # openai
        kwargs = dict(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )

    # 过滤空值
    kwargs = {k: v for k, v in kwargs.items() if v}

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )
