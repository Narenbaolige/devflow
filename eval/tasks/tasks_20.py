"""
评测任务数据集（20 条）。

覆盖 5 个类别、4 个难度级别，用于消融实验：
单 Agent vs 多 Agent（4-Agent Pipeline）对比。

每条任务结构：
  - id: 唯一标识
  - category: simple_fix / bug_fix / refactor / feature / edge_case
  - difficulty: 1-4
  - requirement: 需求描述
  - acceptance_criteria: 验收条件列表
  - expected_files: 预期修改的文件
"""

EVAL_TASKS = [
    # =========================================================================
    # simple_fix (难度 1) — 5 条
    # =========================================================================
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
        "id": "task-011",
        "category": "simple_fix",
        "difficulty": 1,
        "requirement": "给 fibonacci 函数添加 docstring，包含参数说明和返回值说明",
        "acceptance_criteria": [
            "fibonacci 函数有 docstring",
            "docstring 包含 Args 和 Returns 部分",
        ],
        "expected_files": ["math_utils.py"],
    },
    {
        "id": "task-012",
        "category": "simple_fix",
        "difficulty": 1,
        "requirement": "修复 utils.py 中变量名 typo：'calulated_value' 应改为 'calculated_value'",
        "acceptance_criteria": [
            "所有引用 'calulated_value' 的地方改为 'calculated_value'",
            "测试全部通过",
        ],
        "expected_files": ["utils.py"],
    },
    {
        "id": "task-013",
        "category": "simple_fix",
        "difficulty": 1,
        "requirement": "为 calculate_total 函数的参数 price 和 quantity 添加类型注解（float 和 int）",
        "acceptance_criteria": [
            "calculate_total(price: float, quantity: int) 类型注解正确",
            "原有功能不改变",
        ],
        "expected_files": ["calculator.py"],
    },

    # =========================================================================
    # bug_fix (难度 2) — 5 条
    # =========================================================================
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
        "id": "task-014",
        "category": "bug_fix",
        "difficulty": 2,
        "requirement": "修复 binary_search 函数的 off-by-one 错误：查找数组最后一个元素时返回 -1",
        "acceptance_criteria": [
            "binary_search([1,2,3,4,5], 5) 返回 4（索引）",
            "binary_search([1,2,3,4,5], 1) 返回 0",
            "binary_search([1,2,3,4,5], 99) 返回 -1",
        ],
        "expected_files": ["search.py"],
    },
    {
        "id": "task-015",
        "category": "bug_fix",
        "difficulty": 2,
        "requirement": "修复 read_json 函数在 JSON 文件为空时的行为：应返回 None 而不是抛出 JSONDecodeError",
        "acceptance_criteria": [
            "read_json('empty.json') 返回 None",
            "read_json('valid.json') 正常返回解析结果",
        ],
        "expected_files": ["file_utils.py"],
    },

    # =========================================================================
    # refactor (难度 3) — 5 条
    # =========================================================================
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
        "id": "task-016",
        "category": "refactor",
        "difficulty": 3,
        "requirement": "将 API 路由中所有硬编码的字符串常量（如错误消息、默认值）提取到 constants.py",
        "acceptance_criteria": [
            "constants.py 包含所有提取的常量",
            "原有 API 行为不变",
            "常量使用有意义的命名",
        ],
        "expected_files": ["constants.py", "routes.py"],
    },
    {
        "id": "task-017",
        "category": "refactor",
        "difficulty": 3,
        "requirement": "简化 process_order 函数中的多层嵌套 if-else：用 early return 模式改写",
        "acceptance_criteria": [
            "函数逻辑不变",
            "嵌套层级从 ≥3 降低到 ≤1",
            "原有测试全部通过",
        ],
        "expected_files": ["order_service.py"],
    },
    {
        "id": "task-018",
        "category": "refactor",
        "difficulty": 3,
        "requirement": "将 data_pipeline.py 中 200 行的 run() 方法拆分：extract → transform → load 三个独立方法",
        "acceptance_criteria": [
            "run() 方法调用 extract()、transform()、load()",
            "每个方法不超过 80 行",
            "原有测试全部通过",
        ],
        "expected_files": ["data_pipeline.py"],
    },

    # =========================================================================
    # feature (难度 3-4) — 3 条
    # =========================================================================
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
        "id": "task-019",
        "category": "feature",
        "difficulty": 4,
        "requirement": "为 get_data 函数添加重试机制：网络请求失败时自动重试，最多 3 次，指数退避（1s, 2s, 4s）",
        "acceptance_criteria": [
            "临时网络故障时自动重试并最终成功",
            "重试 3 次后仍失败则抛出最后一次异常",
            "每次重试间隔指数增长",
        ],
        "expected_files": ["network.py"],
    },
    {
        "id": "task-020",
        "category": "feature",
        "difficulty": 4,
        "requirement": "为所有数据库操作函数添加 @cache_result 装饰器：相同参数 60 秒内直接返回缓存结果",
        "acceptance_criteria": [
            "连续两次相同参数的查询，第二次命中缓存（不产生新 SQL 日志）",
            "60 秒后缓存过期，重新查询",
            "不同参数各自独立缓存",
        ],
        "expected_files": ["db.py", "cache.py"],
    },

    # =========================================================================
    # edge_case (难度 2-3) — 2 条
    # =========================================================================
    {
        "id": "task-021",
        "category": "edge_case",
        "difficulty": 2,
        "requirement": "修复 process_items 函数：传入空列表时应返回 [] 而不是抛出 IndexError",
        "acceptance_criteria": [
            "process_items([]) 返回 []",
            "process_items([1, 2, 3]) 正常处理",
        ],
        "expected_files": ["item_processor.py"],
    },
    {
        "id": "task-022",
        "category": "edge_case",
        "difficulty": 3,
        "requirement": "修复 file_handler.py 中文件路径处理：支持包含 Unicode 字符（中文、emoji）的文件名",
        "acceptance_criteria": [
            "read_file('测试文件.txt') 正常读取",
            "read_file('report_📊.csv') 正常读取",
            "文件读写往返不丢失内容",
        ],
        "expected_files": ["file_handler.py"],
    },
]


# =============================================================================
# 兼容旧版引入
# =============================================================================

# 保留 INITIAL_TASKS 别名，兼容旧引用
INITIAL_TASKS = EVAL_TASKS[:10]
