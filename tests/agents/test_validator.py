"""
结构化输出校验器测试。

覆盖 extract_json / validate_against_model / ValidationError。
"""

import pytest
from pydantic import BaseModel, Field

from app.agents.validator import (
    ValidationError,
    extract_json,
    validate_against_model,
)

# =============================================================================
# 测试用的 Pydantic 模型
# =============================================================================

class SimpleModel(BaseModel):
    name: str
    value: int


class NestedModel(BaseModel):
    summary: str
    items: list[SimpleModel] = Field(default_factory=list)
    count: int = Field(ge=0)


# =============================================================================
# extract_json
# =============================================================================

class TestExtractJson:
    def test_direct_json(self):
        result = extract_json('{"name": "test", "value": 42}')
        assert result == '{"name": "test", "value": 42}'

    def test_json_with_markdown_fence(self):
        result = extract_json('```json\n{"name": "test", "value": 42}\n```')
        assert result == '{"name": "test", "value": 42}'

    def test_json_with_fence_no_lang(self):
        result = extract_json('```\n{"name": "test", "value": 42}\n```')
        assert result == '{"name": "test", "value": 42}'

    def test_json_with_prefix_text(self):
        result = extract_json('Here is the output:\n\n{"name": "test", "value": 42}\n\nDone.')
        assert result == '{"name": "test", "value": 42}'

    def test_nested_json(self):
        text = '{"summary": "ok", "items": [{"name": "a", "value": 1}], "count": 1}'
        result = extract_json(text)
        assert '"summary"' in result
        assert '"items"' in result

    def test_empty_input(self):
        with pytest.raises(ValidationError, match="为空"):
            extract_json("")

    def test_no_json(self):
        with pytest.raises(ValidationError, match="无法"):
            extract_json("This is just plain text, no JSON here.")

    def test_whitespace_only(self):
        with pytest.raises(ValidationError, match="为空"):
            extract_json("   \n\t  ")


# =============================================================================
# validate_against_model
# =============================================================================

class TestValidateAgainstModel:
    def test_valid_simple(self):
        model = validate_against_model('{"name": "hello", "value": 10}', SimpleModel)
        assert model.name == "hello"
        assert model.value == 10

    def test_valid_with_markdown_fence(self):
        model = validate_against_model(
            '```json\n{"name": "hello", "value": 10}\n```',
            SimpleModel,
        )
        assert model.name == "hello"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError, match="Pydantic 校验失败"):
            validate_against_model('{"name": "hello"}', SimpleModel)

    def test_invalid_type(self):
        with pytest.raises(ValidationError, match="Pydantic 校验失败"):
            validate_against_model('{"name": "hello", "value": "not_a_number"}', SimpleModel)

    def test_malformed_json(self):
        with pytest.raises(ValidationError, match="JSON 解析失败"):
            validate_against_model('{"name": "hello", value: 10}', SimpleModel)

    def test_trailing_comma_repaired(self):
        """尾部多余逗号应被自动修复"""
        model = validate_against_model('{"name": "hello", "value": 10,}', SimpleModel)
        assert model.name == "hello"
        assert model.value == 10

    def test_nested_model(self):
        json_str = (
            '{"summary": "ok", "items": ['
            '{"name": "a", "value": 1},'
            '{"name": "b", "value": 2}'
            '], "count": 2}'
        )
        model = validate_against_model(json_str, NestedModel)
        assert model.summary == "ok"
        assert len(model.items) == 2
        assert model.items[0].name == "a"
        assert model.count == 2

    def test_count_negative(self):
        with pytest.raises(ValidationError, match="Pydantic 校验失败"):
            validate_against_model(
                '{"summary": "ok", "items": [], "count": -1}',
                NestedModel,
            )

    def test_empty_json_object(self):
        with pytest.raises(ValidationError):
            validate_against_model("{}", SimpleModel)


# =============================================================================
# ValidationError
# =============================================================================

class TestValidationError:
    def test_with_fix_hint(self):
        err = ValidationError("bad", "try this instead")
        assert str(err) == "bad"
        assert err.fix_hint == "try this instead"

    def test_without_fix_hint(self):
        err = ValidationError("bad")
        assert err.fix_hint == "bad"
