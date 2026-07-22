"""
评测任务定义示例。

每条任务包含：
  - id: 唯一标识
  - category: 任务类别 (simple_fix / bug_fix / refactor / feature / security)
  - difficulty: 难度 (1-4)
  - requirement: 需求描述
  - repo_url: 目标仓库（可留空，使用默认）
  - acceptance_criteria: 验收条件列表
  - expected_files: 预期修改的文件
"""

INITIAL_TASKS = [
    {
        "id": "task-001",
        "category": "simple_fix",
        "difficulty": 1,
        "requirement": "给 factorial 函数添加参数校验：输入为负数时抛出 ValueError，输入不是整数时抛出 TypeError",
        "acceptance_criteria": [
            "factorial(-1) 抛出 ValueError",
            "factorial(3.5) 抛出 TypeError",
            "factorial(0) 返回 1",
            "factorial(5) 返回 120",
        ],
        "expected_files": ["math_utils.py"],
    },
    {
        "id": "task-002",
        "category": "simple_fix",
        "difficulty": 1,
        "requirement": "修复 test_user.py 中的 import 错误：from models import User 应改为 from app.models import User",
        "acceptance_criteria": [
            "pytest tests/test_user.py 通过",
            "所有 import 使用正确的模块路径",
        ],
        "expected_files": ["tests/test_user.py"],
    },
    {
        "id": "task-003",
        "category": "bug_fix",
        "difficulty": 2,
        "requirement": "修复 divide 函数的除零异常：当除数为 0 时应返回 None 而不是抛出 ZeroDivisionError",
        "acceptance_criteria": [
            "divide(10, 0) 返回 None",
            "divide(10, 0) 不抛出异常",
            "divide(10, 2) 返回 5.0",
        ],
        "expected_files": ["math_utils.py"],
    },
    {
        "id": "task-004",
        "category": "bug_fix",
        "difficulty": 2,
        "requirement": "修复 User 类的 email 属性 setter：设置 email 时应同时更新 _email 和 email_domain 字段",
        "acceptance_criteria": [
            "user.email = 'test@example.com' 后 user.email_domain == 'example.com'",
            "原有测试全部通过",
        ],
        "expected_files": ["models/user.py"],
    },
    {
        "id": "task-005",
        "category": "bug_fix",
        "difficulty": 2,
        "requirement": "修复 parse_config 函数在文件不存在时的行为：应返回空字典 {} 而不是抛出 FileNotFoundError",
        "acceptance_criteria": [
            "parse_config('nonexistent.yaml') 返回 {}",
            "parse_config('valid.yaml') 正常返回配置字典",
        ],
        "expected_files": ["config_loader.py"],
    },
    {
        "id": "task-006",
        "category": "refactor",
        "difficulty": 3,
        "requirement": "将 UserService 中的重复校验逻辑提取为独立的 validate_user_data 函数",
        "acceptance_criteria": [
            "validate_user_data 函数存在且可独立调用",
            "UserService.create() 和 UserService.update() 都调用 validate_user_data",
            "原有测试全部通过",
            "无重复代码（相同校验逻辑只出现一次）",
        ],
        "expected_files": ["services/user_service.py", "validators.py"],
    },
    {
        "id": "task-007",
        "category": "refactor",
        "difficulty": 3,
        "requirement": "将 Database 类的连接字符串构建逻辑从 __init__ 中提取为 build_connection_string 静态方法",
        "acceptance_criteria": [
            "build_connection_string(host, port, dbname) 返回正确的连接字符串",
            "Database.__init__ 调用 build_connection_string",
            "原有测试全部通过",
        ],
        "expected_files": ["database.py"],
    },
    {
        "id": "task-008",
        "category": "feature",
        "difficulty": 3,
        "requirement": "为 Calculator 类添加 power 方法，计算 a 的 b 次方，支持负指数",
        "acceptance_criteria": [
            "Calculator().power(2, 3) == 8",
            "Calculator().power(2, 0) == 1",
            "Calculator().power(2, -1) == 0.5",
            "添加对应的单元测试",
        ],
        "expected_files": ["calculator.py", "tests/test_calculator.py"],
    },
    {
        "id": "task-009",
        "category": "feature",
        "difficulty": 4,
        "requirement": "为所有 API 端点添加请求日志中间件：记录每个请求的方法、路径、耗时和响应状态码",
        "acceptance_criteria": [
            "所有请求都有对应日志",
            "日志格式：{timestamp} {method} {path} {status_code} {duration_ms}ms",
            "不改变原有 API 行为",
        ],
        "expected_files": ["middleware.py", "app.py"],
    },
    {
        "id": "task-010",
        "category": "security",
        "difficulty": 4,
        "requirement": "修复 search_users 函数中的 SQL 注入漏洞：将字符串拼接改为参数化查询",
        "acceptance_criteria": [
            "search_users('admin'); DROP TABLE users;--') 不执行恶意 SQL",
            "正常查询功能不受影响",
        ],
        "expected_files": ["database.py"],
    },
]
