# DevFlow API 文档

默认服务地址：`http://127.0.0.1:8000`。交互式 Swagger 文档位于 `/docs`。

## 任务生命周期

```text
POST /tasks → init → analyzing → planning → developing → testing
            → reviewing → security_check → done
                              └→ awaiting_approval → approve / reject
```

测试或审查失败会返回 `developing`，最多返工 `max_iterations` 次；取消、超时或预算耗尽会停止后续节点。

## 创建任务

`POST /tasks`

请求体：

```json
{
  "requirement": "为 factorial 添加负数参数校验",
  "repo_url": "https://github.com/example/demo-repo",
  "branch": "main",
  "max_iterations": 3,
  "timeout_seconds": 900,
  "budget_limit_usd": 0.1
}
```

任务在后台执行，接口立即返回。`budget_limit_usd` 不传时使用服务端 `TASK_BUDGET_USD`；为 `null` 表示不限制。

响应示例：

```json
{
  "task_id": "a1b2c3d4",
  "phase": "init",
  "requirement": "为 factorial 添加负数参数校验",
  "repo_url": "https://github.com/example/demo-repo",
  "iteration": 0,
  "errors": [],
  "created_at": "2026-07-28T10:00:00",
  "approval_required": false,
  "approval_granted": false,
  "cancel_requested": false,
  "current_node": null,
  "deadline_at": "2026-07-28T10:15:00",
  "budget_limit_usd": 0.1,
  "budget_used_usd": 0.0
}
```

## 查询与列表

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/tasks/{task_id}` | 查询单个任务最新状态；PostgreSQL Checkpointer 下重启后仍可读取。 |
| `GET` | `/tasks?limit=20&offset=0` | 分页列出任务。`limit` 范围为 1–100。 |
| `GET` | `/tasks/stats` | 获取任务状态、迭代、耗时、Token 与费用汇总。 |

`GET /tasks/stats` 响应示例：

```json
{
  "total_tasks": 12,
  "phase_counts": {"done": 8, "failed": 2, "awaiting_approval": 1, "developing": 1},
  "running_tasks": 1,
  "completed_tasks": 8,
  "failed_tasks": 2,
  "cancelled_tasks": 0,
  "awaiting_approval_tasks": 1,
  "average_iterations": 0.75,
  "average_duration_ms": 12650.4,
  "total_input_tokens": 4300,
  "total_output_tokens": 1200,
  "total_cost_usd": 0.0042
}
```

## 审批与取消

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/tasks/{task_id}/approve` | 仅适用于 `awaiting_approval`；从 checkpoint 恢复并继续执行。 |
| `POST` | `/tasks/{task_id}/reject` | 仅适用于 `awaiting_approval`；携带反馈进入返工。 |
| `POST` | `/tasks/{task_id}/cancel` | 请求取消后台工作流，状态变为 `cancelled`。 |

审批请求体：

```json
{"feedback": "请确认依赖升级不会破坏兼容性"}
```

非等待审批状态调用 approve/reject 返回 `409`；不存在任务返回 `404`。

## 事件流

`GET /tasks/{task_id}/events`

响应类型为 `text/event-stream`，以 SSE 格式回放该任务已记录的事件。常见事件包括：

- `node_complete`：工作流节点完成；
- `agent_complete`：Agent 调用完成，包含 token、费用和耗时；
- `test_result`：沙箱测试完成；
- `approval_required`：发现高风险，等待人工审批；
- `error`：超时、预算或执行错误；
- `task_complete`：任务完成。

示例：

```text
event: agent_complete
data: {"task_id":"a1b2c3d4","node_name":"planner","message":"planner Agent 完成"}
```

当前接口回放历史事件；前端可定期重新请求以获得最新进度。

## 健康检查

`GET /health`

```json
{"status":"ok","version":"0.1.0","service":"devflow-api"}
```

## 配置与持久化

默认使用内存 Checkpointer，适合本地 Mock 开发。要跨服务重启恢复任务，请设置：

```env
CHECKPOINTER_BACKEND=postgres
CHECKPOINTER_DATABASE_URL=postgresql://postgres:password@localhost:5432/devflow
```

Windows 使用 PostgreSQL 异步 Checkpointer 时请通过 `python -m app.run` 启动服务。
