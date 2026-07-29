r"""
一键生成/扩展 devflow-test-repo，覆盖 5 类别评测任务所需的所有 bug 模块。

用法: python eval/setup_test_repo.py [--repo D:/Dev/devflow-test-repo]
"""

import argparse
import subprocess
from pathlib import Path

MODULES = {
    # ── math_utils: simple_fix (task-001 参数校验, task-011 docstring) ──
    "math_utils.py": '''\
"""Simple math utilities for DevFlow testing."""


def factorial(n):
    """Calculate factorial of n. Currently missing input validation."""
    if n == 0:
        return 1
    return n * factorial(n - 1)


def fibonacci(n):
    """Return the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


def divide(a, b):
    """Divide a by b. Currently does NOT handle division by zero."""
    return a / b
''',

    "test_math_utils.py": '''\
import pytest
from math_utils import factorial, fibonacci, divide


class TestFactorial:
    def test_factorial_zero(self):
        assert factorial(0) == 1

    def test_factorial_one(self):
        assert factorial(1) == 1

    def test_factorial_five(self):
        assert factorial(5) == 120

    def test_factorial_negative_should_raise(self):
        with pytest.raises(ValueError):
            factorial(-1)

    def test_factorial_non_integer_should_raise(self):
        with pytest.raises(TypeError):
            factorial(3.5)


class TestFibonacci:
    def test_fib_zero(self):
        assert fibonacci(0) == 0

    def test_fib_one(self):
        assert fibonacci(1) == 1

    def test_fib_ten(self):
        assert fibonacci(10) == 55

    def test_fib_negative(self):
        assert fibonacci(-5) == 0


class TestDivide:
    def test_divide_normal(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero_should_return_none(self):
        result = divide(10, 0)
        assert result is None, f"Expected None, got {result}"
''',

    # ── calculator: feature (task-008 power方法) ──
    "calculator.py": '''\
"""Simple calculator for DevFlow testing."""


class Calculator:
    """A simple calculator. Missing power method."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            return None
        return a / b
''',

    "test_calculator.py": '''\
import pytest
from calculator import Calculator


@pytest.fixture
def calc():
    return Calculator()


class TestCalculator:
    def test_add(self, calc):
        assert calc.add(2, 3) == 5

    def test_subtract(self, calc):
        assert calc.subtract(5, 3) == 2

    def test_multiply(self, calc):
        assert calc.multiply(2, 3) == 6

    def test_divide(self, calc):
        assert calc.divide(10, 2) == 5.0

    def test_divide_by_zero(self, calc):
        assert calc.divide(10, 0) is None

    def test_power(self, calc):
        assert calc.power(2, 3) == 8

    def test_power_zero(self, calc):
        assert calc.power(2, 0) == 1

    def test_power_negative(self, calc):
        assert calc.power(2, -1) == 0.5
''',

    # ── item_processor: edge_case (task-021 空列表) ──
    "item_processor.py": '''\
"""Item processor for DevFlow testing."""


def process_items(items):
    """Process a list of items. Bug: fails on empty list."""
    first = items[0]
    result = []
    for item in items:
        result.append(item * 2)
    return result


def get_first(items):
    """Get first item or None."""
    if not items:
        return None
    return items[0]
''',

    "test_item_processor.py": '''\
import pytest
from item_processor import process_items, get_first


class TestProcessItems:
    def test_normal_list(self):
        assert process_items([1, 2, 3]) == [2, 4, 6]

    def test_empty_list(self):
        assert process_items([]) == []

    def test_single_item(self):
        assert process_items([5]) == [10]


class TestGetFirst:
    def test_normal(self):
        assert get_first([1, 2, 3]) == 1

    def test_empty(self):
        assert get_first([]) is None
''',

    # ── search: bug_fix (task-014 binary_search off-by-one) ──
    "search.py": '''\
"""Search utilities for DevFlow testing."""


def binary_search(arr, target):
    """Binary search. Bug: off-by-one when target is the last element."""
    left, right = 0, len(arr) - 1
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def linear_search(arr, target):
    """Linear search."""
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1
''',

    "test_search.py": '''\
import pytest
from search import binary_search, linear_search


class TestBinarySearch:
    def test_find_first(self):
        assert binary_search([1, 2, 3, 4, 5], 1) == 0

    def test_find_last(self):
        assert binary_search([1, 2, 3, 4, 5], 5) == 4

    def test_find_middle(self):
        assert binary_search([1, 2, 3, 4, 5], 3) == 2

    def test_not_found(self):
        assert binary_search([1, 2, 3, 4, 5], 99) == -1

    def test_empty(self):
        assert binary_search([], 1) == -1

    def test_single_element(self):
        assert binary_search([42], 42) == 0


class TestLinearSearch:
    def test_find(self):
        assert linear_search([1, 2, 3], 2) == 1

    def test_not_found(self):
        assert linear_search([1, 2, 3], 99) == -1
''',

    # ── config_loader: bug_fix (task-005 文件不存在时抛异常) ──
    "config_loader.py": '''\
"""Configuration loader for DevFlow testing."""

import json
from pathlib import Path


def parse_config(filepath):
    """Parse a JSON config file. Bug: raises FileNotFoundError instead of returning {}."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(filepath, defaults=None):
    """Load config with defaults."""
    cfg = defaults or {}
    if Path(filepath).exists():
        cfg.update(parse_config(filepath))
    return cfg
''',

    "test_config_loader.py": '''\
import json
import pytest
import tempfile
from pathlib import Path
from config_loader import parse_config, load_config


class TestParseConfig:
    def test_valid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            path = f.name
        try:
            assert parse_config(path) == {"key": "value"}
        finally:
            Path(path).unlink()

    def test_nonexistent_file(self):
        result = parse_config("nonexistent_file_12345.json")
        assert result == {}


class TestLoadConfig:
    def test_with_defaults(self):
        result = load_config("nonexistent.json", {"a": 1})
        assert result == {"a": 1}
''',

    # ── user_service + validators: refactor (task-006 提取校验函数) ──
    "validators.py": '''\
"""Validators module. Currently empty — validation logic is duplicated in user_service."""

# TODO: validate_user_data function should be extracted here from user_service.py
''',

    "user_service.py": '''\
"""User service for DevFlow testing. Has duplicated validation logic."""


class UserService:
    def __init__(self):
        self.users = {}

    def create(self, username, email, age):
        # Duplicated validation (also in update)
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not email or "@" not in email:
            raise ValueError("Invalid email")
        if age is not None and age < 0:
            raise ValueError("Age cannot be negative")
        self.users[username] = {"email": email, "age": age}
        return self.users[username]

    def update(self, username, email=None, age=None):
        if username not in self.users:
            raise KeyError(f"User {username} not found")
        # Duplicated validation (same as create)
        if email is not None:
            if "@" not in email:
                raise ValueError("Invalid email")
            self.users[username]["email"] = email
        if age is not None:
            if age < 0:
                raise ValueError("Age cannot be negative")
            self.users[username]["age"] = age
        return self.users[username]
''',

    "test_user_service.py": '''\
import pytest
from user_service import UserService


@pytest.fixture
def svc():
    return UserService()


class TestUserService:
    def test_create_valid(self, svc):
        u = svc.create("alice", "alice@example.com", 25)
        assert u["email"] == "alice@example.com"

    def test_create_short_username(self, svc):
        with pytest.raises(ValueError):
            svc.create("ab", "a@b.com", 25)

    def test_create_invalid_email(self, svc):
        with pytest.raises(ValueError):
            svc.create("alice", "no-at-sign", 25)

    def test_create_negative_age(self, svc):
        with pytest.raises(ValueError):
            svc.create("alice", "a@b.com", -5)

    def test_update_email(self, svc):
        svc.create("alice", "alice@example.com", 25)
        svc.update("alice", email="bob@example.com")
        assert svc.users["alice"]["email"] == "bob@example.com"

    def test_update_nonexistent(self, svc):
        with pytest.raises(KeyError):
            svc.update("nobody", email="x@y.com")
''',

    # ── file_handler: edge_case (task-022 Unicode文件名) ──
    "file_handler.py": '''\
"""File handler for DevFlow testing."""


def read_file(filepath):
    """Read a file and return its content. Bug: might fail with Unicode paths."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath, content):
    """Write content to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def process_file(filepath):
    """Read, uppercase, and return."""
    content = read_file(filepath)
    return content.upper()
''',

    "test_file_handler.py": '''\
import os
import pytest
import tempfile
from pathlib import Path
from file_handler import read_file, write_file, process_file


class TestFileHandler:
    def test_read_write_roundtrip(self):
        path = Path(tempfile.gettempdir()) / "test_devflow_normal.txt"
        try:
            write_file(str(path), "hello world")
            assert read_file(str(path)) == "hello world"
        finally:
            path.unlink(missing_ok=True)

    def test_unicode_filename(self):
        name = "test_chinese_filename.txt"
        path = Path(tempfile.gettempdir()) / name
        try:
            write_file(str(path), "unicode test")
            assert read_file(str(path)) == "unicode test"
        finally:
            path.unlink(missing_ok=True)

    def test_empty_file(self):
        path = Path(tempfile.gettempdir()) / "test_empty.txt"
        try:
            write_file(str(path), "")
            assert read_file(str(path)) == ""
        finally:
            path.unlink(missing_ok=True)

    def test_process_file(self):
        path = Path(tempfile.gettempdir()) / "test_process.txt"
        try:
            write_file(str(path), "hello")
            assert process_file(str(path)) == "HELLO"
        finally:
            path.unlink(missing_ok=True)
''',

    # ── test_user: simple_fix (task-002 修复 import 路径) ──
    "test_user.py": '''\
"""Test for User model. Task-002: fix the import path below."""
from models import User  # Bug: should be from app.models import User


def test_user_creation():
    user = User("alice", "alice@example.com")
    assert user.name == "alice"
    assert user.email == "alice@example.com"


def test_user_str():
    user = User("bob", "bob@example.com")
    assert str(user) == "User(bob)"
''',

    "models.py": '''\
"""User model — simple dataclass for task-002."""


class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"User({self.name})"
''',

    # ── utils: simple_fix (task-012 修复 typo) ──
    "utils.py": '''\
"""Utility functions for DevFlow testing."""


def calculate_values(a: int, b: int) -> dict:
    """Return calculated values. Contains an intentional typo."""
    return {
        "sum": a + b,
        "product": a * b,
        "calulated_value": a * b * 2,  # Bug: typo, should be 'calculated_value'
    }


def format_result(data: dict) -> str:
    """Format a result dictionary as a string."""
    return ", ".join(f"{k}={v}" for k, v in data.items())
''',

    "test_utils.py": '''\
"""Tests for utils.py — task-012."""
from utils import calculate_values, format_result


class TestCalculateValues:
    def test_returns_sum_and_product(self):
        r = calculate_values(3, 4)
        assert r["sum"] == 7
        assert r["product"] == 12

    def test_has_correct_key_name(self):
        r = calculate_values(2, 5)
        # Should be 'calculated_value', not 'calulated_value'
        assert "calculated_value" in r
        assert r["calculated_value"] == 20


class TestFormatResult:
    def test_format(self):
        assert format_result({"a": 1, "b": 2}) == "a=1, b=2"
''',

    # ── constants + routes: refactor (task-016 提取硬编码字符串) ──
    "constants.py": '''\
"""Application constants."""

# All hardcoded values should be defined here
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
API_VERSION = "v1"
''',

    "routes.py": '''\
"""Routes module — task-016: extract hardcoded strings to constants.py."""

from constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, API_VERSION


def build_pagination_url(base: str, page: int, size: int = DEFAULT_PAGE_SIZE) -> str:
    """Build a paginated API URL."""
    size = min(size, MAX_PAGE_SIZE)
    return f"/api/{API_VERSION}/{base}?page={page}&size={size}"
''',

    "test_routes.py": '''\
"""Tests for routes.py — task-016."""
from routes import build_pagination_url


class TestBuildPaginationURL:
    def test_default_page_size(self):
        url = build_pagination_url("users", 1)
        assert "size=20" in url
        assert "/api/v1/users" in url

    def test_caps_at_max(self):
        url = build_pagination_url("items", 1, size=500)
        assert "size=100" in url

    def test_custom_valid_size(self):
        url = build_pagination_url("posts", 2, size=50)
        assert "page=2" in url
        assert "size=50" in url
''',

    # ── data_pipeline: refactor (task-018 拆分 run() 方法) ──
    "data_pipeline.py": '''\
"""Data pipeline for DevFlow testing. Task-018: refactor the run() method."""


class DataPipeline:
    def __init__(self, source: list):
        self.source = source
        self.extracted: list = []
        self.transformed: list = []
        self.loaded: list = []

    def extract(self):
        """Extract data from source."""
        self.extracted = [x for x in self.source if x is not None]

    def transform(self):
        """Transform extracted data."""
        self.transformed = [x * 2 for x in self.extracted]

    def load(self):
        """Load transformed data."""
        self.loaded = list(self.transformed)

    def run(self):
        """Run the full pipeline — too many responsibilities in one method."""
        # Extract
        self.extracted = [x for x in self.source if x is not None]
        # Transform
        self.transformed = [x * 2 for x in self.extracted]
        # Load
        self.loaded = list(self.transformed)
        # Log
        print(f"Pipeline complete: {len(self.loaded)} items loaded")
        return self.loaded
''',

    "test_data_pipeline.py": '''\
"""Tests for data_pipeline.py — task-018."""
from data_pipeline import DataPipeline


class TestDataPipeline:
    def test_extract_filters_none(self):
        p = DataPipeline([1, None, 2, None, 3])
        p.extract()
        assert p.extracted == [1, 2, 3]

    def test_transform_doubles(self):
        p = DataPipeline([1, 2, 3])
        p.extract()
        p.transform()
        assert p.transformed == [2, 4, 6]

    def test_load_copies(self):
        p = DataPipeline([1, 2])
        p.extract()
        p.transform()
        p.load()
        assert p.loaded == [2, 4]

    def test_run_uses_individual_methods(self):
        """run() should delegate to extract/transform/load, not duplicate logic."""
        import inspect
        source = inspect.getsource(DataPipeline.run)
        # Should call self.extract/transform/load rather than inlining everything
        assert "self.extract()" in source or "self.transform()" in source
''',

}


