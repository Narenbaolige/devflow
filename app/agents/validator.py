"""
结构化输出校验器。

处理 LLM 原始输出的解析、校验与重试。
可独立使用，也可集成到 AgentBase.invoke() 流程中。

核心流程：
  1. extract_json(): 从 LLM 原始文本中提取 JSON
  2. validate_against_model(): Pydantic 校验
  3. 校验失败 → 生成修复提示 → 重试（最多 3 次）
  4. 重试耗尽 → 抛出 ValidationError（由 AgentBase 捕获后 fallback）
"""

import json
import re
import time
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

T = TypeVar("T", bound=BaseModel)

# =============================================================================
# 异常
# =============================================================================


class ValidationError(Exception):
    """校验失败异常。包含可返给 LLM 的修复提示。"""

    def __init__(self, message: str, fix_hint: str = ""):
        super().__init__(message)
        self.fix_hint = fix_hint or message


# =============================================================================
# JSON 提取
# =============================================================================


def extract_json(text: str) -> str:
    """
    从 LLM 原始文本中提取 JSON 字符串。

    处理常见情况：
      - ```json ... ``` 代码块
      - ``` ... ``` 代码块（无语言标记）
      - 直接 JSON
      - 前缀文本 + JSON + 后缀文本

    Returns:
        提取出的 JSON 字符串（去除了代码块包裹和前后空白）

    Raises:
        ValidationError: 无法找到 JSON
    """
    if not text or not text.strip():
        raise ValidationError("LLM 输出为空", "请输出有效的 JSON 对象")

    text = text.strip()

    # 1. 尝试 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        inner = m.group(1).strip()
        if inner.startswith("{") or inner.startswith("["):
            return inner

    # 2. 尝试直接找到最外层 {} 或 []
    # 从第一个 { 或 [ 开始，找到匹配的闭合
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    raise ValidationError(
        f"无法从 LLM 输出中提取 JSON 对象。输出开头: {text[:120]}...",
        "请将输出包裹在 ```json ... ``` 代码块中，或直接输出 JSON 对象",
    )


# =============================================================================
# 校验
# =============================================================================


def validate_against_model(
    raw_text: str,
    target_model: type[T],
    *,
    strict: bool = False,
) -> T:
    """
    将 LLM 原始文本解析并校验为目标 Pydantic 模型。

    Args:
        raw_text: LLM 原始输出文本
        target_model: 目标 Pydantic 模型类
        strict: 是否严格模式（禁止额外字段）

    Returns:
        校验通过的 Pydantic 模型实例

    Raises:
        ValidationError: JSON 提取失败 或 Pydantic 校验失败
    """
    json_str = extract_json(raw_text)

    # 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # 尝试修复常见 JSON 错误
        cleaned = _try_repair_json(json_str)
        if cleaned is not None:
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                raise ValidationError(
                    f"JSON 解析失败: {e}",
                    _build_json_fix_hint(json_str, e),
                ) from e
        else:
            raise ValidationError(
                f"JSON 解析失败: {e}",
                _build_json_fix_hint(json_str, e),
            ) from e

    # Pydantic 校验
    try:
        return target_model.model_validate(data, strict=strict)
    except PydanticValidationError as e:
        raise ValidationError(
            f"Pydantic 校验失败 ({e.error_count()} 个错误)",
            _build_pydantic_fix_hint(e),
        ) from e


def _try_repair_json(text: str) -> str | None:
    """尝试修复常见的 JSON 语法错误。返回修复后的字符串或 None。"""
    # 1. 移除尾部多余逗号: {"a": 1,} → {"a": 1}
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    # 2. 单引号 → 双引号（简单情况）
    if repaired != text:
        return repaired
    return None


def _build_json_fix_hint(json_str: str, error: json.JSONDecodeError) -> str:
    """构建 JSON 解析错误的修复提示。"""
    snippet_start = max(0, error.pos - 30)
    snippet_end = min(len(json_str), error.pos + 30)
    snippet = json_str[snippet_start:snippet_end]
    return (
        f"JSON 格式无效（位置 {error.pos}）: {error.msg}\n"
        f"错误附近: ...{snippet}...\n"
        f"请确保: (1) 所有键和字符串值使用双引号 (2) 对象和数组末尾没有多余逗号 "
        f"(3) 所有花括号和方括号正确闭合"
    )


def _build_pydantic_fix_hint(error: PydanticValidationError) -> str:
    """构建 Pydantic 校验错误的修复提示。"""
    lines = ["请修正以下字段:"]
    for e in error.errors()[:5]:  # 最多显示 5 个错误
        loc = " → ".join(str(x) for x in e["loc"])
        lines.append(f"  - {loc}: {e['msg']}")
    if error.error_count() > 5:
        lines.append(f"  ... 以及其他 {error.error_count() - 5} 个错误")
    return "\n".join(lines)


# =============================================================================
# 校验 + 重试编排
# =============================================================================


async def validate_with_retry(
    invoke_fn,        # async callable: (fix_hint: str) -> str
    target_model: type[T],
    *,
    max_retries: int = 3,
    backoff_base: float = 2.0,
) -> T:
    """
    带重试的结构化输出校验。

    流程:
      1. 调用 invoke_fn() 获取原始输出
      2. validate_against_model() 校验
      3. 失败 → 将 fix_hint 传给 invoke_fn(fix_hint) 重试
      4. 重试耗尽 → 抛出 ValidationError

    Args:
        invoke_fn: 异步函数，接受可选的 fix_hint 字符串，返回 LLM 原始输出
        target_model: 目标 Pydantic 模型
        max_retries: 最大重试次数（默认 3）
        backoff_base: 指数退避基数（秒）

    Returns:
        校验通过的 Pydantic 模型实例

    Raises:
        ValidationError: 所有重试耗尽的最后一次错误
    """
    last_error: ValidationError | None = None
    fix_hint: str = ""

    for attempt in range(max_retries):
        # 指数退避
        if attempt > 0:
            wait = backoff_base ** (attempt - 1)
            time.sleep(wait)

        # 调用 LLM（首次不带修复提示，后续带）
        if attempt == 0:
            raw = await invoke_fn(None)
        else:
            raw = await invoke_fn(fix_hint)

        try:
            return validate_against_model(raw, target_model)
        except ValidationError as e:
            last_error = e
            fix_hint = e.fix_hint

    raise ValidationError(
        f"{max_retries} 次重试后校验仍然失败: {last_error}",
        last_error.fix_hint if last_error else "",
    )
