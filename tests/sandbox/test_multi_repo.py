"""多仓库兼容性测试。

验证沙箱对不同类型的仓库都能正常 clone + 执行基础命令。
沙箱本身语言无关（只跑 execute），本测试覆盖多种项目结构。
默认跳过（需网络），用 pytest -m slow 显式运行。
"""

import pytest

from app.tools.sandbox_ops import cleanup_sandbox, get_sandbox

# 测试仓库列表
REPOS = [
    # (名称, URL, 验证命令, 期望)
    (
        "simplejson (setup.py 项目)",
        "https://github.com/simplejson/simplejson",
        "python -c \"from importlib.metadata import version; print(version('simplejson'))\"",
        0,
    ),
    (
        "rich (pyproject.toml 项目)",
        "https://github.com/Textualize/rich",
        "python -c \"from importlib.metadata import version; print(version('rich'))\"",
        0,
    ),
    (
        "requests (大型项目)",
        "https://github.com/psf/requests",
        "python -c \"from importlib.metadata import version; print(version('requests'))\"",
        0,
    ),
    (
        "click (纯 Python 工具)",
        "https://github.com/pallets/click",
        "python -c \"from importlib.metadata import version; print(version('click'))\"",
        0,
    ),
    (
        "markdown-it-py (pyproject.toml + test/)",
        "https://github.com/executablebooks/markdown-it-py",
        "python -c \"from importlib.metadata import version; print(version('markdown-it-py'))\"",
        0,
    ),
]


@pytest.mark.slow
@pytest.mark.parametrize("name,url,verify_cmd,expected_exit", REPOS)
def test_clone_install_and_verify(name, url, verify_cmd, expected_exit):
    """对不同仓库执行 clone + install + 验证，全部通过。"""
    task_id = name.replace(" ", "-").replace("(", "").replace(")", "")

    try:
        s = get_sandbox(task_id)

        # clone — 先试 main，失败则试 master
        for branch in ("main", "master"):
            r = s.execute(
                f"git clone --depth 1 --branch {branch} {url} repo",
                timeout=60,
            )
            if r.exit_code == 0:
                break
            # 清理失败的 clone 目录
            s.execute("rm -rf repo")
        assert r.exit_code == 0, f"clone 失败 (main & master): {r.stderr[:200]}"

        # install
        r = s.execute("pip install -q -e .", cwd="repo", timeout=180)
        if r.exit_code != 0:
            check = s.execute(
                "python -c \"import os; exit(0 if os.path.exists('requirements.txt') else 1)\"",
                cwd="repo",
            )
            if check.exit_code == 0:
                s.execute("pip install -q -r requirements.txt", cwd="repo", timeout=180)

        # 验证导入
        r = s.execute(verify_cmd, cwd="repo", timeout=30)
        assert r.exit_code == expected_exit, (
            f"{name}: 验证失败 exit={r.exit_code}\n"
            f"stderr: {r.stderr[:300]}"
        )

    finally:
        cleanup_sandbox(task_id)
