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