def setup_repo(repo_path: str):
    """Generate or update the test repository with all modules."""
    repo = Path(repo_path)
    if not repo.exists():
        repo.mkdir(parents=True)

    # Init git if needed
    if not (repo / ".git").exists():
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    # Write all module files
    written = []
    for filename, content in MODULES.items():
        filepath = repo / filename
        if filepath.exists():
            print(f"  skip (exists): {filename}")
        else:
            filepath.write_text(content, encoding="utf-8")
            print(f"  created: {filename}")
            written.append(filename)

    # Write .gitignore
    gitignore = repo / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("__pycache__/\n*.py[cod]\n.pytest_cache/\n.ruff_cache/\n")
        written.append(".gitignore")

    # Git add + commit
    if written:
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add test modules: {', '.join(written[:3])}..."],
            cwd=repo, capture_output=True,
        )
        print(f"\n  committed {len(written)} files")
    else:
        print("\n  no new files to commit")

    # Show current state
    r = subprocess.run(
        ["python", "-m", "pytest", "-v", "--tb=line"],
        cwd=repo, capture_output=True, text=True,
    )
    lines = r.stdout.strip().split("\n")
    failed = sum(1 for l in lines if "FAILED" in l)
    passed = sum(1 for l in lines if "PASSED" in l)
    print(f"\n  Test summary: {passed} passed, {failed} failed (expected failures = bugs)")
    if failed > 0:
        print("  Failures (these are the bugs to fix):")
        for l in lines:
            if "FAILED" in l:
                print(f"    {l.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Setup DevFlow test repository")
    parser.add_argument("--repo", default="D:/Dev/devflow-test-repo", help="Target repo path")
    args = parser.parse_args()
    print(f"Setting up test repo: {args.repo}")
    print()
    setup_repo(args.repo)


if __name__ == "__main__":
    main()
