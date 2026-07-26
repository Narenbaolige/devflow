# DevFlow

> 基于 LangGraph 的面向软件工程的多 Agent 协同智能体系统

**DevFlow** 是一个可恢复、可评测的多 Agent 软件交付平台。输入一个需求描述和代码仓库，系统自动完成需求分析、方案规划、代码修改、自动测试、代码审查和安全检查。

## 前置要求

| 依赖             | 最低版本 | 检查方式             |
| ---------------- | -------- | -------------------- |
| **Python** | 3.11+    | `python --version` |
| **Git**    | 2.30+    | `git --version`    |

> **默认无需 Docker。** 沙箱默认使用本地模式（subprocess 执行），零额外依赖。
> 如需隔离执行不受信任的代码，可安装 Docker Desktop 并设置 `SANDBOX_MODE=docker`。
>
> - Docker 镜像：`python:3.11-slim`
> - 国内网络建议配置镜像加速：Docker Desktop → Settings → Docker Engine → 添加 `"registry-mirrors": ["https://docker.1ms.run", "https://docker.xuanyuan.me"]`

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd devflow

# 2. 创建并激活 Python 虚拟环境
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (Git Bash)
source .venv/Scripts/activate
# macOS / Linux
source .venv/bin/activate

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 配置并启动
cp .env.example .env
# 编辑 .env，填入 LLM API Key（支持 OpenAI / DeepSeek / ChatAnywhere）

# Windows + PostgreSQL Checkpointer：使用兼容 psycopg 的启动入口
python -m app.run
# 本地内存 Checkpointer 开发时，也可使用：
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后验证：

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"requirement": "给 factorial 函数加参数校验", "repo_url": "https://github.com/example/demo-repo"}'
```

> **可选：切换到 Docker 沙箱模式**
>
> ```bash
> # 在 .env 中设置
> SANDBOX_MODE=docker
> # 然后拉取镜像
> docker pull python:3.11-slim
> ```

## 项目结构

```
devflow/
├── contracts/          # 核心接口契约（项目宪法）
│   ├── state.py        # TeamState — LangGraph 全局状态
│   ├── agent_result.py # AgentResult — Agent 输入输出
│   ├── sandbox_result.py # SandboxResult — 沙箱执行结果
│   └── event.py        # TaskEvent — 统一事件模型
├── app/
│   ├── main.py         # FastAPI 入口
│   ├── config.py       # 配置管理
│   ├── graph.py        # LangGraph 工作流定义
│   ├── api/            # API 路由
│   ├── agents/         # Agent 实现
│   ├── tools/          # 工具注册表
│   ├── sandbox/        # 沙箱引擎（local 默认 / docker 可选）
│   └── llm/            # LLM 工厂
├── tests/              # 测试
├── eval/               # 评测任务
├── prompts/            # Agent System Prompts
├── docs/               # 项目文档
└── frontend/           # React 前端
```

## 团队

| 角色                 | 负责人 | 核心模块                         |
| -------------------- | ------ | -------------------------------- |
| 系统架构与 LangGraph | A      | Workflow、API、State、Checkpoint |
| Agent 与知识增强     | B      | Agent、Tool、Prompt、RAG         |
| 执行环境与可靠性     | C      | Sandbox、测试、安全策略、监控    |
| 前端与系统评测       | D      | UI、事件展示、Benchmark          |

## 文档

- [项目蓝图](docs/DevFlow-Project-Blueprint.md) — 完整项目设计与开发方案
- [两周冲刺计划](docs/DevFlow-2Week-Sprint.md) — 高强度交付版计划
- [契约文档](contracts/) — 核心数据结构定义

## 许可证

MIT
