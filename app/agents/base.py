"""
Agent 基类与通用工具。

定义所有 Agent 的统一接口和调用模式。
"""

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from app.config import settings
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

    # Mock 模式：true（不调 LLM）/ false（真实 LLM 调用）
    # 通过环境变量 DEVFLOW_USE_MOCK 控制，默认 true（安全）
    USE_MOCK: bool = os.getenv("DEVFLOW_USE_MOCK", "true").lower() == "true"

    # LLM 调用失败时是否自动降级为 Mock 输出（保证流程不中断）
    FALLBACK_TO_MOCK_ON_ERROR: bool = False
    # Agents that generate larger artifacts may opt into a longer request
    # window than the lightweight analysis agents.
    TIMEOUT_SECONDS: int | None = None

    # 0 means no DevFlow-side context clipping. The model provider's context
    # window remains the only hard limit.
    max_context_tokens: int = 0

    # 是否启用工具调用（子类覆盖为 True 以开启）
    ENABLE_TOOL_CALLING: bool = False
    MAX_TOOL_ROUNDS: int = 5
    REQUIRE_TOOL_CALLING: bool = False
    REQUIRE_READ_FOR_EXISTING_PATCHES: bool = False

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
        在设置了正数预算时确保上下文不超出 Token 预算。

        超长时保留头部 70% + 尾部 30%，中间插入截断标记。
        未超长时原样返回。
        """
        if self.max_context_tokens <= 0:
            return context

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

        流程：
        1. Mock 模式 → mock_result(state)
        2. 工具调用模式(ENABLE_TOOL_CALLING=True) → _invoke_with_tools
        3. 纯 Prompt 模式(默认) → _invoke_prompt_only
        """
        if self.USE_MOCK:
            return self.mock_result(state)

        if llm is None:
            llm = get_llm()

        if self.ENABLE_TOOL_CALLING:
            return self._invoke_with_tools(state, llm)

        return self._invoke_prompt_only(state, llm)

    # ------------------------------------------------------------------
    # 纯 Prompt 模式（当前默认行为）
    # ------------------------------------------------------------------

    @staticmethod
    def _check_patch_quality(result_dict: dict) -> list[str]:
        """检查 patch 输出的常见 LLM 错误。返回 warning 列表（空=无问题）。"""
        import ast as _ast
        import re as _re
        warnings: list[str] = []
        patches = result_dict.get("patches", [])
        if not patches:
            return ["patches 数组为空——必须至少包含一个 patch"]
        for i, p in enumerate(patches):
            snippet = p.get("patched_snippet", "")
            if not snippet.strip():
                warnings.append(f"Patch {i}: patched_snippet 为空")
                continue
            # Check for Python syntax errors
            try:
                _ast.parse(snippet)
            except SyntaxError as e:
                warnings.append(f"Patch {i}: {e.msg} (line {e.lineno})")
            # Check for duplicate class/function definitions
            classes = _re.findall(r'^\s*class\s+(\w+)', snippet, _re.MULTILINE)
            funcs = _re.findall(r'^\s*def\s+(\w+)', snippet, _re.MULTILINE)
            dupes = [c for c in classes if classes.count(c) > 1] + [f for f in funcs if funcs.count(f) > 1]
            if dupes:
                warnings.append(f"Patch {i}: 重复定义 — {list(set(dupes))}")
            # Check for empty diff
            diff = p.get("diff", "")
            if not diff.strip():
                warnings.append(f"Patch {i}: diff 为空")
        return warnings

    def _invoke_prompt_only(self, state: TeamState, llm) -> AgentResult:
        """纯 Prompt 调用：System Prompt + Context → 结构化输出。"""
        start_time = time.time()
        retry_count = 0
        last_error = None

        try:
            context = self.build_context(state)
            context = self._clip_context(context)

            schema_json = json.dumps(
                self.output_schema.model_json_schema(), ensure_ascii=False, indent=2
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context},
                {"role": "user", "content": (
                    "请严格按照以下 JSON Schema 格式返回结果，仅输出 JSON，"
                    "不要包含额外说明文字：\n```json\n" + schema_json + "\n```"
                )},
            ]

            raw_text: str | None = None
            for attempt in range(3):
                try:
                    # Use JSON mode to force valid JSON output.  DeepSeek-chat
                    # otherwise often ignores the schema and emits free-form text.
                    try:
                        response = self._invoke_json_response(llm, messages)
                    except Exception:
                        response = llm.invoke(messages)
                    raw_text = response.content if hasattr(response, "content") else str(response)
                    from app.agents.validator import validate_against_model
                    result = validate_against_model(raw_text, self.output_schema)
                    break
                except Exception as e:
                    retry_count = attempt
                    last_error = str(e)
                    if attempt < 2:
                        hint = getattr(e, "fix_hint", str(e))
                        # Check for patch quality issues and include in hint
                        if raw_text and "patches" not in last_error.lower():
                            try:
                                from app.agents.validator import validate_against_model as _v
                                partial = _v(raw_text, self.output_schema)
                                q_warnings = self._check_patch_quality(partial.model_dump())
                                if q_warnings:
                                    hint += "\n代码质量问题:\n" + "\n".join(f"  - {w}" for w in q_warnings[:5])
                            except Exception:
                                pass
                        extra = ""
                        if "Unterminated string" in last_error:
                            extra = (
                                "\n注意: JSON 字符串值中的双引号必须转义(用 \\\" 代替 \")，"
                                "换行必须写成 \\n。例如代码片段应该写成: "
                                "\"def foo():\\n    return 1\""
                            )
                        messages.append({
                            "role": "user",
                            "content": (
                                f"上一次输出格式有误，请修正后重新输出。\n错误: {hint}{extra}"
                            ),
                        })
            else:
                raise RuntimeError(
                    f"Agent 调用 {retry_count + 1} 次重试后全部失败: {last_error}"
                )

            duration_ms = int((time.time() - start_time) * 1000)

            try:
                meta = getattr(response, "response_metadata", {}) or {}
                usage = meta.get("token_usage", {}) or meta.get("usage", {})
                input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
            except Exception:
                input_tokens = 0
                output_tokens = 0

            return AgentResult(
                agent_role=self.role, success=True, result=result.model_dump(),
                invocation=AgentInvocation(
                    agent_role=self.role,
                    model=getattr(llm, "model", "unknown"),
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    cost_usd=estimate_cost(
                        getattr(llm, "model", "unknown"), input_tokens, output_tokens
                    ),
                    duration_ms=duration_ms, retry_count=retry_count,
                ),
                reasoning=f"{self.role.value} Agent 调用完成",
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            last_error = str(e)

            if self.FALLBACK_TO_MOCK_ON_ERROR:
                fallback = self.mock_result(state)
                fallback.reasoning = (
                    f"[FALLBACK] LLM 调用失败后降级为 Mock — "
                    f"错误: {last_error[:100]}"
                )
                fallback.invocation = AgentInvocation(
                    agent_role=self.role, model="mock-fallback",
                    retry_count=retry_count + 1, duration_ms=duration_ms,
                )
                return fallback

            return AgentResult(
                agent_role=self.role, success=False,
                error=f"Agent 调用失败: {last_error}",
                invocation=AgentInvocation(
                    agent_role=self.role, model="unknown",
                    retry_count=retry_count + 1, duration_ms=duration_ms,
                ),
                reasoning="调用失败", next_action="retry",
            )

    # ------------------------------------------------------------------
    # 工具调用模式
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_assistant_message(response, tool_calls: list[dict]) -> dict:
        """Build the assistant turn that precedes tool-result messages.

        Reasoning-capable OpenAI-compatible providers may return an opaque
        ``reasoning_content`` value together with a tool call. Their APIs
        require that value to be returned unchanged on the next request.
        """
        message = {
            "role": "assistant",
            "content": getattr(response, "content", "") or "",
            "tool_calls": tool_calls,
        }
        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        reasoning_content = additional_kwargs.get("reasoning_content")
        if reasoning_content is not None:
            message["reasoning_content"] = reasoning_content
        return message

    @staticmethod
    def _invoke_json_response(llm, messages):
        """Request a syntactically valid JSON object from the final turn.

        Tool-use turns must remain unconstrained so the model can emit tool
        calls. Once tool use is complete, JSON mode prevents multiline patch
        snippets from being emitted as invalid, unescaped JSON strings.
        """
        return llm.bind(response_format={"type": "json_object"}).invoke(messages)

    @staticmethod
    def _tool_call_args(tool_call: dict) -> dict:
        """Read arguments from both LangChain and raw OpenAI tool-call forms."""
        args = tool_call.get("args", tool_call.get("arguments", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return {}
        return args if isinstance(args, dict) else {}

    def _tool_evidence_error(
        self, result: BaseModel, tool_call_count: int, read_files: set[str]
    ) -> str | None:
        """Reject ungrounded patches before they reach the patch applier."""
        if self.REQUIRE_TOOL_CALLING and tool_call_count == 0:
            return "在交付最终结果前必须先调用工具检索仓库。"
        if not self.REQUIRE_READ_FOR_EXISTING_PATCHES:
            return None
        missing = []
        for patch in result.model_dump().get("patches", []):
            if patch.get("change_type") == "add":
                continue
            file_path = str(patch.get("file_path", "")).removeprefix("repo/")
            if file_path and file_path not in read_files:
                missing.append(file_path)
        if missing:
            return "修改已有文件前必须先用 read_file 读取其真实内容：" + ", ".join(missing)
        return None

    def _invoke_with_tools(self, state: TeamState, llm) -> AgentResult:
        """带工具调用的 Agent 执行：LLM 可在沙箱中读文件/搜索/执行命令。"""
        from app.tools.registry import get_tools_for_agent
        from app.tools.tool_impls import TOOL_IMPL_MAP

        tools = get_tools_for_agent(self.role.value)
        if not tools:
            return self._invoke_prompt_only(state, llm)

        start_time = time.time()
        task_id = state.get("task_meta", {}).get("task_id", "default")
        context = self._clip_context(self.build_context(state))
        schema_json = json.dumps(
            self.output_schema.model_json_schema(), ensure_ascii=False, indent=2
        )

        # Build tool definitions in OpenAI function-calling format
        tool_defs = []
        for t in tools:
            params = t.parameters or {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": t.description},
                },
            }
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": params,
                },
            })

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context},
            {"role": "user", "content": (
                "你可以使用工具在沙箱中执行操作（读文件、搜索代码、运行命令）。\n"
                "获取足够信息后，请严格按照以下 JSON Schema 格式输出最终结果：\n```json\n"
                + schema_json + "\n```"
            )},
        ]

        total_input = 0
        total_output = 0
        validation_retries = 0
        model_name = getattr(llm, "model", "unknown")
        tool_call_count = 0
        read_files: set[str] = set()

        for round_num in range(self.MAX_TOOL_ROUNDS):
            try:
                response = llm.invoke(messages, tools=tool_defs)
            except Exception as exc:
                import logging
                _log = logging.getLogger("devflow.agent")
                _log.warning(
                    "工具调用模式失败: %s: %s，降级到纯提示词模式",
                    type(exc).__name__, str(exc)[:200],
                )
                return self._invoke_prompt_only(state, llm)

            # Track tokens
            try:
                meta = getattr(response, "response_metadata", {}) or {}
                usage = meta.get("token_usage", {}) or meta.get("usage", {})
                total_input += usage.get("input_tokens", usage.get("prompt_tokens", 0))
                total_output += usage.get("output_tokens", usage.get("completion_tokens", 0))
            except Exception:
                pass

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # No tool calls → this should be the final output
                raw_text = response.content if hasattr(response, "content") else str(response)
                try:
                    from app.agents.validator import validate_against_model
                    result = validate_against_model(raw_text, self.output_schema)
                    evidence_error = self._tool_evidence_error(result, tool_call_count, read_files)
                    if evidence_error:
                        last_error = f"证据不足: {evidence_error}"
                        validation_retries += 1
                        messages.append({
                            "role": "user",
                            "content": evidence_error + " 请先完成检索，再重新输出最终 JSON。",
                        })
                        continue
                    duration_ms = int((time.time() - start_time) * 1000)
                    return AgentResult(
                        agent_role=self.role, success=True, result=result.model_dump(),
                        invocation=AgentInvocation(
                            agent_role=self.role, model=model_name,
                            input_tokens=total_input, output_tokens=total_output,
                            cost_usd=estimate_cost(model_name, total_input, total_output),
                            duration_ms=duration_ms, retry_count=validation_retries,
                        ),
                        reasoning=f"{self.role.value} Agent 调用完成（{round_num}轮工具调用）",
                    )
                except Exception as exc:
                    # Output wasn't valid JSON → ask LLM to fix
                    validation_retries += 1
                    fix_hint = getattr(exc, "fix_hint", str(exc))
                    messages.append({
                        "role": "user",
                        "content": (
                            "上一份输出无法通过 JSON Schema 校验。只输出完整 JSON，"
                            "不要截断、不要 Markdown、不要附加解释。\n"
                            f"校验错误：{fix_hint}"
                        ),
                    })
                    continue

            # Preserve the complete assistant turn before adding one result
            # message per call.  Splitting it into several assistant messages
            # loses provider-specific reasoning state and breaks multi-tool
            # responses.
            messages.append(self._tool_assistant_message(response, tool_calls))

            # Execute tool calls
            for tc in tool_calls:
                func_name = tc.get("name", "")
                func_args = self._tool_call_args(tc)
                tool_call_count += 1
                if func_name == "read_file":
                    file_path = str(func_args.get("file_path", "")).removeprefix("repo/")
                    if file_path:
                        read_files.add(file_path)

                impl = TOOL_IMPL_MAP.get(func_name)
                if impl:
                    try:
                        tool_result = impl(task_id=task_id, **func_args)
                    except Exception as e:
                        tool_result = f"[工具执行异常] {type(e).__name__}: {e}"
                else:
                    tool_result = f"[未知工具] {func_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{round_num}"),
                    "content": str(tool_result),
                })

        # Max tool rounds reached — force final output
        messages.append({
            "role": "user",
            "content": "已达最大工具调用轮次。基于已获取的信息，输出最终 JSON 结果。",
        })
        last_error = None
        try:
            for attempt in range(3):
                response = self._invoke_json_response(llm, messages)
                raw_text = response.content if hasattr(response, "content") else str(response)
                try:
                    from app.agents.validator import validate_against_model
                    result = validate_against_model(raw_text, self.output_schema)
                    evidence_error = self._tool_evidence_error(result, tool_call_count, read_files)
                    if evidence_error:
                        last_error = f"证据不足: {evidence_error}"
                        validation_retries += 1
                        messages.append({
                            "role": "user",
                            "content": evidence_error + " 请先完成检索，再重新输出最终 JSON。",
                        })
                        continue
                    duration_ms = int((time.time() - start_time) * 1000)
                    return AgentResult(
                        agent_role=self.role, success=True, result=result.model_dump(),
                        invocation=AgentInvocation(
                            agent_role=self.role, model=model_name,
                            input_tokens=total_input, output_tokens=total_output,
                            cost_usd=estimate_cost(model_name, total_input, total_output),
                            duration_ms=duration_ms, retry_count=validation_retries,
                        ),
                        reasoning=f"{self.role.value} Agent 调用完成（达最大工具轮次）",
                    )
                except Exception as exc:
                    last_error = str(exc)
                    validation_retries += 1
                    if attempt < 2:
                        fix_hint = getattr(exc, "fix_hint", str(exc))
                        messages.append({
                            "role": "user",
                            "content": (
                                "上一份最终输出不是完整有效的 JSON。仅重新输出完整 JSON 对象，"
                                "不得截断、不得输出 Markdown 或解释。\n"
                                f"校验错误：{fix_hint}"
                            ),
                        })
            # 如果 3 次都因 evidence_error 走 continue，last_error 可能仍为 None
            raise RuntimeError(
                f"最终 JSON 在 3 次尝试后仍无效：{last_error or '缺少检索证据（未读取相关文件或工具调用不足）'}"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if self.FALLBACK_TO_MOCK_ON_ERROR:
                fallback = self.mock_result(state)
                fallback.reasoning = f"[FALLBACK] 工具调用后输出解析失败: {e}"
                return fallback
            return AgentResult(
                agent_role=self.role, success=False,
                error=f"工具调用后输出解析失败: {e}",
                reasoning="调用失败", next_action="retry",
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
    started_at = time.monotonic()
    try:
        invocation = asyncio.to_thread(agent.invoke, state)
        timeout = agent.TIMEOUT_SECONDS or settings.AGENT_TIMEOUT_SECONDS
        result = await asyncio.wait_for(invocation, timeout=timeout) if timeout else await invocation
    except TimeoutError:
        # A blocking SDK call may still finish in its worker thread, but it can
        # no longer hold the workflow hostage.  Respect each agent's fallback
        # policy: production agents must expose the upstream timeout instead of
        # silently fabricating a Mock result.
        duration_ms = int((time.monotonic() - started_at) * 1000)
        if agent.FALLBACK_TO_MOCK_ON_ERROR:
            result = agent.mock_result(state)
            result.reasoning = "[FALLBACK] Agent 调用超时，已降级为 Mock 输出"
            result.invocation = AgentInvocation(
                agent_role=agent.role,
                model="mock-fallback",
                retry_count=1,
                duration_ms=duration_ms,
            )
        else:
            result = AgentResult(
                agent_role=agent.role,
                success=False,
                error=f"Agent 调用超时（{agent.TIMEOUT_SECONDS or settings.AGENT_TIMEOUT_SECONDS} 秒）",
                invocation=AgentInvocation(
                    agent_role=agent.role,
                    model=getattr(agent, "model", "unknown"),
                    retry_count=1,
                    duration_ms=duration_ms,
                ),
                reasoning="调用超时",
                next_action="retry",
            )

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
    if result.reasoning and "[FALLBACK]" in result.reasoning:
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

    # Do not continue a production workflow with missing or stale agent
    # output. Continuing here used to let later nodes test the unmodified
    # repository and report a misleading success.
    if not result.success:
        state["phase"] = "failed"
        state.setdefault("errors", []).append({
            "node": state.get("current_node") or agent_name,
            "error_type": "agent_invocation",
            "message": result.error or f"{agent_name} Agent 未返回有效结果",
            "timestamp": datetime.now().isoformat(),
            "recoverable": False,
            "retry_count": result.invocation.retry_count if result.invocation else 0,
        })
        state.setdefault("events", []).append({
            "event_id": str(uuid.uuid4()),
            "task_id": state["task_meta"]["task_id"],
            "event_type": "error",
            "node_name": state.get("current_node", ""),
            "timestamp": datetime.now().isoformat(),
            "message": result.error or f"{agent_name} Agent 调用失败",
            "data": {"phase": state.get("phase"), "agent": agent_name},
        })
        return state

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
                state[field] = result.result.get("patches", [])
        else:
            state[field] = result.model_dump()

    return state
