"""API 接口测试。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI 测试客户端。"""
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查端点。"""

    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "devflow-api"


class TestTaskEndpoints:
    """任务管理端点。"""

    def test_create_task(self, client):
        """创建任务应返回 201 和 task_id。"""
        response = client.post("/tasks", json={
            "requirement": "给 factorial 函数添加参数校验，输入负数时抛出 ValueError",
            "repo_url": "https://github.com/example/demo-repo",
            "branch": "main",
        })
        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
        assert data["phase"] in ("init", "analyzing", "done")

    def test_get_task(self, client):
        """查询任务应返回 200。"""
        # 先创建一个任务
        create_resp = client.post("/tasks", json={
            "requirement": "修复 login 函数的空指针异常",
            "repo_url": "https://github.com/example/demo-repo",
        })
        task_id = create_resp.json()["task_id"]

        # 查询
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id

    def test_get_nonexistent_task(self, client):
        """查询不存在的任务应返回 404。"""
        response = client.get("/tasks/nonexistent")
        assert response.status_code == 404

    def test_list_tasks(self, client):
        """列出任务应返回 200。"""
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data

    def test_list_tasks_reads_checkpointer_after_memory_cache_is_cleared(self, client):
        """列表不应依赖进程内缓存，模拟重启后仍可枚举 checkpoint 任务。"""
        from app.api.tasks import _tasks_store

        create_resp = client.post("/tasks", json={
            "requirement": "验证持久化任务列表",
            "repo_url": "https://github.com/example/demo-repo",
        })
        task_id = create_resp.json()["task_id"]

        _tasks_store.clear()
        response = client.get("/tasks")
        assert response.status_code == 200
        assert any(task["task_id"] == task_id for task in response.json()["tasks"])

    def test_task_stats(self, client):
        """统计接口应暴露状态分布、迭代、耗时与模型用量字段。"""
        response = client.get("/tasks/stats")
        assert response.status_code == 200
        data = response.json()
        assert {"total_tasks", "phase_counts", "average_iterations", "total_cost_usd"} <= data.keys()

    def test_cancel_task(self, client):
        """取消任务应返回 200。"""
        create_resp = client.post("/tasks", json={
            "requirement": "测试取消",
            "repo_url": "https://github.com/example/demo-repo",
        })
        task_id = create_resp.json()["task_id"]

        response = client.post(f"/tasks/{task_id}/cancel")
        assert response.status_code == 200
        assert response.json()["phase"] == "cancelled"

    def test_task_events(self, client):
        """任务应暴露前端可消费的 SSE 事件流。"""
        create_resp = client.post("/tasks", json={
            "requirement": "测试事件流",
            "repo_url": "https://github.com/example/demo-repo",
        })
        task_id = create_resp.json()["task_id"]

        response = client.get(f"/tasks/{task_id}/events")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "data:" in response.text
