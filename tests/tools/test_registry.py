"""工具注册表测试。"""

import pytest

from app.tools.registry import TOOL_REGISTRY, ToolDefinition, ToolPermission, get_tools_for_agent

VALID_AGENTS = {"requirement", "planner", "developer", "reviewer", "security"}


class TestToolRegistry:
    """工具注册表验证。"""

    def test_all_tools_registered(self):
        """所有核心工具应在注册表中。"""
        expected = {
            "read_file", "list_dir", "glob",
            "grep",
            "write_file", "edit_file",
            "sandbox_execute", "execute_test", "execute_command",
        }
        actual = set(TOOL_REGISTRY.keys())
        assert expected == actual, f"缺少: {expected - actual}, 多余: {actual - expected}"

    def test_get_tools_for_developer(self):
        """Developer Agent 应有最多的工具。"""
        tools = get_tools_for_agent("developer")
        tool_names = {t.name for t in tools}
        assert "write_file" in tool_names
        assert "sandbox_execute" in tool_names
        assert len(tools) >= 6

    def test_get_tools_for_requirement(self):
        """Requirement Agent 应只有只读工具。"""
        tools = get_tools_for_agent("requirement")
        assert len(tools) > 0
        for tool in tools:
            assert tool.permission == ToolPermission.READ_ONLY

    def test_readonly_tools_not_writable(self):
        """只读工具不应有写权限。"""
        for name, tool in TOOL_REGISTRY.items():
            if tool.permission == ToolPermission.READ_ONLY:
                assert name not in ("write_file", "edit_file")

    # ── P11 追加 ──

    @pytest.mark.parametrize("tool_name", list(TOOL_REGISTRY.keys()))
    def test_every_tool_has_required_fields(self, tool_name):
        """每个注册工具必须具备 name、description、permission 字段。"""
        tool = TOOL_REGISTRY[tool_name]
        assert isinstance(tool, ToolDefinition)
        assert tool.name == tool_name
        assert len(tool.description) > 10, (
            f"'{tool_name}' 的 description 过短（{len(tool.description)} 字符）"
        )
        assert tool.permission in ToolPermission

    @pytest.mark.parametrize("tool_name", list(TOOL_REGISTRY.keys()))
    def test_every_tool_allowed_agents_are_valid(self, tool_name):
        """每个工具的 allowed_agents 必须引用已知 Agent 名称。"""
        tool = TOOL_REGISTRY[tool_name]
        for agent in tool.allowed_agents:
            assert agent in VALID_AGENTS, (
                f"'{tool_name}' 引用了未知 Agent: '{agent}'"
            )

    def test_deprecated_tools_are_marked(self):
        """已废弃工具应在 description 中标明 [已废弃]。"""
        deprecated = ["execute_test", "execute_command"]
        for name in deprecated:
            assert name in TOOL_REGISTRY
            assert "[已废弃]" in TOOL_REGISTRY[name].description, (
                f"'{name}' 未标记为已废弃"
            )

    def test_sandbox_execute_has_correct_permission(self):
        """sandbox_execute 应具有 EXECUTE_SANDBOX 权限且仅限 developer。"""
        tool = TOOL_REGISTRY["sandbox_execute"]
        assert tool.permission == ToolPermission.EXECUTE_SANDBOX
        assert tool.allowed_agents == ["developer"]

    def test_get_tools_for_invalid_agent_returns_empty(self):
        """不存在的 Agent 名称应返回空列表。"""
        tools = get_tools_for_agent("nonexistent_agent")
        assert tools == []

    def test_get_tools_for_planner(self):
        """Planner Agent 应有只读工具 + grep。"""
        tools = get_tools_for_agent("planner")
        tool_names = {t.name for t in tools}
        assert "read_file" in tool_names
        assert "grep" in tool_names
        assert "write_file" not in tool_names
