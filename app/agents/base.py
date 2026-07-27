"""
Agent 基类与通用工具。

定义所有 Agent 的统一接口和调用模式。
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.llm.factory import get_llm
from app.metrics import estimate_cost
from contracts.agent_result import AgentInvocation, AgentResult, AgentRole
from contracts.state import TeamState


class AgentBase(ABC):
    """
    Agent 抽象基类。

    所有 Agent 必须实现：
      - role: AgentRole 枚举
      - _load_system_prompt(): 加载 System Prompt 文本（基类自动缓存）
      - output_schema: 结构化输出的 Pydantic 模型类
      - build_context(state): 从 TeamState 中提取本 Agent 需要的上下文
      - mock_result(state): 返回 Mock 的 AgentResult（Day 2 使用）
    """

    # Day 2: True（Mock 模式，不调 LLM）；Day 3+: False（真实 LLM 调用）
    USE_MOCK: bool = True

    # LLM 调用失败时是否自动降级为 Mock 输出（保证流程不中断）
    FALLBACK_TO_MOCK_ON_ERROR: bool = True

    # 上下文 Token 预算（粗糙估计：1 token ≈ 4 字符）
    max_context_tokens: int = 2000

    # System Prompt 缓存
    _cached_prompt: str | None = None

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Agent 角色标识。"""

    @property
    def system_prompt(self) -> str:
        """System Prompt 文本（自动缓存，首次访问后不再读盘）。"""
        if self._cached_prompt is None:
            self._cached_prompt = self._load_system_prompt()
        return self._cached_prompt

    @abstractmethod
    def _load_system_prompt(self) -> str:
        """
        加载 System Prompt 文本。子类实现，基类自动缓存。

        只在首次访问 system_prompt property 时调用一次。
        """

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

    # ------------------------------------------------------------------
    # 上下文裁剪
    # ------------------------------------------------------------------

    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        基础输入过滤 — 防止明显的 Prompt 注入。

        规则：
          - 移除常见的 Prompt 注入分隔符
          - 截断超长输入（纯防御，非 token 预算裁剪）

        不会影响正常需求文本。
        """
        # 移除注入常用分隔符（攻击者试图突破 System Prompt 限制）
        dangerous = [
            "Ignore all previous instructions",
            "Ignore previous instructions",
            "Disregard all previous",
            "SYSTEM:",
            "<|im_start|>",
            "<|im_end|>",
            "Previous prompt ended",
        ]
        for pattern in dangerous:
            if pattern.lower() in text.lower():
                text = text.replace(pattern, "[FILTERED]")

        # 防御性长度限制（单个用户输入不超过 10K 字符）
        max_len = 10_000
        if len(text) > max_len:
            text = text[:max_len] + "\n\n[... 输入过长，已截断 ...]"

        return text

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        粗糙 Token 估算（1 token ≈ 4 字符）。

        不引入 tiktoken 等额外依赖，用于预算控制足够。
        """
        return max(1, len(text) // 4)

    def _clip_context(self, context: str) -> str:
        """
        确保上下文不超出 Token 预算。

        超长时保留头部 70% + 尾部 30%，中间插入截断标记。
        未超长时原样返回。
        """
        estimated = self._estimate_tokens(context)
        if estimated <= self.max_context_tokens:
            return context

        # 按字符比例裁剪（token 和字符近似线性）
        max_chars = self.max_context_tokens * 4
        head_chars = int(max_chars * 0.7)
        tail_chars = int(max_chars * 0.3)

        head = context[:head_chars]
        tail = context[-tail_chars:]
        marker = (
            f"\n\n[... 上下文已截断：原始 {estimated} tokens → "
            f"裁剪至 {self.max_context_tokens} tokens ...]\n\n"
        )
        return head + marker + tail

    # ------------------------------------------------------------------
    # Mock
    # ------------------------------------------------------------------

    @abstractmethod
    def mock_result(self, state: TeamState) -> AgentResult:
        """
        返回 Mock 的 AgentResult。

        USE_MOCK=True 时调用此方法，不经过 LLM。
        每个 Agent 各自实现，返回合法的结构化假数据。
        Day 3 切换真实 LLM 后不再使用。
        """

    # ------------------------------------------------------------------
    # 调用
    # ------------------------------------------------------------------

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
        # Mock 模式：直接返回假数据，不调 LLM
        if self.USE_MOCK:
            return self.mock_result(state)

        start_time = time.time()
        retry_count = 0
        last_error = None

        try:
            if llm is None:
                llm = get_llm()

            context = self.build_context(state)
            context = self._clip_context(context)

            # 构建消息
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context},
            ]

            for attempt in range(3):  # 最多 3 次尝试（含格式修复）
                try:
                    structured_llm = llm.with_structured_output(self.output_schema)
                    result = structured_llm.invoke(messages)
                    break
                except Exception as e:
                    retry_count = attempt
                    last_error = str(e)
                    if attempt < 2:
                        messages.append({
                            "role": "user",
                            "content": (
                                f"你的上一次输出不符合要求的 JSON Schema。\n"
                                f"错误: {e}\n"
                                f"请严格按照 "
                                f"{self.output_schema.model_json_schema()} 的格式重新输出。"
                            ),
                        })
            else:
                # 3 次尝试全部失败
                raise RuntimeError(
                    f"Agent 调用 {retry_count + 1} 次重试后全部失败: {last_error}"
                )

            duration_ms = int((time.time() - start_time) * 1000)

            # 尝试获取 Token 信息（取决于 LLM provider）
            try:
                meta = getattr(result, "response_metadata", {}) or {}
                usage = meta.get("token_usage", {}) or meta.get("usage", {})
                input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
            except Exception:
                input_tokens = 0
                output_tokens = 0

            # 校验结构化输出（处理 LangChain 解析器未能捕获的边缘情况）
            if isinstance(result, str):
                from app.agents.validator import validate_against_model
                result = validate_against_model(result, self.output_schema)
            elif isinstance(result, dict):
                result = self.output_schema.model_validate(result)

            return AgentResult(
                agent_role=self.role,
                success=True,
                result=result.model_dump() if hasattr(result, "model_dump") else result,
                invocation=AgentInvocation(
                    agent_role=self.role,
                    model=getattr(llm, "model", "unknown"),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=estimate_cost(
                        getattr(llm, "model", "unknown"), input_tokens, output_tokens
                    ),
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                ),
                reasoning=f"{self.role.value} Agent 调用完成",
            )

        except Exception as e:
            # LLM 调用失败 → 降级或返回错误
            duration_ms = int((time.time() - start_time) * 1000)
            last_error = str(e)

            if self.FALLBACK_TO_MOCK_ON_ERROR:
                fallback = self.mock_result(state)
                fallback.reasoning = (
                    f"[FALLBACK] LLM 调用失败后降级为 Mock — "
                    f"错误: {last_error[:100]}"
                )
                fallback.invocation = AgentInvocation(
                    agent_role=self.role,
                    model="mock-fallback",
                    retry_count=retry_count + 1,
                    duration_ms=duration_ms,
                )
                return fallback

            return AgentResult(
                agent_role=self.role,
                success=False,
                error=f"Agent 调用失败: {last_error}",
                invocation=AgentInvocation(
                    agent_role=self.role,
                    model="unknown",
                    retry_count=retry_count + 1,
                    duration_ms=duration_ms,
                ),
                reasoning="调用失败",
                next_action="retry",
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
    # ── P3: 调用前检查 — 任务已取消则跳过 Agent 调用 ──
    if state.get("cancel_requested"):
        return state

    # LLM 调用是同步 SDK 操作；放在线程中避免阻塞 API 事件循环，
    # 使取消、状态查询等请求仍可被处理。
    result = await asyncio.to_thread(agent.invoke, state)

    # ── P3: 调用后检查 — 调用期间被取消则不写入产出物 ──
    if state.get("cancel_requested"):
        return state

    agent_name = agent.role.value

    # ── P2: 统一记录 Agent 调用费用 ──
    if result.invocation and result.invocation.cost_usd:
        state["budget_used_usd"] = round(
            state.get("budget_used_usd", 0.0) + float(result.invocation.cost_usd), 6
        )

    # ── P4: Agent 级别事件记录 ──
    if not result.success and result.reasoning and "[FALLBACK]" in result.reasoning:
        state.setdefault("events", []).append({
            "event_id": str(uuid.uuid4()),
            "task_id": state["task_meta"]["task_id"],
            "event_type": "agent_fallback",
            "node_name": state.get("current_node", ""),
            "timestamp": datetime.now().isoformat(),
            "message": f"{agent_name} Agent LLM 调用失败，已降级为 Mock",
            "data": {"phase": state.get("phase"), "agent": agent_name},
        })

    if result.invocation:
        state.setdefault("events", []).append({
            "event_id": str(uuid.uuid4()),
            "task_id": state["task_meta"]["task_id"],
            "event_type": "agent_complete",
            "node_name": state.get("current_node", ""),
            "timestamp": datetime.now().isoformat(),
            "message": (
                f"{agent_name} Agent 完成 — "
                f"model={result.invocation.model}, "
                f"tokens={result.invocation.input_tokens}+{result.invocation.output_tokens}, "
                f"cost=${result.invocation.cost_usd:.4f}, "
                f"duration={result.invocation.duration_ms}ms, "
                f"retries={result.invocation.retry_count}"
            ),
            "data": {
                "phase": state.get("phase"),
                "agent": agent_name,
                "model": result.invocation.model,
                "input_tokens": result.invocation.input_tokens,
                "output_tokens": result.invocation.output_tokens,
                "cost_usd": result.invocation.cost_usd,
                "duration_ms": result.invocation.duration_ms,
                "retry_count": result.invocation.retry_count,
            },
        })

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
            # Developer Agent 返回 PatchResult，存入 patches 列表。
            # 注意：patches 使用 merge_by_file reducer（按 file_path 去重），
            # 因此直接存 PatchResult 字典而非 AgentResult 包装——否则 reducer
            # 找不到 file_path 字段，所有 patch 会被错误合并为一个。
            if result.success and result.result:
                state[field] = [result.result]
        else:
            state[field] = result.model_dump()

    return state
