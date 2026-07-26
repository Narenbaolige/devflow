# 工作日志 — 2026-07-26

## 负责人

A（LangGraph 与后端）

## 本次完成内容

### 1. 工作流控制改造

- 审批节点改为 LangGraph `interrupt_before` 中断点；任务进入 `awaiting_approval` 后不再自动通过。
- `POST /tasks/{id}/approve` 与 `POST /tasks/{id}/reject` 使用 checkpoint 恢复任务，不会重新从 `init_task` 开始执行。
- 测试失败和审查失败会递增 `iteration`，受 `max_iterations` 限制，避免无限返工。
- 新增协作式取消：`POST /tasks/{id}/cancel` 写入 `cancel_requested`，后续节点在执行边界停止产生副作用。

### 2. 状态与事件

`TeamState` 增加：

- `cancel_requested`
- `current_node`
- `events`

工作流节点会记录初始化、阶段完成、测试结果、返工、审批和完成事件。新增：

```text
GET /tasks/{task_id}/events
```

接口以 SSE 格式输出当前任务事件，供前端任务详情页消费。

### 3. Checkpointer 配置

- 默认使用 `MemorySaver`，便于本地开发。
- 新增 `app/checkpoint.py`，在应用生命周期内创建与释放 Checkpointer。
- 支持通过环境变量切换到 PostgreSQL：

```env
CHECKPOINTER_BACKEND=postgres
CHECKPOINTER_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/devflow
```

- 增加 `langgraph-checkpoint-postgres` 项目依赖。

## 修改文件

| 文件 | 说明 |
|---|---|
| `contracts/state.py` | 任务控制与事件状态字段 |
| `app/graph.py` | 审批中断/恢复、返工计数、取消检查、事件记录 |
| `app/api/tasks.py` | checkpoint 查询、审批恢复、取消与 SSE 事件接口 |
| `app/checkpoint.py` | 内存/PostgreSQL Checkpointer 生命周期管理 |
| `app/main.py` | 启动时装配持久化工作流 |
| `app/config.py`、`.env.example`、`pyproject.toml` | PostgreSQL Checkpointer 配置与依赖 |
| `tests/api/test_tasks.py`、`tests/test_integration.py` | SSE 与审批返工行为测试 |

## 验证结果

- Python 静态语法检查通过：`py_compile`。
- Git diff 格式检查通过：`git diff --check`。
- 全量自动测试通过：`187 passed in 4.03s`。
- 存在 3 条非阻塞警告：
  - FastAPI/Starlette TestClient 对当前 httpx 兼容层的弃用提示；
  - `TestFailure`、`TestSummary` 为 Pydantic 模型，pytest 因类名以 `Test` 开头而尝试收集后跳过。

## 依赖与后续事项

| 项目 | 负责人 | 状态 |
|---|---|---|
| 应用真实 Patch | C 提供沙箱执行能力，A 接入工作流节点 | 待集成 |
| 执行真实测试命令 | C 提供稳定的沙箱调用约定，A 接入路由和错误处理 | 待集成 |
| PostgreSQL 环境与恢复测试 | A | 待准备数据库后验证 |
| Windows PostgreSQL 驱动 | A | 已补充 `psycopg[binary]` 依赖，待重新安装验证 |
| Windows 异步事件循环 | A | 已切换为 Selector 策略，兼容 psycopg 异步连接 |
| Windows PostgreSQL 启动 | A | 新增 `python -m app.run`，在 Uvicorn 创建事件循环前固定使用 Selector |
| PostgreSQL 配置加载顺序 | A | 修复启动入口先读取 `.env` 再创建 settings，避免错误回退到内存 Checkpointer |
| 处理 TestClient 弃用提示与 Pydantic 模型收集警告 | A | 可延后处理，不阻塞交付 |
