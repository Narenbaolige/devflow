# DevFlow 架构设计

> 草稿 v0.1 — Day 13 答辩文档原型

## 骨架层（A）：编排与后端

### 架构模式

- **状态机编排（State Machine Orchestration）**：用图结构（节点+边）显式管理流程走向
- **Orchestrator 模式**：A 是中枢，B（Agent）、C（沙箱）是它调度的下游服务
- **可恢复架构（Durable Execution）**：Checkpoint 机制保证崩溃/重启后从断点继续
- **Human-in-the-loop**：状态图中的中断点，高风险操作卡住等人工审批
- **RESTful API**：对外暴露标准 HTTP 接口

### 技术栈

| 用途 | 技术 |
|------|------|
| 工作流编排 | LangGraph（StateGraph） |
| Web 框架 | FastAPI |
| 持久化 | 内存 Checkpointer（开发期）→ SQLite（Day 8）→ PostgreSQL（后期） |
| 状态容器 | 全局 TeamState（Pydantic TypedDict） |
| 事件推送 | 轮询 + 关键节点 SSE push |

---

## 决策层（B）：Agent 与工具系统

### 架构模式

- **多 Agent Pipeline**：Requirement → Planner → Developer → Reviewer，职责单一，链式传递
- **结构化输出 / Schema 约束**：Agent 间不传裸文本，传 Pydantic 强类型对象
- **带反馈的迭代闭环**：Reviewer 意见回传 Developer 返工（上限 3 次）
- **上下文隔离 / 裁剪**：每个 Agent 只看到完成任务所需的最小信息
- **Tool Calling**：Agent 通过工具接口操作外部世界

### 技术栈

| 用途 | 技术 |
|------|------|
| 结构化输出 | Pydantic（RequirementResult, PlanResult, PatchResult, ReviewResult） |
| 输出类型约束 | Literal 枚举 |
| Prompt 管理 | `prompts/*.md` 版本化管理 |
| 工具集 | 文件读取、代码搜索、沙箱命令执行 |
| 容错 | LLM 调用重试（3 次）、格式校验失败重试、失败降级到 Mock |
| 对照基线 | 单 Agent Baseline（Day 9） |

---

## 执行层（C）：沙箱与可靠性

### 架构模式

- **沙箱隔离架构**：代码修改和测试在隔离环境执行
- **确定性结果契约**：对外返回统一 JSON 结构（exit_code / stdout / stderr）
- **资源受限架构**：CPU / 内存 / 执行时长强制上限
- **安全防御架构**：网络限制、路径校验，纵深防御
- **可观测性架构**：结构化日志 + 前端直接展示（2 周版砍掉 OpenTelemetry）

### 技术栈

| 用途 | 技术 |
|------|------|
| 沙箱（默认） | LocalSandbox（subprocess，零依赖） |
| 沙箱（加固） | DockerSandbox（容器隔离） |
| 命令执行 | `execute(command, cwd, timeout)` → CommandResult |
| 测试 | Agent 自行决定策略（pytest / npm test / cargo test） |

---

## 展示与评测层（D）：前端与实验

### 架构模式

- **事件驱动前端**：订阅状态变更，实时更新
- **管理台架构**：任务创建 / 详情 / 审批分页面
- **对照实验架构**：单 Agent vs 多 Agent 受控变量对比
- **自动化评测流水线**：批量调用 API + 轮询结果 + 汇总指标

### 技术栈

| 用途 | 技术 |
|------|------|
| 前端框架 | React |
| 实时通信 | 轮询（2 周版）+ SSE 关键推送 |
| 可视化 | 状态流转、Diff 展示、时间线 |
| 评测产出 | CSV 导出 + 图表（20 条评测任务） |
