"""LLM 工厂测试。"""

import os

from app.llm.factory import create_llm


class TestLLMFactory:
    """LLM 工厂验证。"""

    def test_create_llm_returns_chatopenai(self):
        """create_llm 应返回 ChatOpenAI 实例。"""
        from langchain_openai import ChatOpenAI

        # 设置虚拟 API key 避免 OpenAI 初始化报错
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
        os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")

        llm = create_llm(provider="openai", model="gpt-4o-mini")
        assert isinstance(llm, ChatOpenAI)

    def test_create_llm_with_temperature(self):
        """temperature 参数应生效。"""
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

        llm = create_llm(temperature=0.3)
        assert llm.temperature == 0.3
