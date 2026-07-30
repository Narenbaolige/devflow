# DevFlow

> 基于 LangGraph 的多 Agent 协同软件工程平台 — 输入需求，自动完成分析→规划→编码→测试→审查全流程。

**DevFlow** 是一个 AI 驱动的自动化软件工程系统。给定一个需求描述和代码仓库，五个专用 Agent 协同工作，完成从需求理解到代码审查的完整开发闭环。支持返工循环、中断审批、Checkpoint 恢复和实时事件流。

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **多 Agent 协同** | 5 个专用 Agent（Requirement / Planner / Developer / Reviewer + 单 Agent 基线），各司其职 |
| **完整流水线** | 12 节点 LangGraph 状态图：`init → analyze → plan → setup → develop → apply → test → review → security → finalize` |
| **工具调用** | Developer & Planner 可调用 9 种沙箱工具（读文件、列目录、搜索、写文件、执行命令等），基于真实代码生成修改 |
| **返工循环** | 测试失败或审查不通过时自动触发返工（≤3 次），Developer 根据 Reviewer 反馈修正代码 |
| **中断审批** | 安全风险评估为高风险时暂停流水线，等待人工审批后继续 |
| **实时事件** | SSE 端点实时推送每个节点的执行状态、Agent 调用结果、测试输出 |
| **双模式运行** | Mock 模式零配置即可运行全流程；Real 模式接入 DeepSeek/OpenAI 真实生成代码 |
| **沙箱隔离** | 代码修改和测试在独立沙箱中执行（默认本地 subprocess，可选 Docker 容器隔离） |
| **Checkpoint 持久化** | 支持 Memory（开发）和 PostgreSQL（生产）两种后端，服务重启后可恢复任务 |
| **前端界面** | React + TypeScript 前端，3 个页面（创建任务 / 任务详情 / 评测对比），SSE 实时更新 |
| **评测体系** | 20 条标准化评测任务，覆盖 5 个类别 × 4 个难度级别，支持单/多 Agent 消融实验对比 |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│   TaskCreate  │  TaskDetail (SSE)  │  EvalCompare       │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Server                         │
│   /tasks  │  /tasks/{id}/events  │  /tasks/stats        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                LangGraph StateGraph (12 nodes)            │
│                                                          │
│  init_task → analyze_requirement → plan_solution         │
│       → setup_workspace → develop_changes → apply_patches│
│       → run_tests → review_code → security_check         │
│       → await_approval / finalize                        │
│                                                          │
│  返工循环: review_code/test 失败 → develop_changes       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    Agents (5)                             │
│  Requirement │ Planner │ Developer │ Reviewer │ Single    │
│                                                          │
│  LLM Backend: DeepSeek / OpenAI / ChatAnywhere           │
│  Tool Calling: read_file / list_dir / grep / glob /      │
│                write_file / edit_file / sandbox_execute   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Sandbox                                │
│  Local (subprocess, 默认)  │  Docker (容器隔离)          │
│  git clone → pip install → apply patches → pytest        │
└─────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 前置要求

| 依赖 | 版本 | 说明 |
|------|:----:|------|
| Python | 3.11+ | — |
| Git | 2.30+ | — |
| Node.js | 18+ | 仅前端 |
| LLM API Key | — | Mock 模式不需要；真实模式需 DeepSeek / OpenAI Key |

> 默认无需 Docker。沙箱使用本地 subprocess，零额外依赖。

### 一键启动

```bash
# 1. 克隆
git clone https://github.com/Narenbaolige/devflow.git
cd devflow

# 2. 安装
python -m venv .venv
.venv\Scripts\activate      # Windows
python -m pip install -e ".[dev]"

cd frontend && npm install && cd ..

# 3. 启动
# Windows: 双击 start.bat
# 或手动：
python -m app.run            # 后端 → http://localhost:8000
cd frontend && npm run dev   # 前端 → http://localhost:5173
```

### LangGraph / LangChain Core 版本兼容性

DevFlow 使用 LangGraph 1.x，必须与 **LangChain Core 1.x** 一起安装。
如果虚拟环境中残留 `langchain-core 0.2.x`，后端启动时可能出现如下错误：

```text
ModuleNotFoundError: No module named 'langchain_core.language_models.chat_model_stream'
```

遇到该错误时，请关闭服务并在项目根目录重建虚拟环境：

```powershell
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

安装后可检查已解析的版本（不要使用 `langgraph.__version__`）：

```powershell
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print('langgraph=', version('langgraph')); print('langchain-core=', version('langchain-core'))"
```

`langchain-core` 必须显示为 `1.x`。通过检查后再运行 `start.ps1` 或 `start.bat`。

### Mock 模式（默认）

**无需配置任何 API Key**，开箱即用。Agent 返回预置数据，沙箱在内存中模拟执行，适合开发调试和 CI。

```bash
# .env 中控制
DEVFLOW_USE_MOCK=true    # Mock 模式（默认）
DEVFLOW_USE_MOCK=false   # 真实 LLM 调用 + 真实沙箱执行
```

### 真实模式

```bash
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY，设置 DEVFLOW_USE_MOCK=false
```

---

## 项目结构

```
devflow/
├── contracts/                  # 核心接口契约（P0 冻结）
│   ├── state.py                # TeamState — LangGraph 全局状态定义
│   ├── agent_result.py         # AgentResult — 5 个 Agent 的输入输出模型
│   ├── sandbox_result.py       # SandboxResult — 沙箱执行结果
│   └── event.py                # TaskEvent — 统一事件模型
│
├── app/
│   ├── main.py                 # FastAPI 应用入口 + 生命周期管理
│   ├── run.py                  # Windows 启动入口（SelectorEventLoop）
│   ├── config.py               # 配置管理（Settings dataclass，21 项）
│   ├── graph.py                # LangGraph 工作流（12 节点 + 条件路由 + 返工循环）
│   ├── checkpoint.py           # Checkpointer 生命周期管理（Memory / PostgreSQL）
│   ├── metrics.py              # Token 统计与费用估算（12 模型定价表）
│   │
│   ├── api/
│   │   └── tasks.py            # REST API：CRUD + 审批 + 取消 + SSE 事件流 + 统计
│   │
│   ├── agents/
│   │   ├── base.py             # AgentBase — 统一基类 + agent_node + 工具调用循环
│   │   ├── requirement.py      # Requirement Agent — 需求分析与验收条件提取
│   │   ├── planner.py          # Planner Agent — 文件级实现方案规划（支持工具调用）
│   │   ├── developer.py        # Developer Agent — 代码修改与 unified diff 生成（支持工具调用）
│   │   ├── reviewer.py         # Reviewer Agent — 代码审查 + 安全漏洞检测
│   │   ├── single_agent.py     # SingleAgent — 单 Agent 基线（消融实验用）
│   │   └── validator.py        # 结构化输出校验 + JSON 修复 + 重试机制
│   │
│   ├── tools/
│   │   ├── registry.py         # 工具注册表（9 工具 + 权限矩阵 + Agent 白名单）
│   │   ├── tool_impls.py       # 工具实现（read_file/list_dir/grep/glob/write_file/edit_file/exec）
│   │   ├── file_ops.py         # 文件操作底层实现
│   │   ├── search.py           # 代码搜索（grep）
│   │   └── sandbox_ops.py      # 沙箱命令执行 + 实例注册表（按 task_id 复用）
│   │
│   ├── sandbox/
│   │   ├── base.py             # BaseSandbox 抽象 + 路径安全校验 + 结构化日志
│   │   ├── local.py            # LocalSandbox — subprocess 执行，零依赖
│   │   ├── docker.py           # DockerSandbox — 容器隔离（CPU/内存限制 + tmpfs）
│   │   └── manager.py          # 多实例管理
│   │
│   └── llm/
│       └── factory.py          # LLM 工厂（DeepSeek / OpenAI / ChatAnywhere）
│
├── prompts/                    # Agent System Prompts（7 文件）
│   ├── requirement_agent.md    # 需求分析 Agent 提示词
│   ├── planner_agent.md        # 方案规划 Agent 提示词
│   ├── developer_agent.md      # 代码开发 Agent 提示词（含工具使用流程）
│   ├── developer_tools.md      # Developer 工具调用指南
│   ├── reviewer_agent.md       # 代码审查 Agent 提示词
│   ├── reviewer_security_rules.md  # 安全审查规则
│   └── single_agent.md         # 单 Agent 基线提示词
│
├── frontend/                   # React + TypeScript 前端
│   └── src/
│       ├── pages/
│       │   ├── TaskCreate/     # 创建任务页（含最近任务列表）
│       │   ├── TaskDetail/     # 任务详情页（实时状态 + 补丁/测试/审批面板）
│       │   └── EvalCompare/    # 评测对比页（统计卡片 + 图表）
│       ├── components/
│       │   ├── ApprovalPanel/  # 审批操作面板
│       │   ├── DiffViewer/     # Unified Diff 查看器
│       │   ├── TestPanel/      # 测试结果面板
│       │   ├── Timeline/       # 事件时间线
│       │   ├── StatsCard/      # 统计卡片
│       │   ├── StatusBadge/    # 任务状态徽章
│       │   ├── Toast/          # Toast 通知系统
│       │   └── Layout/         # 页面布局
│       ├── hooks/
│       │   ├── useTaskPolling.ts   # 2s 轮询 + 终态自动停止
│       │   ├── useTaskSSE.ts       # SSE 事件流订阅 + 重连
│       │   └── useNetworkStatus.ts # 在线/离线检测
│       ├── services/api.ts     # API 客户端（8 端点全覆盖）
│       └── types/task.ts       # 完整类型定义（30+ 接口/类型）
│
├── eval/                       # 评测体系
│   ├── runner.py               # 多 Agent 评测运行器（Mock / Real）
│   ├── single_agent_runner.py  # 单 Agent 基线运行器
│   ├── agent_quality.py        # 8 维度质量评分器
│   ├── real_sandbox_compare.py # 真实沙箱 A/B 对比实验
│   ├── setup_test_repo.py      # 测试仓库生成器（16 模块 + 有意的 Bug）
│   ├── compare_report.py       # 对比报告生成
│   └── tasks/
│       ├── tasks_20.py         # 20 条评测任务（5 类别 × 4 难度）
│       └── initial_10.py       # 初版 10 条任务
│
├── tests/                      # 测试套件（24 文件，331 tests）
│   ├── agents/                 # Agent 单元测试（7 文件）
│   ├── tools/                  # 工具测试（3 文件）
│   ├── sandbox/                # 沙箱测试（4 文件，含稳定性/多仓库测试）
│   ├── api/                    # API 端点测试
│   ├── llm/                    # LLM 工厂测试
│   ├── test_reducers.py        # Reducer 函数测试
│   ├── test_events.py          # 事件系统测试
│   ├── test_graph.py           # 图结构 + 路由测试
│   ├── test_prompts.py         # Prompt 文件验证
│   ├── test_integration.py     # 集成测试（全流程 + 返工 + 取消 + 审批）
│   ├── test_metrics.py         # 费用估算测试
│   └── test_d5_real_pipeline.py # D5 里程碑验证脚本
│
├── docs/                       # 项目文档（16 文件）
│   ├── DevFlow-Project-Blueprint.md   # 项目蓝图（v4.0）
│   ├── architecture.md         # 技术架构与设计决策
│   ├── api.md                  # API 接口文档
│   ├── agent-design.md         # Agent 设计文档
│   ├── eval-report.md          # 评测报告
│   ├── audit-report-2026-07-30.md  # 代码审计报告
│   └── ...
│
├── pyproject.toml              # 项目配置（ruff + pytest + mypy）
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .env.example                # 环境变量模板
├── start.bat / start.ps1       # Windows 一键启动脚本
└── setup.py
```

---

## Agent 体系

| Agent | 角色 | 模型 | 工具调用 | 职责 |
|-------|------|:--:|:--:|------|
| **Requirement** | 需求分析师 | Prompt-only | — | 理解需求，提取受影响模块和验收条件，评估置信度 |
| **Planner** | 方案架构师 | Prompt + Tools | ✅ | 浏览代码仓库，设计文件级实现方案，规划步骤依赖 |
| **Developer** | 代码工程师 | Prompt + Tools | ✅ | 读取代码，生成 unified diff，通过沙箱自测验证 |
| **Reviewer** | 代码审查员 | Prompt-only | — | 审查 patch 正确性、代码风格、安全漏洞（CWE） |
| **SingleAgent** | 全栈工程师 | Prompt-only | — | 单 Agent 基线：独自完成分析→编码→自审（消融实验用） |

### 工具调用流程（Developer & Planner）

```
LLM 决策 → 调用工具 → 沙箱执行 → 返回结果 → LLM 分析 → 下一轮 / 最终输出
              │                                          │
              └──── 最多 5 轮 ──────┘                    │
              │                                          │
    read_file / list_dir / grep / glob        结构化 JSON 输出（经验证）
    write_file / edit_file / sandbox_execute
```

---

## 沙箱系统

| 模式 | 实现 | 隔离级别 | 依赖 |
|------|------|:--:|------|
| **Local**（默认） | `subprocess.run()` | 进程级 | 无 |
| **Docker** | Docker SDK (`docker run`) | 容器级 | Docker Desktop |

### 沙箱生命周期

```
create → git clone → [Developer 工具探索] → apply patches → pip install → pytest → cleanup
  │                                                      │
  └── 同一 task_id 复用实例（文件持久） ──────────────────┘
```

### 安全措施

- 路径遍历检测（拒绝 `..`、绝对路径、Windows 盘符）
- `shlex.quote()` 防 shell 注入
- Docker 模式：CPU 限制 + 内存限制 + tmpfs 工作区
- 结构化 JSON 日志记录每条命令的执行详情

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/tasks` | 创建任务（需求 + 仓库 + 可选的超时/预算限制） |
| `GET` | `/tasks` | 列出所有任务（支持 `?limit=&offset=` 分页） |
| `GET` | `/tasks/stats` | 任务统计（阶段分布 / 平均迭代 / Token / 费用） |
| `GET` | `/tasks/{id}` | 查询任务状态与完整结果 |
| `GET` | `/tasks/{id}/events` | SSE 实时事件流 |
| `POST` | `/tasks/{id}/approve` | 审批通过（含反馈） |
| `POST` | `/tasks/{id}/reject` | 审批拒绝（触发返工） |
| `POST` | `/tasks/{id}/cancel` | 协作式取消任务 |
| `GET` | `/health` | 健康检查 |

---

## 评测体系

### 数据集

20 条标准化任务，覆盖 5 个类别 × 4 个难度级别：

| 类别 | 数量 | 示例 |
|------|:--:|------|
| `simple_fix` | 5 | 添加参数校验、修复 import 路径、修正变量名 typo |
| `bug_fix` | 5 | 除零保护、off-by-one、空列表处理 |
| `refactor` | 5 | 提取校验函数、简化嵌套 if、拆分方法、提取常量 |
| `feature` | 3 | 新增方法、重试机制、缓存装饰器 |
| `edge_case` | 2 | Unicode 文件名、空输入处理 |

### 消融实验

| 组别 | 架构 | 返工 |
|------|------|:--:|
| **单 Agent 基线** | 1 个 SingleAgent 完成全流程（分析→编码→自审） | 无 |
| **多 Agent 管道** | 4 Agent 协同（Requirement → Planner → Developer → Reviewer） | ≤3 次 |

### 质量评估维度（8 维）

结构化输出有效性、输出完整性、补丁可应用性、测试通过率、审查结果、Token 用量、费用、耗时。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 编排引擎 | LangGraph (StateGraph + Checkpointer + interrupt_before) |
| LLM 后端 | DeepSeek / OpenAI / ChatAnywhere（OpenAI 兼容协议） |
| API 框架 | FastAPI + Pydantic v2 + SSE (sse-starlette) |
| 前端 | React 18 + TypeScript + Vite + Recharts + CSS Modules |
| 沙箱 | subprocess (Local) / Docker SDK (Docker) |
| 持久化 | MemorySaver / AsyncPostgresSaver |
| 代码质量 | ruff + mypy + pre-commit |
| 测试 | pytest (310 core + 21 slow) |

---

## 项目统计

| 指标 | 数值 |
|------|:--:|
| Python 文件 | 70（~12,000 行） |
| TypeScript 文件 | 19（~530 行） |
| 测试 | 331（310 即时 + 21 慢速/网络依赖） |
| Graph 节点 | 12 |
| Agent | 5 |
| 工具 | 9 |
| 提示词文件 | 7 |
| 前端页面 | 3 |
| 前端组件 | 8 |
| API 端点 | 9 |
| 评测任务 | 20 |
| 文档 | 16 |

---

## 团队

| 模块 | 负责人 | 核心工作 |
|------|:--:|------|
| 系统架构 & 工作流 | A | LangGraph 编排、API、State、Checkpointer、审批流程、运行时管控 |
| Agent & Prompt & 工具 | B | 5 Agent、工具系统、Prompt 工程、LLM 集成、结构化输出 |
| 执行环境 & 可靠性 | C | 沙箱（Local/Docker）、pytest 集成、Patch 应用、安全检测 |
| 前端 & 系统评测 | D | React UI、SSE 实时更新、20 任务 Benchmark、消融实验 |

---

## 许可证

MIT
