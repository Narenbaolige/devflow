# DevFlow

> 基于 LangGraph 的多 Agent 协同软件工程平台

**DevFlow** 输入一个需求描述和代码仓库，自动完成需求分析 → 方案规划 → 代码修改 → 自动测试 → 代码审查 → 安全审查，支持返工循环、中断审批和 Checkpoint 恢复。

## 项目状态

| 项目 | 状态 |
|------|------|
| **两周冲刺** | Day 6 / 14 |
| **测试** | 310 tests，全部通过 |
| **4 Agent** | Requirement / Planner / Developer / Reviewer，支持 DeepSeek 真实调用 |
| **工作流** | 11 节点 LangGraph StateGraph + 5 条件路由 + 返工循环（≤3 次） |
| **沙箱** | Local 模式（默认，零依赖）/ Docker 模式（可选隔离） |
| **Checkpointer** | Memory（默认）/ PostgreSQL（可选，支持重启恢复） |

### Mock 模式

默认开启 Mock 模式，**无需配置任何 API Key 即可运行全流程**（Agent 返回预置假数据，沙箱返回假测试结果）。适合开发调试和 CI。

```bash
# .env 中控制
DEVFLOW_USE_MOCK=true    # Mock 模式（默认）
DEVFLOW_USE_MOCK=false   # 真实 LLM + 真实沙箱
```

关闭 Mock 模式前，需先在 `.env` 中配置 LLM API Key。

## 前置要求

| 依赖 | 最低版本 | 说明 |
|------|:--:|------|
| **Python** | 3.11+ | `python --version` |
| **Git** | 2.30+ | `git --version` |
| **LLM API Key** | — | Mock 模式下不需要；真实模式需 DeepSeek / OpenAI / ChatAnywhere |

> **默认无需 Docker。** 沙箱使用本地 subprocess 执行。如需隔离，安装 Docker Desktop 并设置 `SANDBOX_MODE=docker`。

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Narenbaolige/devflow.git
cd devflow

# 2. 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# .venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux

# 3. 安装依赖
pip install -e ".[dev]"

# 4. （可选）配置 LLM — 默认 Mock 模式无需 Key
cp .env.example .env
# 编辑 .env，填入 API Key，然后将 DEVFLOW_USE_MOCK 改为 false

# 5. 启动服务
python -m app.run
# 或: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后验证：

```bash
# 健康检查
curl http://localhost:8000/health

# 创建任务
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"requirement": "给 factorial 函数加参数校验", "repo_url": "https://github.com/example/demo-repo"}'

# 查询状态
curl http://localhost:8000/tasks/{task_id}

# 查询事件流
curl http://localhost:8000/tasks/{task_id}/events
```

## 项目结构

```
devflow/
├── contracts/              # 核心接口契约（项目宪法，P0 冻结）
│   ├── state.py            # TeamState — LangGraph 全局状态
│   ├── agent_result.py     # AgentResult — 4 Agent 输入输出模型
│   ├── sandbox_result.py   # SandboxResult — 沙箱执行结果
│   └── event.py            # TaskEvent — 统一事件模型
├── app/
│   ├── main.py             # FastAPI 入口 + 生命周期管理
│   ├── run.py              # Windows 兼容启动入口（SelectorEventLoop）
│   ├── config.py           # 配置管理（Settings dataclass）
│   ├── graph.py            # LangGraph 工作流（11 节点 + 5 条件路由）
│   ├── checkpoint.py       # Checkpointer 生命周期（Memory / PostgreSQL）
│   ├── metrics.py          # Token 统计与费用估算
│   ├── api/
│   │   └── tasks.py        # 任务 CRUD + 审批 + SSE 事件
│   ├── agents/
│   │   ├── base.py         # AgentBase — 统一基类 + agent_node
│   │   ├── requirement.py  # Requirement Agent — 需求分析
│   │   ├── planner.py      # Planner Agent — 方案规划
│   │   ├── developer.py    # Developer Agent — 代码生成
│   │   ├── reviewer.py     # Reviewer Agent — 代码审查 + 安全检测
│   │   ├── single_agent.py # SingleAgent — 单 Agent 基线（消融实验用）
│   │   └── validator.py    # 结构化输出校验 + JSON 提取 + 重试
│   ├── tools/
│   │   ├── registry.py     # 工具注册表 + 权限矩阵
│   │   ├── file_ops.py     # 文件读写工具（read/write/edit/list/glob）
│   │   ├── search.py       # 代码搜索（grep）
│   │   └── sandbox_ops.py  # 沙箱命令执行 + 实例注册表
│   ├── sandbox/
│   │   ├── base.py         # BaseSandbox 抽象 + CommandResult
│   │   ├── local.py        # LocalSandbox（subprocess，默认）
│   │   ├── docker.py       # DockerSandbox（Docker SDK）
│   │   └── manager.py      # SandboxManager（多实例管理）
│   └── llm/
│       ├── factory.py       # LLM 工厂（OpenAI / DeepSeek / ChatAnywhere）
│       └── __init__.py
├── tests/
│   ├── agents/             # Agent 单元测试（7 文件）
│   ├── tools/              # 工具测试（3 文件）
│   ├── sandbox/            # 沙箱测试（2 文件）
│   ├── api/                # API 测试
│   ├── llm/                # LLM 工厂测试
│   ├── test_reducers.py    # Reducer 函数测试
│   ├── test_events.py      # 事件系统测试
│   ├── test_graph.py       # 图结构 + agent_node 行为测试
│   ├── test_prompts.py     # Prompt 文件正确性验证
│   ├── test_integration.py # 集成测试（路由 + 节点 + 返工循环）
│   └── test_metrics.py     # 费用估算测试
├── prompts/                # Agent System Prompts（6 文件）
├── eval/
│   └── tasks/              # 评测任务数据集
├── docs/                   # 项目文档
│   ├── DevFlow-Project-Blueprint.md
│   ├── DevFlow-2Week-Sprint.md
│   ├── architecture.md
│   └── session-log-*.md
├── frontend/               # React 前端
├── pyproject.toml
├── setup.py
├── start.sh
├── .env.example
└── .gitignore
```

## 团队

| 角色 | 负责人 | 核心模块 |
|------|:--:|------|
| 系统架构与 LangGraph | A | Workflow、API、State、Checkpoint、审批流程 |
| Agent 与 Prompt | B | 4 Agent、Tools、Prompt、LLM、结构化输出 |
| 执行环境与可靠性 | C | Sandbox、pytest、Patch 应用、安全策略 |
| 前端与系统评测 | D | React UI、事件展示、Benchmark、实验分析 |

## 文档

- [项目蓝图](docs/DevFlow-Project-Blueprint.md) — 完整项目设计与开发方案
- [两周冲刺计划](docs/DevFlow-2Week-Sprint.md) — 高强度交付版 14 天计划
- [架构文档](docs/architecture.md) — 技术架构与设计决策
- [API 文档](docs/api.md) — 任务、审批、事件流与统计接口
- [契约文档](contracts/) — P0 冻结的核心数据结构

## 许可证

MIT
