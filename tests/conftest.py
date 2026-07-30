"""pytest 全局配置。"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试环境默认启用 Mock 模式，避免依赖外部 LLM
os.environ.setdefault("DEVFLOW_USE_MOCK", "true")
os.environ.setdefault("DEVFLOW_USE_SANDBOX", "true")
# Tests expect tool calling to be available
os.environ["DEVFLOW_ENABLE_TOOLS"] = "true"


def pytest_addoption(parser):
    parser.addoption(
        "--rounds",
        type=int,
        default=10,
        help="稳定性测试轮数（默认 10）",
    )
