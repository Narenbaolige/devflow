"""
Agent 基类与通用工具。

定义所有 Agent 的统一接口和调用模式。
"""

import time
from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.llm.factory import get_llm
from contracts.agent_result import AgentInvocation, AgentResult, AgentRole
from contracts.state import TeamState


class AgentBase(ABC):
    """
    Agent 抽象基类。

    所有 Agent 必须实现：
      - role: AgentRole 枚举
      - system_prompt: System Prompt 文本
      - output_schema: 结构化输出的 Pydantic 模型类
      - build_context(state): 从 TeamState 中提取本 Agent 需要的上下文
    """

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Agent 角色标识。"""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System Prompt 文本。"""

    @property
    @abstractmethod
    def output_schema(self) -> type[BaseModel]:
        """结构化输出的 Pydantic 模型。"""

    @abstractmethod
    def build_context(self, state: TeamState) -> str:
        """
        从 TeamState 中提取本 Agent 需要的上下文。

        核心设计：每个 Agent 只看到完成任务所需的最小信息。
        返回的是拼装好的 prompt 文本。
        """

    def invoke(self, state: TeamState, llm=None) -> AgentResult:
        """
        调用 Agent。

        完整流程：
        1. build_context: 提取上下文
        2. LLM 调用: System Prompt + Context → 结构化输出
        3. 校验: Pydantic 验证
        4. 包装: AgentResult

        Returns:
            AgentResult，success=True 表示调用成功且输出合法。
        """
        start_time = time.time()

        if llm is None:
            llm = get_llm()

        context = self.build_context(state)

        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context},
        ]

        # 调用 LLM（带结构化输出）
        retry_count = 0
        last_error = None

        for attempt in range(3):  # 最多 3 次尝试（含格式修复）
            try:
                structured_llm = llm.with_structured_output(self.output_schema)
                result = structured_llm.invoke(messages)
                break
            except Exception as e:
                retry_count = attempt
                last_error = str(e)
                if attempt < 2:
                    # 格式错误 → 在 prompt 中加入错误提示后重试
                    messages.append({
                        "role": "user",
                        "content": (
                            f"你的上一次输出不符合要求的 JSON Schema。\n"
                            f"错误: {e}\n"
                            f"请严格按照 {self.output_schema.model_json_schema()} 的格式重新输出。"
                        ),
                    })
        else:
            # 3 次尝试全部失败
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_role=self.role,
                success=False,
                error=f"Agent 调用失败（{retry_count + 1} 次重试后）: {last_error}",
                invocation=AgentInvocation(
                    agent_role=self.role,
                    model="unknown",
                    retry_count=retry_count + 1,
                    duration_ms=duration_ms,
                ),
                reasoning="调用失败",
                next_action="retry",
            )

        duration_ms = int((time.time() - start_time) * 1000)

        # 尝试获取 Token 信息（取决于 LLM provider）
        try:
            # 部分 provider 在 response_metadata 中返回 token 信息
            input_tokens = 0
            output_tokens = 0
        except Exception:
            input_tokens = 0
            output_tokens = 0

        return AgentResult(
            agent_role=self.role,
            success=True,
            result=result.model_dump() if hasattr(result, "model_dump") else result,
            invocation=AgentInvocation(
                agent_role=self.role,
                model=getattr(llm, "model_name", "unknown"),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                retry_count=retry_count,
            ),
            reasoning=f"{self.role.value} Agent 调用完成",
        )


async def agent_node(state: TeamState, agent: AgentBase) -> TeamState:
    """
    LangGraph 节点包装器。

    在 graph.py 中，每个节点调用此函数来运行 Agent。

    用法：
        async def analyze_requirement(state: TeamState) -> TeamState:
            agent = RequirementAgent()
            return await agent_node(state, agent)

    Agent 的输出会自动写入 state 中的对应字段。
    """
    result = agent.invoke(state)

    # 根据 Agent 角色写入不同字段
    field_map = {
        AgentRole.REQUIREMENT: "requirement_analysis",
        AgentRole.PLANNER: "plan",
        AgentRole.DEVELOPER: "patches",
        AgentRole.REVIEWER: "review",
        AgentRole.SECURITY: "security_review",
    }

    field = field_map.get(agent.role)
    if field:
        if field == "patches":
            # Developer Agent 返回多个 Patch，用 append reducer
            if result.success and result.result:
                # AgentResult.result 是 dict，但 patches 期望 list[dict]
                state[field] = [result.model_dump()]
        else:
            state[field] = result.model_dump()

    return state
