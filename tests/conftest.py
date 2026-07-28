"""pytest 全局配置。"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_addoption(parser):
    parser.addoption(
        "--rounds",
        type=int,
        default=10,
        help="稳定性测试轮数（默认 10）",
    )
