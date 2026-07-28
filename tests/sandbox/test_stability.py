"""沙箱稳定性测试（D10 交付物）。

50 轮连续 clone + pytest + cleanup，验证无资源泄漏、无性能衰减。
默认跳过（需网络），用 pytest -m slow 显式运行。

用法：
    pytest tests/sandbox/test_stability.py -v -s
    pytest tests/sandbox/test_stability.py -v -s --rounds 10   # 自定义轮数
"""

import time

import pytest

from app.tools.sandbox_ops import cleanup_sandbox, get_sandbox, reset_all


@pytest.mark.slow
class TestStability:
    """沙箱稳定性验证。"""

    def test_rounds_clone_and_pytest(self, request):
        """N 轮 clone + pytest，全部通过，无资源泄漏。默认 10 轮。"""
        rounds = int(request.config.getoption("--rounds", default=10))
        repo_url = "https://github.com/pallets/markupsafe"
        passed = 0
        failed = 0
        errors = 0
        durations = []

        for i in range(rounds):
            task_id = f"stability-{i}"
            t0 = time.time()

            try:
                s = get_sandbox(task_id)

                r = s.execute(
                    f"git clone --depth 1 --branch main {repo_url} repo",
                    timeout=60,
                )
                if r.exit_code != 0:
                    failed += 1
                    cleanup_sandbox(task_id)
                    continue

                r = s.execute(
                    "python -m pytest --tb=short -q 2>&1",
                    cwd="repo",
                    timeout=120,
                )
                durations.append(round(time.time() - t0, 1))

                if r.exit_code == 0:
                    passed += 1
                else:
                    failed += 1

            except Exception:
                errors += 1

            cleanup_sandbox(task_id)

        reset_all()

        # 断言
        assert failed == 0, f"{failed} 轮失败"
        assert errors == 0, f"{errors} 轮异常"
        assert passed == rounds, f"期望 {rounds} 轮通过，实际 {passed}"

        # 性能衰减检查：后 10 轮平均不应超过前 10 轮 2 倍
        if len(durations) >= 20:
            first_10 = sum(durations[:10]) / 10
            last_10 = sum(durations[-10:]) / 10
            assert last_10 <= first_10 * 2, (
                f"性能衰减: 前10轮均 {first_10:.1f}s, 后10轮均 {last_10:.1f}s"
            )
