# DevFlow：两周冲刺计划

## 高强度交付版开发方案

| 项目 | 内容 |
|------|------|
| **文档版本** | v1.0（两周冲刺版） |
| **文档日期** | 2026-07-22 |
| **开发周期** | 14 天（含加班） |
| **团队规模** | 4 人 |
| **工作强度** | 每天 10-12 小时，周末不休 |
| **核心原则** | 砍掉一切非演示必需的功能，只保留能证明"多 Agent > 单 Agent"的最小闭环 |

---

## 目录

1. [范围裁剪：从六周到两周](#1-范围裁剪从六周到两周)
2. [两周总览](#2-两周总览)
3. [每日任务分解](#3-每日任务分解)
4. [四人并行工作表](#4-四人并行工作表)
5. [每日站会检查点](#5-每日站会检查点)
6. [风险与应急预案](#6-风险与应急预案)

---

## 1. 范围裁剪：从六周到两周

### 1.1 裁剪决策表

| 功能模块 | 原计划 | 两周版 | 裁剪理由 |
|----------|--------|--------|----------|
| **Agent 数量** | 5 个 | **4 个**（Req + Planner + Developer + Reviewer） | Security Agent 合并入 Reviewer 的风险检查项；答辩时说明"已完成 4 Agent，Security Agent 架构已预留" |
| **RAG 知识库** | Chroma + Embeddings | **完全砍掉** | Agent 通过工具直接读代码仓库即可；RAG 是锦上添花不是雪中送炭 |
| **PostgreSQL Checkpointer** | 完整实现 | **SQLite 足矣** | 两周内不需要演示数据库迁移；SQLite 开发速度更快 |
| **人工审批节点** | 暂停-审批-恢复全流程 | **自动审批 + 日志标记** | 保留 `await_approval` 节点但默认自动通过；高风险操作记录日志 |
| **OpenTelemetry + Prometheus** | 全链路追踪 | **结构化日志 + 前端直接展示** | 可观测性数据直接写 DB，前端读 DB 展示；不引入额外基础设施 |
| **SSE 流式推送** | 实时事件流 | **轮询 + 关键节点推送** | 前端每 2 秒轮询 `/tasks/{id}/status`；关键节点（测试完成、审查完成）用一次 SSE push |
| **Docker 安全策略** | seccomp + 命令白名单 + 日志脱敏 | **基础隔离**（无网络 + 资源限制） | 保留最核心的安全措施；白名单和脱敏在第 2 周后半段再说 |
| **评测任务** | 50 条 + 4 组消融实验 | **20 条 + 2 组实验**（单 Agent vs 多 Agent） | 数量减半但保证覆盖简单/Bug修复/重构三类；2 组实验足以证明多 Agent 增益 |
| **前端页面** | 6+ 页面 | **3 页面**（任务创建 + 详情 + 评测对比） | 历史页面和全局看板砍掉；核心是"能演示一条完整链路" |
| **CI/CD** | GitHub Actions | **手动运行** | 本地 `pytest + ruff` 通过即可 |
| **Docker Compose 全栈** | 一键启动 | **手动启动后端 + 前端** | 写一个 `start.sh` 脚本即可，不做完整容器编排 |
| **演示视频** | 2-3 分钟精剪 | **屏幕录制 + 旁白** | 不追求剪辑质量，内容完整即可 |

### 1.2 两周版保留的核心能力

```
用户输入需求
       │
       ▼
  📋 Requirement Agent    ←── 需求分析，输出验收条件
       │
       ▼
  📝 Planner Agent        ←── 浏览代码仓库，设计修改方案
       │
       ▼
  💻 Developer Agent      ←── 生成 unified diff，写入文件
       │
       ▼
  🐳 Sandbox (Docker)     ←── 应用 Patch，执行 pytest
       │
       ▼
  🔍 Reviewer Agent       ←── 代码审查 + 测试结果分析 + 安全风险标注
       │
       ▼
  ✅ 完成 / ❌ 返工 (≤3次)
```

### 1.3 两周版的技术栈（简化后）

| 层级 | 技术 | 备注 |
|------|------|------|
| 工作流 | LangGraph + 内存/SQLite Checkpointer | SQLite 只需改一行配置 |
| 后端 | FastAPI | 6 个核心端点 |
| Agent | LangChain + Pydantic | 4 个 Agent |
| LLM | DeepSeek / ChatAnywhere（免费/便宜） | 控制成本 |
| 沙箱 | Docker SDK for Python | 基础隔离 |
| 前端 | React | 3 个核心页面 |
| 持久化 | SQLite | 零配置 |
| 评测 | Python 脚本 | 2 组实验 |

---

## 2. 两周总览

```
Day 1 ───── 项目骨架 + 契约冻结
Day 2 ───── Mock Agent 全流程跑通
Day 3 ───── Docker 沙箱 + Agent 开始真实 LLM 调用
Day 4 ───── 3 个核心 Agent 完成（Req + Planner + Developer）
Day 5 ───── 端到端：第一次真实代码修改 + pytest
Day 6 ───── 条件路由（返工循环）+ Reviewer Agent
Day 7 ───── 前端：任务创建 + 详情 + 实时进度
────────────────── 第一周里程碑：修一个真实 Bug 并通过测试 ──────────────────
Day 8 ───── 系统加固：错误处理 + Checkpoint + 恢复
Day 9 ───── Reviewer 完善 + Security 检查项集成
Day 10 ──── 前端完成 + 评测数据集（20 条）
Day 11 ──── 单 Agent 基线构建 + 两组实验脚本
Day 12 ──── 实验运行 + 数据收集 + Bug 修复
Day 13 ──── 文档 + 演示视频 + 报告
Day 14 ──── 最终集成测试 + 彩排 + 交付
```

---

## 3. 每日任务分解

### Day 1：项目骨架 + 契约冻结

**目标**：仓库可运行，四个契约文件进入 `contracts/`，每个人知道自己的第一个任务是什么。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 初始化项目结构 + 依赖管理 | `pyproject.toml`、`requirements.txt` | 2h |
| | FastAPI 骨架（`/health` 可访问） | `app/main.py`、`app/api/` | 3h |
| | LangGraph 空图 + State 定义 | `app/graph.py`、`contracts/state.py` | 3h |
| | 项目仓库 + 分支保护规则 | GitHub repo | 1h |
| **B** | 4 个 Agent 的 Pydantic 模型全部写完 | `contracts/agent_result.py` | 4h |
| | 工具注册表骨架 | `app/tools/registry.py` | 2h |
| | 第一个 Agent（Requirement）Prompt 草稿 | `app/agents/requirement.py` | 2h |
| **C** | Docker 环境确认 + 拉取 Python 镜像 | 可 `docker run python:3.11-slim` | 2h |
| | 沙箱原型：创建容器 + 执行 `python --version` | `app/sandbox/manager.py` | 4h |
| | SandboxResult 模型实现 | `contracts/sandbox_result.py` | 2h |
| **D** | React 项目初始化 + 路由 | `frontend/` | 2h |
| | 任务创建页面（纯 UI，不接 API） | 表单布局 | 4h |
| | 10 条初始评测任务草稿 | `eval/tasks/` | 2h |

**Day 1 验收**：
- `curl localhost:8000/health` → `{"status": "ok"}`
- `contracts/` 下四个文件存在，内容经四人确认
- Docker 能创建容器
- 前端 `npm run dev` 能看到任务创建表单

---

### Day 2：Mock Agent 全流程跑通

**目标**：LangGraph 图的全部节点用 Mock Agent 串起来，从 API 提交请求到返回结果全链路通。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 实现全部 LangGraph 节点（8 个） | `graph.py` 完整 | 4h |
| | 条件路由函数（测试失败→返工、审查→安全→审批） | 路由逻辑 | 2h |
| | `POST /tasks` + `GET /tasks/{id}` 接入图中 | API → Graph 调用链 | 2h |
| | 内存 Checkpointer 接入 | `checkpointer.py` | 1h |
| **B** | 4 个 Agent 的 Mock 输出（返回合法的 Pydantic 对象） | `app/agents/mock.py` | 3h |
| | Agent 调用接口标准化（统一用 `AgentResult` 包装） | `app/agents/base.py` | 2h |
| | Requirement + Planner Agent Prompt 第二版 | `prompts/` | 2h |
| **C** | 沙箱：在容器内 clone 一个公开 Python 仓库 | `sandbox/setup.py` | 3h |
| | 沙箱：在容器内运行该仓库的 pytest | `sandbox/executor.py` | 3h |
| | 返回结构化 SandboxResult（Mock 数据先） | 结构化输出验证 | 1h |
| **D** | 任务详情页（状态展示 + 节点列表） | React 详情页 | 4h |
| | 轮询 `/tasks/{id}` 展示进度 | API 对接 | 2h |
| | 评测任务精炼到 10 条终版 | JSON 格式规范 | 1h |

**Day 2 验收**：
```bash
curl -X POST localhost:8000/tasks \
  -d '{"requirement": "给 factorial 函数加参数校验", "repo_url": "..."}'
# → 返回 task_id → 轮询 → phase 依次变化 → 最终 done
```

---

### Day 3：Docker 沙箱打通 + Agent 开始真实调用

**目标**：沙箱能真正执行 pytest 并返回结果；至少一个 Agent 接入真实 LLM。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | Agent 节点从 Mock 切换到真实调用（B 的接口） | `graph.py` 中节点对接 | 3h |
| | 事件记录（每次节点执行写入 DB） | `app/events.py` | 2h |
| | `GET /tasks/{id}/events` 端点 | 轮询接口 | 2h |
| **B** | LLM Factory（DeepSeek/ChatAnywhere） | `app/llm/factory.py` | 2h |
| | Requirement Agent 真实 LLM 调用 | 可调通并返回合法 `RequirementResult` | 4h |
| | 结构化输出校验 + 格式错误重试 | `app/agents/validator.py` | 2h |
| **C** | 完整沙箱执行流程：clone → apply patch → install → pytest | `sandbox/pipeline.py` | 4h |
| | 真实 SandboxResult 返回（不用 Mock） | 端到端验证 | 3h |
| **D** | 任务详情页：显示节点执行状态（Mock 数据驱动） | 状态流转 UI | 4h |
| | 评测任务补齐到 15 条 | `eval/tasks/` | 3h |

**Day 3 验收**：
- 沙箱对示例仓库执行 pytest，返回真实 SandboxResult（含测试通过/失败数）
- Requirement Agent 对真实需求返回合法结构化输出

---

### Day 4：3 个核心 Agent 完成

**目标**：Requirement + Planner + Developer 三个 Agent 都能稳定产出合法输出。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 错误分类处理（LLM 超时 / 沙箱超时 / 校验失败） | `app/error_handler.py` | 3h |
| | 迭代计数 + 最大迭代限制 | State 中的 iteration 字段逻辑 | 1h |
| | 集成 B 的 3 个 Agent 到图中 | 完整调用链 | 3h |
| **B** | Planner Agent 真实 LLM 调用 | 浏览仓库 + 生成 PlanResult | 4h |
| | Developer Agent 真实 LLM 调用 | 读取文件 + 生成 unified diff | 5h |
| | 上下文裁剪实现（每个 Agent 独立窗口） | `app/agents/context.py` | 2h |
| **C** | git apply 流程实现（Patch 应用到沙箱工作区） | `sandbox/patch.py` | 3h |
| | 测试失败详情解析（区分原有失败 vs 新引入失败） | `sandbox/parser.py` | 2h |
| | 沙箱异常处理（容器崩溃、OOM、超时） | 错误恢复逻辑 | 2h |
| **D** | 代码 Diff 展示组件（side-by-side） | React diff view | 4h |
| | 测试结果展示组件（通过/失败/详情） | React test panel | 3h |

**Day 4 验收**：
- 三个 Agent 各测试 3 种不同需求，结构化输出成功率 ≥ 80%
- Developer Agent 对简单需求能生成合法 unified diff

---

### Day 5：端到端——第一次真实代码修改 + pytest

**目标**：这是整个项目最关键的一天。系统对一个真实 Python 仓库的简单 Bug 完成修复并通过测试。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 全链路调试：API → Graph → Agent → Sandbox → 返回 | 端到端调通 | 4h |
| | 条件路由测试：测试失败 → 自动返工 → 重试 | 返工循环验证 | 2h |
| | 统一错误处理 + 日志 | 可定位问题 | 2h |
| **B** | Developer Agent 优化（提升 Patch 生成成功率） | Prompt 调优 | 4h |
| | 三个 Agent 的上下文裁剪调优 | 上下文窗口优化 | 2h |
| | Agent 调用 Token/耗时记录 | Invocation 元信息 | 1h |
| **C** | 沙箱稳定性测试（连续 10 次 pytest 执行无异常） | 可靠性验证 | 3h |
| | 多仓库兼容性（至少 2 个不同 Python 项目能跑通） | 兼容性测试 | 3h |
| **D** | 前端：从创建任务到看到结果的完整路径 | 全流程 UI | 4h |
| | 实时轮询状态更新 | 2 秒轮询 | 2h |
| | 评测任务 15 条最终定稿 | JSON | 1h |

**Day 5 验收（第一周核心里程碑）**：
- 对一个真实 Python 仓库提一个简单 Bug 修复需求
- 系统自动完成代码修改
- 沙箱中 pytest 全部通过
- 前端从创建到结果展示全链路通

---

### Day 6：条件路由 + Reviewer Agent

**目标**：返工循环真正工作；Reviewer Agent 能发现 Developer 的问题并触发返工。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 返工循环完整测试（构造一个 Developer 必然失败的场景） | 路由验证 | 3h |
| | 最大迭代硬限制测试（3 次后 → failed） | 终止验证 | 1h |
| | Checkpoint 持久化测试（中途重启服务 → 任务继续） | 恢复测试 | 3h |
| **B** | Reviewer Agent 完整实现（代码审查 + 测试结果分析） | `app/agents/reviewer.py` | 5h |
| | Reviewer → Developer 反馈传递 | 结构化 feedback | 2h |
| | 安全风险检查项集成到 Reviewer（SQL注入/硬编码密钥/路径遍历） | Reviewer 增强 | 2h |
| **C** | 沙箱资源限制验证（CPU 1核/内存 512MB/超时 300s） | 压力测试 | 3h |
| | 容器清理机制（正常退出 + 超时强制清理） | `sandbox/cleanup.py` | 2h |
| | 敏感信息掩码（日志中的 API Key 等） | 基础脱敏 | 2h |
| **D** | 人工审批面板（简化版：显示风险 + 自动通过按钮） | React 审批组件 | 3h |
| | 返工过程展示（每次迭代的 Diff 和测试结果） | 迭代历史 UI | 3h |

**Day 6 验收**：
- 测试失败时系统自动触发返工
- 3 次迭代后标记为 failed
- Reviewer 能指出 Developer 代码中的明显问题

---

### Day 7：前端完善 + 第 1 周收尾

**目标**：前端三个页面基本可用；第 1 周里程碑正式达成。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 第 1 周 Bug 修复 + 集成联调 | 全系统稳定 | 3h |
| | API 文档初稿（自动生成 + 手动补充） | OpenAPI JSON | 2h |
| | 第 1 周里程碑演示准备 | Demo 脚本 | 2h |
| **B** | 4 个 Agent 的 Prompt 终版 + 版本标记 | `prompts/v1/` | 3h |
| | Agent 单元测试（每个 Agent ≥ 3 个用例） | `tests/agents/` | 3h |
| | Token/费用统计模块 | `app/metrics.py` | 1h |
| **C** | 沙箱单元测试 + 异常场景覆盖 | `tests/sandbox/` | 3h |
| | Docker Compose 骨架（后端 + 前端） | `docker-compose.yml` | 2h |
| | 启动脚本 `start.sh` | 一键启动 | 1h |
| **D** | 任务详情页完善（Diff + 测试结果 + 时间线） | 完整详情页 | 4h |
| | 评测对比页面骨架 | 表格布局 | 2h |
| | 评测任务补齐到 18 条 | `eval/tasks/` | 1h |

**Day 7 验收——第 1 周里程碑**：
- ✅ 提交需求 → 系统自动完成代码修改 → pytest 通过
- ✅ 测试失败时自动返工（≤3 次）
- ✅ 服务重启后任务从 Checkpoint 恢复
- ✅ 前端可创建任务并看到完整执行过程

---

### Day 8：系统加固

**目标**：把第 1 周快速搭建的脆弱系统加固为可靠系统。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | SQLite Checkpointer 替换内存实现 | 持久化 Checkpoint | 3h |
| | 暂停/恢复/取消 API 完整实现 | 状态控制 | 3h |
| | 错误分类覆盖全部场景（LLM/沙箱/超时/校验/未知） | 错误矩阵测试 | 2h |
| **B** | Agent 异常处理（LLM 超时重试、格式错误重试） | 指数退避 + 最多 3 次 | 3h |
| | 4 个 Agent 的上下文裁剪微调 | 减少幻觉 | 2h |
| | Prompt 注入防护（基础） | 输入过滤 | 1h |
| **C** | 沙箱安全加固（命令白名单 + 路径校验） | 安全策略 v1 | 3h |
| | 容器超时 + OOM 强制清理测试 | 资源泄漏检测 | 2h |
| | 日志结构化（JSON 格式，含 trace_id） | `app/logging.py` | 2h |
| **D** | 前端错误处理（网络断开、超时、500） | 容错 UI | 3h |
| | 任务状态图组件（Mermaid 或自绘） | 流程图组件 | 3h |
| | 评测任务补齐到 20 条终版 | `eval/tasks/` | 1h |

**Day 8 验收**：
- 服务 `kill -9` 后重启，未完成任务从 SQLite Checkpoint 恢复
- 沙箱命令白名单生效（非白名单命令被拒绝）

---

### Day 9：Reviewer 完善 + 单 Agent 基线

**目标**：Reviewer Agent 稳定产出有价值的审查意见；单 Agent 基线可运行。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 审批节点实现（自动审批 + 高风险日志标记） | `await_approval` 简化版 | 2h |
| | 全链路集成测试（3 种不同需求类型） | 集成测试 | 3h |
| | 系统统计接口（总任务数/成功率/平均耗时） | `GET /tasks/stats` | 2h |
| **B** | Reviewer Agent 优化（降低误报率） | Prompt 调优 | 3h |
| | 单 Agent 基线 Agent 构建（一个 Agent 完成全部：分析→修改→测试） | `app/agents/single_agent.py` | 4h |
| | Agent 调用记录完整（reasoning 字段不再为空） | 可解释性 | 1h |
| **C** | 沙箱性能优化（镜像预构建、缓存 pip 依赖） | 加速执行 | 3h |
| | 监控指标收集（成功率/延迟/资源使用） | `sandbox/metrics.py` | 3h |
| **D** | Agent 执行时间线组件（瀑布图） | React 时间线 | 4h |
| | 成本/耗时统计卡片 | 数据展示 | 2h |
| | 单 Agent vs 多 Agent 对比页面骨架 | 对比表格 | 1h |

**Day 9 验收**：
- Reviewer 对 3 个不同 Patch 产出有区分度的审查意见
- 单 Agent 基线可独立运行

---

### Day 10：前端完成 + 评测准备

**目标**：前端 3 个页面全部可用；评测任务和脚本就绪。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 关键节点 SSE push（测试完成、审查完成） | 前端即时感知 | 3h |
| | 最终集成联调 + 边缘场景修复 | 稳定性 | 4h |
| **B** | 4 个 Agent 的最终 Prompt 定稿 | `prompts/final/` | 2h |
| | Agent 评测脚本（自动打分：结构化输出成功率、Patch 可用率） | `eval/agent_quality.py` | 4h |
| **C** | 沙箱最终稳定性测试（50 次连续执行） | 可靠性报告 | 3h |
| | Docker Compose 完善 + `start.sh` 调试 | 一键启动 | 2h |
| | 部署文档骨架 | `docs/deploy.md` | 1h |
| **D** | 任务详情页终版（所有组件集成） | 完整详情页 | 4h |
| | 评测对比页面功能完成 | 并排对比 | 2h |
| | 20 条评测任务最终验证（每条在目标仓库上可执行） | 任务验证 | 2h |

**Day 10 验收**：
- 三个前端页面功能完整
- 20 条评测任务全部可执行
- Docker Compose 可启动全栈

---

### Day 11：两组实验运行

**目标**：单 Agent vs 多 Agent 两组实验各跑完 20 条任务。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 实验运行监控（确保系统不崩） | 实时监控 | 2h |
| | 实验数据收集 Pipeline | `eval/collector.py` | 3h |
| | Bug 修复（实验中暴露的问题） | 热修复 | 3h |
| **B** | 单 Agent 组：20 条任务依次运行 | 实验组 A 原始数据 | 4h |
| | 多 Agent 组：20 条任务依次运行 | 实验组 B 原始数据 | 4h |
| **C** | 沙箱支撑两组实验（确保隔离、清理） | 运行保障 | 3h |
| | 资源使用数据收集 | 指标采集 | 3h |
| **D** | 实验进度展示页面 | 实时进度 | 3h |
| | 结果数据实时入库 | 数据持久化 | 2h |
| | 实验报告骨架 | Markdown 模板 | 2h |

**Day 11 验收**：
- 两组实验各完成 ≥ 15 条任务（允许部分失败，记录失败原因）

---

### Day 12：数据分析 + Bug 修复

**目标**：完成实验数据收集和分析；修复实验中发现的关键 Bug。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 分析工作流效率数据（调用轮数、返工次数） | 效率分析 | 3h |
| | 系统 Bug 集中修复 | 稳定性提升 | 3h |
| **B** | Agent 质量分析（哪些类型任务成功率低？为什么？） | Agent 分析 | 3h |
| | Agent Prompt 针对性优化 | 最后一轮调优 | 3h |
| **C** | 沙箱性能数据分析 | 瓶颈分析 | 2h |
| | 系统部署验证（在新机器上 `start.sh` 能否跑通） | 部署测试 | 3h |
| **D** | 10 项指标计算 + 可视化图表生成 | 指标图表 | 4h |
| | 实验报告初稿（含成功/失败案例分析） | 报告草稿 | 3h |

**Day 12 验收**：
- 10 项指标数据齐全
- 至少 3 个成功案例和 3 个失败案例的详细分析

---

### Day 13：文档 + 演示视频

**目标**：所有文档定稿；演示视频录制完成。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 架构图定稿 + 技术决策记录 | `docs/architecture.md` | 3h |
| | API 文档定稿 | `docs/api.md` | 2h |
| | 状态恢复 Demo 录制准备 | 演示脚本 | 2h |
| **B** | Agent 设计文档 | `docs/agent-design.md` | 3h |
| | 单 Agent vs 多 Agent 对比分析 | 对照文档 | 2h |
| **C** | 安全模型文档 | `docs/security.md` | 2h |
| | 部署文档定稿 | `docs/deploy.md` | 2h |
| | Worker 崩溃恢复 Demo | 演示脚本 | 2h |
| **D** | 实验报告定稿（含图表 + CSV 导出） | `docs/eval-report.md` | 3h |
| | 演示视频录制（屏幕录制 + 旁白） | MP4 | 3h |
| | README 定稿 | `README.md` | 1h |

**Day 13 验收**：
- 全部文档在 `docs/` 下
- 演示视频内容完整（需求提交 → 全流程 → 结果 → 评测对比）

---

### Day 14：最终集成测试 + 彩排 + 交付

**目标**：完整彩排一遍；整理最终交付物；GitHub 仓库 ready。

| 成员 | 任务 | 交付物 | 预计耗时 |
|------|------|--------|:--:|
| **A** | 全系统集成测试（完整回归） | 测试报告 | 3h |
| | GitHub 仓库整理（README/CHANGELOG/CONTRIBUTING） | Public repo | 2h |
| | 最终彩排 | 演示彩排 | 2h |
| **B** | Agent 测试全部通过 | 测试绿 | 2h |
| | 个人技术贡献说明 | 每人一份 | 2h |
| **C** | 沙箱测试全部通过 | 测试绿 | 2h |
| | Docker 镜像最终验证 | 可拉取可运行 | 1h |
| **D** | 前端最终检查 | 无 bug | 2h |
| | 实验数据最终验证 | CSV 可导出 | 1h |
| **全员** | 最终彩排 + 交付检查清单 | 全部 green | 2h |

**Day 14 验收——最终交付**：
- ✅ GitHub 仓库 public，`git clone` + `bash start.sh` 可运行
- ✅ 对一个示例仓库，从需求到代码修改到测试验证全链路跑通
- ✅ 两组消融实验数据齐全，多 Agent 优于单 Agent
- ✅ 全部文档在仓库 `docs/` 下
- ✅ 演示视频可播放
- ✅ 四份个人技术贡献说明

---

## 4. 四人并行工作表

### 4.1 A：系统架构与 LangGraph

| 天数 | 核心任务 | 状态 |
|:--:|------|:--:|
| D1 | 项目骨架 + FastAPI + LangGraph 空图 + State 定义 | ☐ |
| D2 | 全部 8 个节点 + 条件路由 + 内存 Checkpointer + API 对接 | ☐ |
| D3 | Agent 节点切入真实调用 + 事件记录 + 事件 API | ☐ |
| D4 | 错误分类 + 迭代计数 + 3 Agent 集成入图 | ☐ |
| D5 | 全链路调试 + 返工循环验证 + 统一错误处理 | ☐ |
| D6 | 返工循环完整测试 + 最大迭代硬限制 + Checkpoint 恢复测试 | ☐ |
| D7 | Bug 修复 + 集成联调 + API 文档 + 第 1 周 Demo 准备 | ☐ |
| D8 | SQLite Checkpointer + 暂停/恢复/取消 API | ☐ |
| D9 | 审批节点（简化版）+ 全链路集成测试 + 统计接口 | ☐ |
| D10 | SSE push + 最终集成联调 | ☐ |
| D11 | 实验监控 + 数据收集 + Bug 修复 | ☐ |
| D12 | 工作流效率分析 + 系统 Bug 集中修复 | ☐ |
| D13 | 架构图 + 技术决策 + API 文档 + 状态恢复 Demo | ☐ |
| D14 | 集成测试 + 仓库整理 + 彩排 | ☐ |

### 4.2 B：Agent 与工具

| 天数 | 核心任务 | 状态 |
|:--:|------|:--:|
| D1 | 4 Agent Pydantic 模型 + 工具注册表 + Requirement Prompt | ☐ |
| D2 | 4 Agent Mock 输出 + Agent 基类 + Req/Planner Prompt v2 | ☐ |
| D3 | LLM Factory + Requirement Agent 真实调用 + 校验器 | ☐ |
| D4 | Planner Agent + Developer Agent + 上下文裁剪 | ☐ |
| D5 | Developer Agent 优化 + 上下文调优 + Token 记录 | ☐ |
| D6 | Reviewer Agent 完整实现 + Reviewer→Developer 反馈 + 安全检查项 | ☐ |
| D7 | Prompt 终版 + Agent 单元测试 + Token/费用统计 | ☐ |
| D8 | Agent 异常处理 + 上下文裁剪微调 + Prompt 注入防护 | ☐ |
| D9 | Reviewer 优化 + 单 Agent 基线构建 + reasoning 完善 | ☐ |
| D10 | 4 Agent 最终 Prompt + Agent 质量评测脚本 | ☐ |
| D11 | 单 Agent 组实验运行 + 多 Agent 组实验运行 | ☐ |
| D12 | Agent 质量分析 + Prompt 针对性优化 | ☐ |
| D13 | Agent 设计文档 + 单 vs 多 Agent 对比分析 | ☐ |
| D14 | Agent 测试全部通过 + 个人技术贡献说明 | ☐ |

### 4.3 C：执行环境与可靠性

| 天数 | 核心任务 | 状态 |
|:--:|------|:--:|
| D1 | Docker 环境 + 沙箱原型（创建容器+执行命令）+ SandboxResult | ☐ |
| D2 | 沙箱 clone 仓库 + pytest 执行 + 结构化返回 | ☐ |
| D3 | 完整沙箱流水线（clone→patch→install→test）+ 真实 SandboxResult | ☐ |
| D4 | git apply 流程 + 测试失败解析 + 沙箱异常处理 | ☐ |
| D5 | 沙箱稳定性测试 + 多仓库兼容性 | ☐ |
| D6 | 资源限制验证 + 容器清理 + 日志脱敏 | ☐ |
| D7 | 沙箱单元测试 + Docker Compose 骨架 + start.sh | ☐ |
| D8 | 命令白名单 + 路径校验 + OOM 清理 + 结构化日志 | ☐ |
| D9 | 沙箱性能优化 + 监控指标收集 | ☐ |
| D10 | 沙箱稳定性最终测试 + Docker Compose 完善 + 部署文档 | ☐ |
| D11 | 沙箱支撑两组实验 + 资源使用数据收集 | ☐ |
| D12 | 沙箱性能分析 + 部署验证 | ☐ |
| D13 | 安全模型文档 + 部署文档 + 崩溃恢复 Demo | ☐ |
| D14 | 沙箱测试全部通过 + Docker 镜像验证 | ☐ |

### 4.4 D：前端与评测

| 天数 | 核心任务 | 状态 |
|:--:|------|:--:|
| D1 | React 初始化 + 任务创建页面 + 10 条评测任务草稿 | ☐ |
| D2 | 任务详情页 + 轮询 + 评测任务精炼 | ☐ |
| D3 | 节点状态展示 + 15 条评测任务 | ☐ |
| D4 | Diff 展示组件 + 测试结果组件 | ☐ |
| D5 | 全流程 UI + 实时轮询 + 15 条终稿 | ☐ |
| D6 | 审批面板 + 返工迭代展示 | ☐ |
| D7 | 详情页完善 + 评测对比骨架 + 18 条任务 | ☐ |
| D8 | 前端错误处理 + 状态图组件 + 20 条任务终版 | ☐ |
| D9 | Agent 时间线组件 + 成本/耗时卡片 + 对比页面 | ☐ |
| D10 | 详情页终版 + 评测对比页 + 20 条任务验证 | ☐ |
| D11 | 实验进度页 + 数据入库 + 报告骨架 | ☐ |
| D12 | 10 项指标计算 + 可视化图表 + 报告初稿 | ☐ |
| D13 | 实验报告定稿 + 演示视频 + README | ☐ |
| D14 | 前端最终检查 + 数据验证 + 彩排 | ☐ |

---

## 5. 每日站会检查点

### 5.1 每日站会议程（每天 9:00，15 分钟）

1. **昨天完成了什么？**（每人 2 分钟）
2. **今天要完成什么？**（每人 1 分钟）
3. **遇到什么阻塞？**（需要谁协助？）

### 5.2 关键检查点

| 天数 | 检查点 | 如果不达标 |
|:--:|------|-----------|
| **D1** | `contracts/` 下四个文件存在 + 四人签字 | 不能进入 D2，加班补完 |
| **D2** | Mock Agent 全流程走通（API → done） | D3 上午必须补齐，否则后续全堵 |
| **D3** | 沙箱真实执行 pytest 返回结果 | C 最优先任务，D3 不完成不睡觉 |
| **D4** | 3 个 Agent 真实 LLM 调用成功率 ≥ 80% | B 最优先，简化 Prompt 降级方案 |
| **D5** | **端到端：真实 Bug 修复 + pytest 通过** | **第一周核心里程碑，不惜代价达成** |
| **D7** | 前端全流程可用 + 第 1 周 Demo 就绪 | 前端是门面，不能丑 |
| **D10** | 前端终版 + 20 条评测任务 + 一键启动 | D11 实验依赖此检查点 |
| **D12** | 实验数据齐全 + 图表生成 | D13 文档依赖此检查点 |
| **D14** | 全部交付物 ready | 最终检查清单全部打勾 |

---

## 6. 风险与应急预案

### 6.1 最大风险：D5 无法完成端到端

**症状**：Developer Agent 生成的 Patch 无法通过 pytest。

**预案**（按优先级）：
1. 缩小 Bug 修复的难度（从"修逻辑 Bug"降为"修 import 语句"）
2. 手动辅助 Developer Agent（B 看 LLM 输出，手动修正后再喂回去）
3. 最坏情况：用一条手工编写的 Patch 演示全流程，Agent 调用记录证明 LLM 确实被调用了

### 6.2 次大风险：Agent 调用 LLM 不稳定

**预案**：
- 所有 Agent 调用预置 fallback 响应（合理的默认输出）
- 3 次重试后使用 fallback
- 答辩时说明"这是当前 LLM API 可靠性的限制，架构上已设计重试和降级机制"

### 6.3 时间不足时的砍刀顺序

如果进度落后，按以下顺序砍功能：

| 优先级 | 砍什么 | 影响 |
|:--:|------|------|
| 1 | 审批面板交互 → 改为纯日志 | 不影响核心流程 |
| 2 | SSE push → 纯轮询 | 前端体验略差 |
| 3 | 状态图实时高亮 → 静态图片 | 演示效果打折扣 |
| 4 | 时间线组件 → 简单列表 | 演示效果打折扣 |
| 5 | 评测从 20 条 → 15 条 | 数据量减少但够用 |
| 6 | SQLite Checkpointer → 内存 | 不能演示恢复 |
| 7 | Reviewer 审查 → 只做测试结果分析 | 审查维度减少 |
| 8 | **绝不砍**：端到端流程（需求→代码修改→测试→结果） | 这是项目存在的唯一证明 |

---

> **最后的话**：
>
> 两周做完六周的事，不是靠加班就能解决的——关键是把范围砍对。
>
> 这份计划的核心思路是：**只保留能证明"多 Agent > 单 Agent"的最小功能集**。
>
> 每天的任务都标了预计耗时，如果某天 12 小时做不完，说明当天的范围还需要砍，而不是加班到 16 小时。
>
> 祝顺利。🚀
