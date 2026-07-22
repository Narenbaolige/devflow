"""
沙箱管理器。

管理 Docker 容器的生命周期：创建、执行、清理。
"""

import time
import uuid
from datetime import datetime

import docker
from docker.errors import DockerException

from app.config import settings
from contracts.sandbox_result import SandboxResult, TestFailure, TestSummary


class SandboxManager:
    """
    Docker 沙箱管理器。

    职责：
      - 创建隔离的 Docker 容器
      - clone 代码仓库
      - 应用代码 Patch
      - 运行 pytest
      - 返回结构化 SandboxResult
      - 强制清理超时/异常的容器

    Day 1-2: 基础原型（创建容器 + 执行简单命令）
    Day 3: 完整流水线（clone → patch → install → test）
    Day 6+: 安全加固（资源限制、清理机制、白名单）
    """

    def __init__(self):
        self._client: docker.DockerClient | None = None
        self._active_containers: dict[str, str] = {}  # execution_id → container_id

    @property
    def client(self) -> docker.DockerClient:
        """懒加载 Docker 客户端。"""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise RuntimeError(
                    f"无法连接 Docker 守护进程。请确认 Docker 正在运行。\n原始错误: {e}"
                )
        return self._client

    # ------------------------------------------------------------------
    # 容器管理
    # ------------------------------------------------------------------

    def _create_container(self, execution_id: str) -> str:
        """
        创建隔离容器。

        Day 1 安全基线：
          - 网络完全隔离 (network_mode='none')
          - 只读根文件系统 (read_only=True)，/workspace 为 tmpfs
          - CPU 限制 1 核
          - 内存限制 512MB
        """
        container = self.client.containers.run(
            image=settings.DOCKER_IMAGE,
            command="tail -f /dev/null",  # 保持容器运行
            detach=True,
            network_mode="none",
            read_only=True,
            tmpfs={"/workspace": "rw,size=512m"},
            cpu_count=settings.SANDBOX_MAX_CPUS,
            mem_limit=f"{settings.SANDBOX_MAX_MEMORY_MB}m",
            name=f"devflow-sandbox-{execution_id}",
            remove=True,              # 自动删除
        )
        container_id = container.id[:12]
        self._active_containers[execution_id] = container_id
        return container_id

    def _exec_command(
        self,
        container_id: str,
        command: str,
        timeout: int = 60,
    ) -> tuple[int, str, str]:
        """
        在容器中执行命令。

        Returns:
            (exit_code, stdout, stderr)
        """
        container = self.client.containers.get(container_id)
        result = container.exec_run(
            cmd=["/bin/sh", "-c", command],
            workdir="/workspace",
        )
        return (
            result.exit_code,
            result.output.decode("utf-8", errors="replace") if result.output else "",
            "",
        )

    def _cleanup_container(self, execution_id: str) -> None:
        """清理容器（强制停止并删除）。"""
        container_id = self._active_containers.pop(execution_id, None)
        if container_id:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=5)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 执行流水线
    # ------------------------------------------------------------------

    def execute_pytest(
        self,
        task_id: str,
        repo_url: str,
        branch: str = "main",
        patches: list[dict] | None = None,
    ) -> SandboxResult:
        """
        完整执行流水线：
          1. 创建容器
          2. git clone 目标仓库
          3. 应用 Patch（如有）
          4. pip install -r requirements.txt（如存在）
          5. pytest --json-report
          6. 解析测试结果
          7. 清理容器

        Args:
            task_id: 任务 ID
            repo_url: 代码仓库 URL
            branch: 目标分支
            patches: 可选的 Patch 列表

        Returns:
            SandboxResult 结构化结果
        """
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        try:
            # Step 1: 创建容器
            container_id = self._create_container(execution_id)

            # Step 2: clone 仓库
            exit_code, stdout, stderr = self._exec_command(
                container_id,
                f"git clone --depth 1 --branch {branch} {repo_url} /workspace/repo",
                timeout=120,
            )
            if exit_code != 0:
                return self._build_error_result(
                    execution_id, task_id, "error", exit_code,
                    stderr or stdout, started_at,
                )

            # Step 3: 应用 Patch（若有）
            if patches:
                for patch in patches:
                    diff = patch.get("result", {}).get("diff", "")
                    if diff:
                        # 写入 diff 文件并 git apply
                        self._exec_command(
                            container_id,
                            f"cat > /tmp/patch.diff << 'PATCH_EOF'\n{diff}\nPATCH_EOF",
                        )
                        exit_code, stdout, stderr = self._exec_command(
                            container_id,
                            "cd /workspace/repo && git apply /tmp/patch.diff",
                        )
                        if exit_code != 0:
                            return self._build_error_result(
                                execution_id, task_id, "error", exit_code,
                                f"Patch 应用失败: {stderr or stdout}",
                                started_at,
                            )

            # Step 4: 安装依赖
            self._exec_command(
                container_id,
                "cd /workspace/repo && "
                "[ -f requirements.txt ] && pip install -q -r requirements.txt || true",
                timeout=180,
            )

            # Step 5: 运行 pytest
            pytest_cmd = (
                "cd /workspace/repo && "
                "python -m pytest --tb=short -v 2>&1"
            )
            start_time = time.time()
            exit_code, stdout, stderr = self._exec_command(
                container_id,
                pytest_cmd,
                timeout=settings.SANDBOX_TIMEOUT_SECONDS,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Step 6: 解析测试结果
            test_summary, test_failures = self._parse_pytest_output(stdout)

            finished_at = datetime.now()

            return SandboxResult(
                execution_id=execution_id,
                task_id=task_id,
                sandbox_type="test",
                status="success" if exit_code == 0 else "failure",
                exit_code=exit_code,
                timed_out=(duration_ms >= settings.SANDBOX_TIMEOUT_SECONDS * 1000),
                duration_ms=duration_ms,
                stdout=stdout[-50000:],  # 截断
                stderr=stderr[-10000:],
                test_summary=test_summary,
                test_failures=test_failures,
                started_at=started_at.isoformat(),
                finished_at=finished_at.isoformat(),
            )

        except Exception as e:
            return self._build_error_result(
                execution_id, task_id, "error", -1,
                f"沙箱异常: {str(e)}", started_at,
            )

        finally:
            self._cleanup_container(execution_id)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _parse_pytest_output(self, stdout: str) -> tuple[TestSummary, list[TestFailure]]:
        """解析 pytest 输出，提取测试汇总和失败详情。"""
        # 简单解析：正则匹配 pytest 的 summary line
        import re

        # 匹配: "X passed, Y failed, Z errors"
        summary_match = re.search(
            r'(\d+)\s+passed[,;]?\s*(\d+)\s+failed[,;]?\s*(\d+)\s+errors?',
            stdout,
        )
        if summary_match:
            total = sum(int(g) for g in summary_match.groups())
            passed = int(summary_match.group(1))
            failed = int(summary_match.group(2))
            errors = int(summary_match.group(3))
        else:
            # 无法解析时设为 0
            total = passed = failed = errors = 0

        summary = TestSummary(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
        )

        # 提取失败测试（匹配 FAILED test_name 行）
        failures = []
        for match in re.finditer(r'FAILED\s+(.+)', stdout):
            test_full = match.group(1).strip()
            parts = test_full.split("::")
            test_name = parts[-1] if parts else test_full
            test_file = parts[0] if parts else "unknown"

            failures.append(TestFailure(
                test_name=test_name,
                test_file=test_file,
                failure_type="assertion",
                message="测试失败",
                traceback="详见完整 stdout",
                is_new_failure=True,
            ))

        return summary, failures

    def _build_error_result(
        self,
        execution_id: str,
        task_id: str,
        status: str,
        exit_code: int,
        message: str,
        started_at: datetime,
    ) -> SandboxResult:
        """构建错误结果。"""
        finished_at = datetime.now()
        return SandboxResult(
            execution_id=execution_id,
            task_id=task_id,
            sandbox_type="test",
            status=status,
            exit_code=exit_code,
            timed_out=False,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            stdout=message,
            stderr="",
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )
