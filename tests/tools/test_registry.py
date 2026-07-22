"""工具注册表测试。"""

from app.tools.registry import TOOL_REGISTRY, ToolPermission, get_tools_for_agent


class TestToolRegistry:
    """工具注册表验证。"""

    def test_all_tools_registered(self):
        """所有核心工具应在注册表中。"""
        expected = {
            "read_file", "list_dir", "glob",
            "grep",
            "write_file", "edit_file",
            "execute_test", "execute_command",
        }
        actual = set(TOOL_REGISTRY.keys())
        assert expected == actual, f"缺少: {expected - actual}, 多余: {actual - expected}"

    def test_get_tools_for_developer(self):
        """Developer Agent 应有最多的工具。"""
        tools = get_tools_for_agent("developer")
        tool_names = {t.name for t in tools}
        assert "write_file" in tool_names
        assert "execute_test" in tool_names
        assert len(tools) >= 6

    def test_get_tools_for_requirement(self):
        """Requirement Agent 应只有只读工具。"""
        tools = get_tools_for_agent("requirement")
        for tool in tools:
            assert tool.permission == ToolPermission.READ_ONLY

    def test_readonly_tools_not_writable(self):
        """只读工具不应有写权限。"""
        for name, tool in TOOL_REGISTRY.items():
            if tool.permission == ToolPermission.READ_ONLY:
                assert name not in ("write_file", "edit_file")
