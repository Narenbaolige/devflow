"""
Reducer 函数单元测试。

contracts/state.py 中的 reducer_append 和 reducer_merge_by_file
是 LangGraph state 合并的核心逻辑，任何 bug 会影响 events、
errors、patches 等关键字段的正确性。
"""

import pytest
from contracts.state import reducer_append, reducer_merge_by_file


class TestReducerAppend:
    """reducer_append: (existing or []) + (new or [])"""

    def test_both_none_returns_empty(self):
        assert reducer_append(None, None) == []

    def test_existing_none_new_has_items(self):
        assert reducer_append(None, [{"a": 1}]) == [{"a": 1}]

    def test_existing_has_items_new_none(self):
        assert reducer_append([{"a": 1}], None) == [{"a": 1}]

    def test_append_to_existing(self):
        result = reducer_append([{"a": 1}], [{"b": 2}])
        assert result == [{"a": 1}, {"b": 2}]

    def test_append_empty_new(self):
        assert reducer_append([{"a": 1}], []) == [{"a": 1}]

    def test_append_multiple_items(self):
        result = reducer_append([1, 2], [3, 4, 5])
        assert result == [1, 2, 3, 4, 5]

    def test_append_preserves_duplicates(self):
        """reducer_append 不去重，同值元素可重复出现。"""
        result = reducer_append([{"a": 1}], [{"a": 1}])
        assert result == [{"a": 1}, {"a": 1}]


class TestReducerMergeByFile:
    """reducer_merge_by_file: 按 file_path 去重合并，同文件新覆盖旧。"""

    def test_both_none_returns_empty(self):
        assert reducer_merge_by_file(None, None) == []

    def test_existing_none_new_has_items(self):
        new = [{"file_path": "a.py", "diff": "..."}]
        assert reducer_merge_by_file(None, new) == new

    def test_existing_has_items_new_none(self):
        existing = [{"file_path": "a.py", "diff": "..."}]
        assert reducer_merge_by_file(existing, None) == existing

    def test_new_file_appended(self):
        existing = [{"file_path": "a.py", "diff": "diff-a"}]
        new = [{"file_path": "b.py", "diff": "diff-b"}]
        result = reducer_merge_by_file(existing, new)
        assert len(result) == 2
        file_paths = {p["file_path"] for p in result}
        assert file_paths == {"a.py", "b.py"}

    def test_same_file_overwritten(self):
        """同一 file_path 的 patch 以新值覆盖旧值。"""
        existing = [{"file_path": "a.py", "diff": "old-diff", "change_description": "old"}]
        new = [{"file_path": "a.py", "diff": "new-diff", "change_description": "new"}]
        result = reducer_merge_by_file(existing, new)
        assert len(result) == 1
        assert result[0]["diff"] == "new-diff"
        assert result[0]["change_description"] == "new"

    def test_mixed_merge(self):
        """部分文件被覆盖，部分新增。"""
        existing = [
            {"file_path": "a.py", "diff": "old-a"},
            {"file_path": "b.py", "diff": "old-b"},
        ]
        new = [
            {"file_path": "a.py", "diff": "new-a"},      # 覆盖
            {"file_path": "c.py", "diff": "new-c"},      # 新增
        ]
        result = reducer_merge_by_file(existing, new)
        assert len(result) == 3
        file_map = {p["file_path"]: p["diff"] for p in result}
        assert file_map == {"a.py": "new-a", "b.py": "old-b", "c.py": "new-c"}

    def test_empty_existing_list(self):
        new = [{"file_path": "a.py", "diff": "..."}]
        assert reducer_merge_by_file([], new) == new

    def test_empty_new_list(self):
        existing = [{"file_path": "a.py", "diff": "..."}]
        assert reducer_merge_by_file(existing, []) == existing

    def test_missing_file_path_defaults_to_empty_string(self):
        """缺少 file_path 的 dict 会被归到 '' 键，后出现的覆盖先出现的。"""
        existing = [{"diff": "old", "other": "keep"}]
        new = [{"diff": "new"}]
        result = reducer_merge_by_file(existing, new)
        assert len(result) == 1
        assert result[0]["diff"] == "new"
        # file_path 本身不在原始 dict 中，不会被添加
        assert "file_path" not in result[0]

    def test_multiple_missing_file_path_last_wins(self):
        """多个缺 file_path 的元素，最后一个覆盖前面所有。"""
        items = [
            {"diff": "first"},
            {"diff": "second"},
            {"diff": "third"},
        ]
        result = reducer_merge_by_file([], items)
        assert len(result) == 1
        assert result[0]["diff"] == "third"

    def test_original_existing_not_mutated(self):
        """reducer 不应修改传入的 existing 列表。"""
        existing = [{"file_path": "a.py", "diff": "old"}]
        existing_copy = [dict(existing[0])]
        new = [{"file_path": "b.py", "diff": "new"}]
        reducer_merge_by_file(existing, new)
        assert existing == existing_copy
