# DevFlow：基于 LangGraph 的面向软件工程的多 Agent 协同智能体开发

## 项目设计与开发方案文档（两周冲刺版）

| 项目 | 内容 |
|------|------|
| **项目名称** | DevFlow |
| **项目全称** | 基于 LangGraph 的面向软件工程的多 Agent 协同智能体开发 |
| **文档版本** | v4.0（两周冲刺终版） |
| **文档日期** | 2026-07-28 |
| **开发周期** | 14 天 |
| **团队规模** | 4 人 |
| **代码仓库** | https://github.com/Narenbaolige/devflow |

---

## 目录

1. [项目概述](#1-项目概述)
2. [核心能力](#2-核心能力)
3. [系统架构设计](#3-系统架构设计)
4. [核心数据结构与接口契约](#4-核心数据结构与接口契约)
5. [Agent 体系设计](#5-agent-体系设计)
6. [工作流设计](#6-工作流设计)
7. [工具系统](#7-工具系统)
8. [沙箱与执行引擎](#8-沙箱与执行引擎)
9. [前端与评测平台](#9-前端与评测平台)
10. [团队角色与职责](#10-团队角色与职责)
11. [十四天开发计划](#11-十四天开发计划)
12. [协作规则与工程规范](#12-协作规则与工程规范)
13. [风险管理与降级方案](#13-风险管理与降级方案)
14. [成功标准与验收条件](#14-成功标准与验收条件)
15. [最终交付清单](#15-最终交付清单)

---

## 1. 项目概述

### 1.1 项目背景

在传统软件开发过程中，需求分析、代码编写、测试调试、代码审查等环节通常需要开发人员反复交互完成，存在以下痛点：

- **信息传递损耗**：需求 → 设计 → 编码各阶段之间存在理解偏差和重复沟通
- **重复工作多**：相似的 Bug 修复、代码审查模式反复出现，缺乏知识复用
- **流程割裂**：分析、开发、测试、审查各环节工具独立，缺乏统一的编排层
- **质量不可量化**：代码审查的深度、测试的有效性难以标准化评估

本项目面向软件工程开发场景，设计并实现一个基于 **LangGraph** 的多 Agent 协同智能体系统。系统模拟真实软件开发团队的协作模式，通过多个具有不同专业职责的 AI Agent 协同完成软件开发流程中的关键任务。

### 1.2 项目定义

**DevFlow** 是一个基于 LangGraph 的**多 Agent 协同软件交付平台**，支持工作流状态持久化、任务中断恢复、以及可量化的 Agent 能力评测。

核心流程：

```
用户输入软件需求
       │
       ▼
  📋 需求分析 Agent    →  理解需求、识别范围、输出验收条件
       │
       ▼
  📝 方案规划 Agent    →  分析代码仓库、设计修改步骤、评估风险
       │
       ▼
  💻 代码开发 Agent    →  生成 unified diff、应用 Patch
       │
       ▼
  🐳 沙箱测试执行      →  隔离环境、pytest 自动运行
       │
       ▼
  🔍 代码审查 Agent    →  代码质量检查 + 测试结果分析 + 安全风险标注
       │
       ▼
  ✅ 完成 / ❌ 返工     →  最多 3 次迭代
```

### 1.3 项目目标

| 目标维度 | 具体目标 |
|----------|---------|
| **多 Agent 协同** | 4 个专业 Agent 分工协作，非单一 Agent 完成所有任务 |
| **状态化工作流** | LangGraph 条件路由、Checkpoint 持久化、故障恢复 |
| **真实代码操作** | Agent 读取仓库、搜索文件、生成 diff、应用 Patch |
| **安全可执行** | 沙箱隔离执行环境 |
| **自动测试验证** | pytest 自动运行，结构化返回结果，失败触发返工 |
| **可量化评测** | 22 条可重复评测任务 + 单 Agent vs 多 Agent 消融实验对比 |

### 1.4 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **工作流编排** | LangGraph | 原生 StateGraph、条件路由、Checkpoint |
| **后端 API** | FastAPI | 高性能异步、自动文档、SSE 支持 |
| **Agent 框架** | LangChain + LangGraph | 工具调用成熟、技术栈一致 |
| **LLM 后端** | DeepSeek / ChatAnywhere | 控制开发成本 |
| **持久化** | MemorySaver（开发）/ PostgreSQL（生产） | 渐进式复杂度 |
| **沙箱** | Local（subprocess）/ Docker（可选） | 灵活切换 |
| **前端** | React + TypeScript | 生态丰富 |
| **评测** | Python 脚本 | 灵活、可复现 |

---

## 2. 核心能力

### 2.1 两周版核心能力

| 能力 | 说明 |
|------|------|
| 🤖 **多 Agent 协同** | Requirement → Planner → Developer → Reviewer，安全审查并入 Reviewer |
| 🔄 **LangGraph 编排** | 条件路由 + 返工循环（≤3 次）+ Checkpoint 持久化 |
| 🛠️ **工具系统** | 文件读写、代码搜索、diff 生成、沙箱命令执行，带权限矩阵 |
| 🐳 **沙箱执行** | LocalSandbox（本地 subprocess）+ DockerSandbox（可选），支持 pytest 结构化返回 |
| 🧪 **自动测试** | pytest 执行 + 失败分类 + 自动触发返工 |
| 📊 **可观测性** | Agent 调用记录（Token / 耗时 / 费用 / 决策理由）+ 事件流 |
| 📈 **消融实验** | 22 条评测任务 + 单 Agent vs 多 Agent 两组对比 |
| 🛡️ **安全审查** | Reviewer Agent 含安全检查维度，高风险触发人工审批 |

### 2.2 单 Agent vs 多 Agent 对比

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **多 Agent 管道** | 4 Agent 分工协作，含沙箱反馈循环 | 复杂 Bug 修复，需要迭代验证 |
| **单 Agent 基线** | 一个 Agent 完成全部工作 | 简单任务、消融实验对照组 |

---

## 3. 系统架构设计

### 3.1 系统全景架构

```
┌──────────────────────────────────────────────────────────────┐
│                     D：React 管理界面                          │
│  任务创建 │ 状态图实时高亮 │ Agent 时间线 │ Diff 展示            │
│  测试结果 │ 审批面板 │ 成本看板 │ 评测对比                       │
└──────────────────────────┬───────────────────────────────────┘
                           │ 轮询 + 关键事件 push
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  A：FastAPI 网关层                              │
│  POST /tasks  │  GET /tasks/{id}  │  POST /tasks/{id}/approve │
│  POST /tasks/{id}/reject  │  POST /tasks/{id}/cancel         │
│  GET /tasks/{id}/events  │  GET /health                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                A：LangGraph 编排引擎                            │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  StateGraph 主流程                        │ │
│  │                                                          │ │
│  │  [分析] → [规划] → [开发] → [测试] → [审查] → [安全] → [审批]  │ │
│  │    ↑                  ↑         ↓                        │ │
│  │    └──────────────────┴─── 返工循环（≤3次）                │ │
│  │                                                          │ │
│  │  条件路由 │ Checkpointer │ 错误分类 │ 迭代控制               │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────┬────────────────────────────────┘
       │                      │
       ▼                      ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  B：Agent 层      │  │  C：沙箱执行引擎               │
│                  │  │                              │
│  Requirement     │  │  仓库 clone + Patch 应用       │
│  Planner         │  │  pip install + pytest 执行     │
│  Developer  ─────┼──│▶ 测试结果结构化解析             │
│  Reviewer        │  │  超时控制 + 资源清理             │
│  (含安全检查)     │  │                              │
│                  │  │                              │
│  工具注册表       │  │                              │
│  Prompt 管理     │  │                              │
└──────────────────┘  └──────────────────────────────┘
       │                      │
       └──────────┬───────────┘
                  ▼
         ┌────────────────┐
         │   持久化层       │
         │  · Checkpointer │
         │  · 任务状态      │
         │  · 事件日志      │
         └────────────────┘
```

### 3.2 分层架构

```
┌─────────────────────────────────────────┐
│        表示层（D 负责）                    │  React SPA
│        任务界面 / 状态图 / 时间线 / 评测     │  轮询 + push
├─────────────────────────────────────────┤
│        API 网关层（A 负责）                 │  FastAPI
│        路由 / 事件 / 统计                   │
├─────────────────────────────────────────┤
│        编排层（A 负责）                     │  LangGraph
│        StateGraph / 条件路由 / Checkpoint  │
├─────────────────────────────────────────┤
│        Agent 层（B 负责）                   │  LangChain
│        4 Agent / 工具 / Prompt             │  Pydantic
├─────────────────────────────────────────┤
│        执行层（C 负责）                     │  subprocess/Docker
│        沙箱 / pytest / 安全策略             │
├─────────────────────────────────────────┤
│        持久化层（A + C 负责）               │  Memory/PostgreSQL
│        Checkpointer / 状态 / 事件          │
└─────────────────────────────────────────┘
```

### 3.3 核心设计原则

| 原则 | 说明 |
|------|------|
| **接口先行** | `TeamState`、`AgentResult`、`SandboxResult` 为项目宪法，P0 冻结，四人评审 |
| **故障可恢复** | 关键节点后保存 Checkpoint，服务重启从断点恢复 |
| **安全默认** | 沙箱隔离执行，超时和资源硬限制 |
| **可观测内置** | 每个 Agent 的决策理由、工具调用、Token 消耗均记录 |
| **垂直集成** | 每周交付完整链路：前端 → API → 编排 → Agent → 沙箱 → 前端 |

---

## 4. 核心数据结构与接口契约

> **项目宪法。`contracts/` 模块已实现，P0 冻结，修改需四人评审。**

### 4.1 模块结构

```
contracts/
├── __init__.py          # 统一导出
├── state.py             # TeamState — LangGraph 全局状态
├── agent_result.py      # AgentResult — 所有 Agent 的输入输出契约
├── sandbox_result.py    # SandboxResult — 沙箱执行结果
└── event.py             # TaskEvent — 统一事件模型
```

### 4.2 TeamState

```python
class TeamState(TypedDict):
    # 任务层 [A]
    task_meta: TaskMeta                    # task_id, repo_url, branch, requirement
    phase: Literal["init", "analyzing", "planning", "developing",
                   "testing", "reviewing", "security_check",
                   "awaiting_approval", "done", "failed", "cancelled"]
    iteration: int                         # 当前返工次数
    max_iterations: int                    # 默认 3

    # 控制层 [A]
    approval_required: bool
    approval_granted: bool
    approval_feedback: str
    cancel_requested: bool
    deadline_at: str | None
    budget_limit_usd: float | None
    budget_used_usd: float
    current_node: str | None
    events: Annotated[list[dict], "append"]
    errors: Annotated[list[ErrorRecord], "append"]

    # Agent 产出物层 [B 写入]
    requirement_analysis: Optional[dict]   # RequirementResult.model_dump()
    plan: Optional[dict]                  # PlanResult.model_dump()
    patches: Annotated[list[dict], "merge_by_file"]  # 按 file_path 去重
    review: Optional[dict]               # ReviewResult.model_dump()
    security_review: Optional[dict]      # SecurityResult.model_dump()

    # 沙箱层 [C]
    sandbox_results: Annotated[list[dict], "append"]
```

### 4.3 AgentResult

```python
# 5 个枚举角色
AgentRole: StrEnum = "requirement" | "planner" | "developer" | "reviewer" | "security"

# 各 Agent 输出模型
RequirementResult:  summary, affected_modules, acceptance_criteria, ambiguity_flags, confidence
PlanResult:         approach, steps[], risk_points, estimated_changed_files, confidence
PatchResult:        file_path, original_snippet, patched_snippet, diff, change_type
ReviewResult:       passed, risk_level, issues[], summary, actionable_feedback
SecurityResult:     passed, issues[], summary, requires_approval

# 统一包装
AgentResult:
    agent_role, success, result, error, invocation, reasoning, next_action

# 调用元信息
AgentInvocation:
    agent_role, model, input_tokens, output_tokens, cost_usd, duration_ms, retry_count
```

---

## 5. Agent 体系设计

### 5.1 Agent 总览

```
┌──────────────────────────────────────────────────────────┐
│                    Agent 系统（B 负责）                     │
│                                                           │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐              │
│  │Requirement│  │ Planner  │  │Developer │              │
│  │   Agent   │  │  Agent   │  │  Agent   │              │
│  │           │  │          │  │          │              │
│  │ · 理解需求 │─▶│ · 设计步骤│─▶│ · 生成代码│              │
│  │ · 识别范围 │  │ · 评估风险│  │ · 生成Diff│              │
│  │ · 验收条件 │  │ · 文件定位│  │ · 应用修改│              │
│  └───────────┘  └──────────┘  └────┬─────┘              │
│                                    │                     │
│            ┌───────────────────────┘                     │
│            ▼                                            │
│  ┌──────────────────────────────────┐                   │
│  │         Reviewer Agent           │                   │
│  │  · 代码质量审查                   │                   │
│  │  · 测试结果分析                   │                   │
│  │  · 安全风险标注（含 CWE 映射）     │                   │
│  │  · 返工建议生成                   │                   │
│  └──────────────────────────────────┘                   │
│                                                           │
│  关键设计决策：                                             │
│  · 无独立 Security Agent — 安全审查并入 Reviewer             │
│  · 无独立 Tester Agent — 测试执行归沙箱（C），分析归 Reviewer │
│  · 每个 Agent 独立上下文窗口 — 只看到完成任务所需的最小信息     │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Agent 详细定义

#### 5.2.1 Requirement Agent（需求分析）

| 属性 | 内容 |
|------|------|
| **角色** | 资深软件需求分析师 |
| **输入** | 用户需求原文 |
| **输出** | `RequirementResult` |

**核心指令**：一句话概述需求真实意图；推断受影响模块；提取可验证的验收条件；标记模糊点（置信度 < 0.6 时触发人工审批）。

#### 5.2.2 Planner Agent（方案规划）

| 属性 | 内容 |
|------|------|
| **角色** | 资深软件架构师 |
| **输入** | `RequirementResult` |
| **输出** | `PlanResult` |

**核心指令**：设计具体到文件级别的修改步骤；每个步骤原子性、可独立验证；标注步骤依赖关系；识别技术风险点和备选方案。

#### 5.2.3 Developer Agent（代码开发）

| 属性 | 内容 |
|------|------|
| **角色** | 资深软件工程师 |
| **输入** | `PlanResult` + Review 反馈（如有返工） |
| **输出** | `PatchResult`（每个修改文件一个） |

**核心指令**：基于方案生成 unified diff；使用标准 diff 格式（含 `@@` hunk 头部和上下文行）；`file_path` 仅用相对路径；`original_snippet` 尽可能接近真实代码以支持多种 patch 应用方式；返工时精确定位 Reviewer 反馈中的问题。

#### 5.2.4 Reviewer Agent（代码审查 + 测试分析 + 安全检查）

| 属性 | 内容 |
|------|------|
| **角色** | 严格的代码审查者 + 安全分析者 |
| **输入** | `PatchResult` + `SandboxResult` |
| **输出** | `ReviewResult`（含安全问题） |

**核心指令**：审查正确性、完整性、可维护性、回归风险；分析测试结果（区分原有失败 vs 新引入失败）；安全扫描（注入风险、硬编码凭据、路径遍历、敏感信息泄露，标记 CWE 编号）；未通过时给出可执行的返工指令。

### 5.3 上下文管理策略

| Agent | 可见上下文 | 不可见上下文 |
|-------|-----------|-------------|
| **Requirement** | 需求原文 + 仓库基本信息 | 文件内容、历史对话 |
| **Planner** | RequirementResult + 需求分析 | 历史 Patch、LLM 原始对话 |
| **Developer** | PlanResult + 当前 Review 反馈 | 其他步骤细节、原始需求 |
| **Reviewer** | PatchResult + SandboxResult（含失败详情） | Planner 方案细节 |

### 5.4 SingleAgent（消融实验基线）

为量化多 Agent 协同的实际增益，额外构建了一个 **单 Agent 基线**：一个 Agent 完成需求分析、方案规划、代码开发、自我审查的全部工作。用于在相同评测任务集上与 4-Agent 管道进行对比。

---

## 6. 工作流设计

### 6.1 主工作流状态图

```
init_task
  └→ analyze_requirement
       ├→ [confidence < 0.6]      await_approval (interrupt)
       ├→ [failed]                handle_error → END
       └→ [normal]                plan_solution
                                    └→ develop_changes (iteration++)
                                         └→ apply_patches (sandbox: clone + patch apply)
                                              └→ run_tests (sandbox: pip install + pytest)
                                                   ├→ [all pass]        review_code
                                                   ├→ [fail, retry]     develop_changes (rework loop)
                                                   └→ [fail, max_iter]  handle_error → END
                                                        └→ security_check
                                                             ├→ [safe]   finalize → END
                                                             └→ [risk]   await_approval (interrupt)
                                                                          ├→ [approve] finalize → END
                                                                          └→ [reject]  develop_changes (rework)
```

### 6.2 节点定义

| 节点 | Owner | 说明 |
|------|:--:|------|
| `init_task` | A | 初始化任务元信息 |
| `analyze_requirement` | B | Requirement Agent 调用 |
| `plan_solution` | B | Planner Agent 调用 |
| `develop_changes` | B | Developer Agent 调用 |
| `apply_patches` | C | 沙箱中 clone 仓库 + 应用 Patch（三层兜底） |
| `run_tests` | C | pip install + pytest 执行 + 结果解析 |
| `review_code` | B | Reviewer Agent（含安全审查） |
| `security_check` | B | 高风险审批决策 |
| `await_approval` | A | 审批中断点（interrupt_before） |
| `finalize` | A | 汇总完成 |
| `handle_error` | A | 错误分类 + 终止/重试决策 |

### 6.3 条件路由

| 路由函数 | 触发点 | 逻辑 |
|---------|--------|------|
| `route_after_analyze` | 需求分析后 | confidence < 0.6 → 人工审批；正常 → 规划 |
| `route_after_test` | 测试后 | 全部通过 → 审查；失败且 iter < 3 → 返工；达上限 → 错误 |
| `route_after_review` | 审查后 | passed → 安全检查；未通过且 iter < 3 → 返工 |
| `route_after_security` | 安全审查后 | requires_approval → 审批中断；安全 → 完成 |

### 6.4 Patch 应用机制（关键设计）

由于 Developer Agent 基于方案推断生成 patch（无法直接读取目标仓库源文件），diff 的上下文行和行号可能与实际文件不完全匹配。为此实现了三层兜底应用策略：

1. **git apply**：严格 unified diff 应用（上下文和行号必须精确匹配）
2. **字符串精确替换**：在目标文件中查找 `original_snippet`，替换为 `patched_snippet`
3. **函数级模糊替换**：从 patch 中提取函数名，在目标文件中定位同名字段，容忍中间的 docstring 和注释差异，替换整个函数体

### 6.5 边界控制

每个节点执行前检查：
- **取消检查**：`cancel_requested` → 跳过后续节点
- **时间超限**：`deadline_at` → 标记 failed
- **预算超限**：`budget_used_usd ≥ budget_limit_usd` → 标记 failed

### 6.6 Checkpoint 策略

| Checkpoint 类型 | 触发时机 | 恢复行为 |
|----------------|---------|---------|
| **关键节点后** | 每个 Agent 节点完成后 | 从该节点后继续 |
| **审批节点前** | 进入 `await_approval` | 等待人工决策后继续 |
| **错误发生时** | 任何异常 | 重试当前节点 |

支持 MemorySaver（开发默认）和 PostgreSQL Checkpointer（生产持久化）。

---

## 7. 工具系统

### 7.1 工具注册表

| 工具 | 权限 | 可用 Agent |
|------|------|-----------|
| `read_file` | 只读 | Planner, Developer, Reviewer |
| `list_dir` | 只读 | Requirement, Planner, Developer |
| `glob` | 只读 | Planner, Developer |
| `grep` | 只读 | Planner, Developer, Reviewer |
| `write_file` | 沙箱内写 | Developer |
| `edit_file` | 沙箱内写 | Developer |
| `sandbox_execute` | 沙箱内执行 | Developer |

### 7.2 工具权限矩阵

| 工具 | Requirement | Planner | Developer | Reviewer |
|------|:--:|:--:|:--:|:--:|
| `read_file` | | ✅ | ✅ | ✅ |
| `list_dir` | ✅ | ✅ | ✅ | |
| `grep` | | ✅ | ✅ | ✅ |
| `glob` | | ✅ | ✅ | |
| `write_file` | | | ✅ | |
| `edit_file` | | | ✅ | |
| `sandbox_execute` | | | ✅ | |

---

## 8. 沙箱与执行引擎

### 8.1 双模式设计

| 模式 | 实现 | 适用场景 |
|------|------|---------|
| **LocalSandbox**（默认） | subprocess 本地执行 | 开发测试、快速迭代 |
| **DockerSandbox**（可选） | Docker 容器隔离 | 生产部署、安全要求高 |

### 8.2 执行流程

```
1. 创建沙箱实例（按 task_id 复用）
2. git clone 目标仓库到沙箱工作区
3. 应用 Patch（三层兜底策略）
4. pip install 依赖
5. pytest --tb=short -v
6. 解析结果 → 构建 SandboxResult（含测试摘要 + 失败详情）
7. 清理沙箱资源
```

### 8.3 SandboxResult

```python
SandboxResult:
    execution_id, task_id, sandbox_type
    status: "success" | "failure" | "timeout" | "error"
    exit_code, timed_out, duration_ms
    stdout, stderr（截断保护）
    test_summary: {total, passed, failed, errors, skipped}
    test_failures: [{test_name, test_file, failure_type, message, is_new_failure}]
```

---

## 9. 前端与评测平台

### 9.1 前端页面（3 个核心页面）

```
/                    任务创建页：需求输入 + 仓库配置 + 参数调整
/tasks/:id           任务详情页：
                       · 状态图实时高亮
                       · Agent 执行时间线
                       · 代码 Diff 展示
                       · 测试结果面板
                       · Token/耗时统计卡片
                       · 审批按钮
/eval                评测对比页：
                       · 单 Agent vs 多 Agent 指标对比
                       · 成功/失败案例列表
                       · CSV 导出
```

### 9.2 评测体系

#### 消融实验设计

| 实验组 | 配置 | 对比目的 |
|--------|------|---------|
| **A: 单 Agent** | 一个 Agent 完成全部 | 多 Agent 是否有增益？ |
| **B: 多 Agent** | Requirement + Planner + Developer + Reviewer | 分工协作是否提升成功率？ |

#### 评测指标（7 项）

| 指标 | 采集方式 |
|------|---------|
| 任务成功率 | 验收条件全部满足 |
| 测试通过率 | `SandboxResult.test_summary` |
| 回归率 | 与 baseline 对比 |
| 返工率 | `iteration` 计数 |
| 平均 Token | `AgentInvocation` 汇总 |
| 平均耗时 | 任务完成时间 |
| 平均调用轮数 | `iteration` 终值 |

#### 评测任务分类（22 条）

| 类别 | 数量 | 难度 | 示例 |
|------|:--:|------|------|
| simple_fix | 5 | ⭐ | 改函数签名、修 import、加类型注解 |
| bug_fix | 5 | ⭐⭐ | 逻辑错误、边界条件、异常处理 |
| refactor | 5 | ⭐⭐⭐ | 提取函数、消除重复、简化嵌套 |
| feature | 3 | ⭐⭐⭐-⭐⭐⭐⭐ | 加新函数、重试机制、缓存装饰器 |
| edge_case | 2 | ⭐⭐-⭐⭐⭐ | 空列表处理、Unicode 文件名 |

---

## 10. 团队角色与职责

### 10.1 角色总览

```
┌─────────────────────────────────────────────────────────┐
│                    DevFlow 团队                           │
│                                                          │
│  👤 A：系统架构与 LangGraph 负责人                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 总体架构 │ StateGraph │ 条件路由 │ Checkpoint        │ │
│  │ FastAPI │ 任务管理 │ 事件流 │ 错误恢复 │ 系统集成      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  👤 B：Agent 与工具负责人                                   │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 4 Agent 实现 │ Prompt 管理 │ 结构化输出 │ 上下文裁剪    │ │
│  │ 工具系统 │ LLM 工厂 │ Agent 评测                     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  👤 C：执行环境与可靠性负责人                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 沙箱引擎 │ pytest 执行 │ Patch 应用 │ 安全策略         │ │
│  │ 资源限制 │ 容器管理 │ 结构化日志                      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  👤 D：前端与系统评测负责人                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │ React 界面 │ 状态展示 │ Diff 组件 │ 时间线组件         │ │
│  │ 评测数据集 │ 实验框架 │ 报告生成 │ 数据可视化          │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 10.2 各角色交付清单

#### A：系统架构与 LangGraph

| 交付物 | 截止 | 状态 |
|--------|:--:|:--:|
| TeamState 定义 | D1 | ✅ |
| LangGraph 完整图（11 节点 + 条件路由） | D2 | ✅ |
| FastAPI API 端点 | D2 | ✅ |
| Checkpointer 生命周期管理 | D3 | ✅ |
| 错误分类与恢复逻辑 | D4 | ✅ |
| 任务暂停/恢复/取消 | D8 | ✅ |
| 关键节点事件 push | D8 | ✅ |
| 系统架构文档 | D13 | ✅ |

#### B：Agent 与工具

| 交付物 | 截止 | 状态 |
|--------|:--:|:--:|
| AgentResult 及子模型 | D1 | ✅ |
| 工具注册表 | D1 | ✅ |
| Requirement Agent 真实调用 | D3 | ✅ |
| Planner + Developer Agent 真实调用 | D4 | ✅ |
| 上下文裁剪实现 | D4 | ✅ |
| Reviewer Agent（含安全检查） | D6 | ✅ |
| Agent 调用记录（Token/耗时/reasoning） | D5 | ✅ |
| LLM 异常处理 + 重试 | D8 | ✅ |
| 单 Agent 基线 | D9 | ✅ |
| Agent 单元测试 | D7 | ✅ |
| Agent 设计文档 | D13 | ✅ |

#### C：执行环境与可靠性

| 交付物 | 截止 | 状态 |
|--------|:--:|:--:|
| SandboxResult 模型 | D1 | ✅ |
| 沙箱原型 | D3 | ✅ |
| 完整流水线（clone → patch → install → test） | D3 | ✅ |
| 真实 pytest 执行 + 结构化返回 | D3 | ✅ |
| Patch 应用流程 | D4 | ✅ |
| 资源限制 + 清理机制 | D6 | ✅ |
| 沙箱单元测试 | D7 | ✅ |
| start.sh 一键启动 | D7 | ✅ |
| 部署 + 安全文档 | D13 | ⬜ |

#### D：前端与评测

| 交付物 | 截止 | 状态 |
|--------|:--:|:--:|
| 任务创建页面 | D2 | ⬜ |
| 任务详情页（状态 + 结果展示） | D2 | ⬜ |
| 10 条评测任务 | D2 | ✅ |
| 实时轮询进度 | D5 | ⬜ |
| 代码 Diff 展示 | D4 | ⬜ |
| 测试结果面板 | D4 | ⬜ |
| 审批面板 + 时间线组件 | D6 | ⬜ |
| 全流程 UI 打通 | D7 | ⬜ |
| 20 条评测任务终版 | D8 | ✅ |
| 评测对比页面 | D10 | ⬜ |
| 实验运行 + 数据收集 | D11 | ⬜ |
| 实验报告 + 图表 | D12 | ⬜ |
| 演示视频 | D13 | ⬜ |

---

## 11. 十四天开发计划

### 11.1 两周总览

```
Day 1 ───── 项目骨架 + 契约冻结                                    [✅ 已完成]
Day 2 ───── Mock Agent 全流程跑通                                  [✅ 已完成]
Day 3 ───── 沙箱打通 + Agent 真实 LLM 调用开始                       [✅ 已完成]
Day 4 ───── 3 个核心 Agent 完成（Req + Planner + Developer）         [✅ 已完成]
Day 5 ───── 端到端：第一次真实代码修改 + pytest 通过                  [✅ 已完成]
Day 6 ───── 条件路由（返工循环）+ Reviewer Agent                     [✅ 已完成]
Day 7 ───── 前端完善 + 第 1 周收尾                                  [🔄 进行中]
────────────────── 第一周里程碑：真实 Bug 修复 + pytest 全部通过 ──────────
Day 8 ───── 系统加固（Checkpoint + 恢复 + 错误处理）
Day 9 ───── Reviewer 完善 + 单 Agent 基线 + 多 Agent 对比
Day 10 ──── 前端终版 + 评测就绪 + 20 条任务验证
Day 11 ──── 两组实验运行 + 数据收集
Day 12 ──── 数据分析 + Bug 修复 + 报告初稿
Day 13 ──── 文档 + 演示视频
Day 14 ──── 最终测试 + 彩排 + 交付
```

### 11.2 每日详细任务

#### Day 1：项目骨架 + 契约冻结 ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | 项目结构 + FastAPI 骨架 + LangGraph 空图 + State 定义 | ✅ |
| **B** | 4 Agent Pydantic 模型 + 工具注册表 + Prompt 草稿 | ✅ |
| **C** | 沙箱环境 + 沙箱原型 + SandboxResult 模型 | ✅ |
| **D** | React 初始化 + 任务创建页 UI + 10 条评测草稿 | ✅ |
| **全员** | 冻结 `contracts/` 四个文件 | ✅ |

#### Day 2：Mock Agent 全流程跑通 ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | 全部 11 个节点 + 条件路由 + 内存 Checkpointer + API 对接 | ✅ |
| **B** | 4 Agent Mock 输出 + Agent 基类 + Prompt v2 | ✅ |
| **C** | 沙箱 clone 仓库 + pytest 执行 + Mock SandboxResult | ✅ |
| **D** | 任务详情页 + 轮询 API + 评测任务 | ✅ |

#### Day 3：沙箱打通 + Agent 真实调用 ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | Agent 节点切入真实调用 + 事件记录 + 事件 API | ✅ |
| **B** | LLM Factory + Requirement Agent 真实 LLM + 格式校验器 | ✅ |
| **C** | 完整沙箱流水线（clone → apply → install → pytest） | ✅ |
| **D** | 节点状态展示 + 15 条评测任务 | ✅ |

#### Day 4：3 个核心 Agent 完成 ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | 错误分类 + 迭代计数 + 3 Agent 集成入图 | ✅ |
| **B** | Planner + Developer Agent + 上下文裁剪 | ✅ |
| **C** | git apply 流程 + 测试失败解析 | ✅ |
| **D** | Diff 展示组件 + 测试结果组件 | — |

#### Day 5：端到端——真实代码修改 + pytest ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | 全链路调试 + 返工循环验证 + 错误处理 | ✅ |
| **B** | Developer Agent 优化 + 上下文调优 + Token 记录 | ✅ |
| **C** | 沙箱稳定性 + 多仓库兼容 | ✅ |
| **D** | 全流程 UI + 实时轮询 | — |

**★ 第一周核心里程碑已达成**：真实 DeepSeek LLM + 真实沙箱成功修复 factorial 参数校验 bug，7/7 测试通过，1 次迭代完成，成本 $0.0015。

#### Day 6：条件路由 + Reviewer Agent ✅

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | 返工循环测试 + 迭代限制 + Checkpointer 恢复测试 | ✅ |
| **B** | Reviewer Agent（含安全检查 + 测试分析）+ 单 Agent 基线 | ✅ |
| **C** | 资源限制验证 + 容器清理 + 日志脱敏 | ✅ |
| **D** | 审批面板 + 返工迭代展示 | — |

#### Day 7：第 1 周收尾 🚧

| 成员 | 任务 | 状态 |
|------|------|:--:|
| **A** | Bug 修复 + 集成联调 + API 文档 | 🔄 |
| **B** | Prompt 终版 + Agent 单元测试 + 评测框架完善 + 多 Agent 对比 | ✅ |
| **C** | 沙箱单元测试 + start.sh | ✅ |
| **D** | 详情页完善 + 评测对比骨架 | — |

**Day 7 实际成果（B 超额完成）**：
- ✅ D5 里程碑验证：真实管道端到端成功（三层 patch 兜底）
- ✅ P17b .gitignore 完善
- ✅ P18 单 Agent 基线：22/22 任务，$0.008 总成本
- ✅ P19 多 Agent 对比数据：20/20 任务，3.1x 成本 / 3.7x Token
- ✅ P22 Developer Prompt 调优（基于 D5 经验重写）
- ✅ P17a Agent 设计文档（docs/agent-design.md）
- ✅ P23 Demo 脚本（4 模式：mock / real / compare / d5）
- ✅ 测试套件：322 tests 全部通过
- ✅ 评测对比报告（eval/compare_report.py）

#### Day 8：系统加固

| 成员 | 任务 |
|------|------|
| **A** | SQLite/PostgreSQL Checkpointer + 暂停/恢复/取消完善 |
| **B** | Agent 异常处理（LLM 超时重试 + 格式错误重试） |
| **C** | 安全加固（命令白名单 + 路径校验）+ 容器清理 |
| **D** | 前端错误处理 + 状态图组件 + 20 条任务终版 |

#### Day 9：Reviewer 完善 + 基线验证

| 成员 | 任务 |
|------|------|
| **A** | 审批节点（自动通过）+ 全链路集成测试 + 统计接口 |
| **B** | 单 Agent 基线完善 + 多 Agent 对比分析 |
| **C** | 沙箱性能优化 + 监控指标收集 |
| **D** | Agent 时间线组件 + 成本/耗时卡片 + 对比页面 |

#### Day 10：前端终版 + 评测就绪

| 成员 | 任务 |
|------|------|
| **A** | 关键节点事件 push + 最终集成联调 |
| **B** | 4 Agent 最终 Prompt + 评测脚本完善 |
| **C** | 沙箱稳定性测试 + 部署文档 |
| **D** | 详情页终版 + 评测对比页 + 20 条任务验证 |

#### Day 11：两组实验运行

| 成员 | 任务 |
|------|------|
| **A** | 实验监控 + 数据收集 + Bug 修复 |
| **B** | 单 Agent 组 22 条 + 多 Agent 组 22 条 |
| **C** | 沙箱支撑 + 资源数据收集 |
| **D** | 实验进度页 + 数据入库 + 报告骨架 |

#### Day 12：数据分析 + Bug 修复

| 成员 | 任务 |
|------|------|
| **A** | 工作流效率分析 + 系统 Bug 集中修复 |
| **B** | Agent 质量分析 + Prompt 最后一轮调优 |
| **C** | 沙箱性能分析 + 部署验证 |
| **D** | 7 项指标计算 + 图表生成 + 报告初稿 |

#### Day 13：文档 + 演示视频

| 成员 | 任务 |
|------|------|
| **A** | 架构图 + 技术决策 + API 文档定稿 |
| **B** | Agent 设计文档 + 单 vs 多对比分析 |
| **C** | 安全文档 + 部署文档 + 崩溃恢复 Demo |
| **D** | 实验报告定稿 + 演示视频录制 |

#### Day 14：最终测试 + 彩排 + 交付

| 成员 | 任务 |
|------|------|
| **A** | 全系统回归测试 + GitHub 仓库整理 + 彩排 |
| **B** | Agent 测试全绿 + 个人技术贡献说明 |
| **C** | 沙箱测试全绿 + 部署验证 |
| **D** | 前端最终检查 + 数据验证 |
| **全员** | 最终彩排 + 交付检查清单全部打勾 |

---

## 12. 协作规则与工程规范

### 12.1 接口契约规则

```
contracts/ 模块 — 项目宪法

修改规则：
  ✗ 任何修改须经四人共同评审
  ✗ 不允许单方面修改字段类型或删除字段
  ✓ PR 标题格式：[CONTRACT] 变更说明
  ✓ P0 冻结后两周内最多修改 1 次
```

### 12.2 分支与代码评审

```
main — 始终可运行
  ├── feature/a-*    A 的所有功能分支
  ├── feature/b-*    B 的所有功能分支
  ├── feature/c-*    C 的所有功能分支
  └── feature/d-*    D 的所有功能分支

规则：
  ✓ PR 须至少一人评审（交叉评审）
  ✓ PR 须通过 pytest + ruff
  ✓ 每天合并前确保 main 可运行
  ✗ 禁止四人同时编辑同一文件
  ✗ 禁止直接 push 到 main
```

### 12.3 工程规范

```yaml
python: "3.11+"
linter: ruff (零容忍)
test: pytest (异步 + 同步)
commit: "{type}({scope}): {desc}"     # 例: feat(agent): Requirement Agent 完成
tag: "v{major}.{minor}.{patch}-d{day}" # 例: v0.1.0-d5
```

### 12.4 沟通规则

- **每日站会**（9:00，15min）：昨天 + 今天 + 阻塞
- **每日收工会**（21:00，10min）：进度同步 + 风险预警
- **contracts 修改**：先开 Issue → 讨论 → PR
- **阻塞立即说**：不自己闷头超过 2 小时

---

## 13. 风险管理与降级方案

### 13.1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:--:|:--:|------|
| LLM API 不稳定 | 高 | 中 | 3 次重试 + 指数退避 + Fallback 降级到 Mock |
| D5 端到端不通 | 中 | **高** | 三层 patch 应用兜底 + 缩小难度 |
| Agent 输出格式错误 | 高 | 中 | JSON 自动修复 + 最多 3 次格式重试 |
| 评测数据量不够 | 中 | 中 | 保证每组 ≥ 15 条有数据 |
| Token 费用超预算 | 低 | 低 | 全程用 DeepSeek（最便宜模型） |

### 13.2 降级方案

| 触发条件 | 降级方案 |
|---------|---------|
| Patch 无法应用 | 三层兜底：git apply → 字符串替换 → 函数级模糊替换 |
| Reviewer 误报率太高 | 简化安全审查，只保留 SQL 注入 + 硬编码密钥 |
| D11 实验来不及跑完 | 优先跑 15 条代表性任务 |
| 某个 Agent 效果极差 | 简化 Prompt，减少职责范围 |

---

## 14. 成功标准与验收条件

### 14.1 每日硬性验收

| 天数 | 验收条件 | 判定 |
|------|---------|:--:|
| **D1** | 4 个契约文件进入仓库 + 四人签字 | ✅ |
| **D2** | Mock Agent 全流程走通 | ✅ |
| **D3** | 沙箱真实执行 pytest 返回 SandboxResult | ✅ |
| **D4** | 3 Agent 结构化输出成功率 ≥ 80% | ✅ |
| **D5** | **真实 Bug 修复 + pytest 全部通过** | ✅ |
| **D6** | 返工循环生效 + Reviewer 产出审查意见 | ✅ |
| **D7** | 单 Agent 基线 + 多 Agent 对比 + 评测框架完整 | ✅ |
| **D8** | 系统加固 + 恢复测试 | — |
| **D10** | 前端终版 + 22 条任务 + 一键启动 | — |
| **D12** | 实验数据齐全 + 图表生成 | — |
| **D14** | 全部交付物 ready | — |

### 14.2 最终成功标准

```
功能性：
  ✅ 提交需求 → 自动代码修改 → pytest 通过
  ✅ 测试失败自动返工（≤3 次）
  ⬜ 服务重启后任务从 Checkpoint 恢复
  ✅ 高风险安全问题记录日志并标记

质量：
  ⬜ 多 Agent 成功率 > 单 Agent 基线（真实沙箱下）
  ✅ 无无限循环或资源泄漏

工程：
  ⬜ bash start.sh 一键启动全栈
  ✅ ruff 零报错 + pytest 全绿（322 tests）
  ✅ 22 条评测任务可复现
```

---

## 15. 最终交付清单

### 15.1 代码

| 交付物 | 负责人 | 状态 |
|--------|:--:|:--:|
| `contracts/` — 4 个核心契约 | 全员 | ✅ |
| `app/graph.py` — LangGraph 完整工作流（双图） | A | ✅ |
| `app/api/tasks.py` — 8 个 API 端点 | A | ✅ |
| `app/agents/` — 5 Agent + 基类 | B | ✅ |
| `app/tools/registry.py` — 7 工具注册 | B | ✅ |
| `app/llm/factory.py` — 多 Provider 支持 | B | ✅ |
| `app/sandbox/` — 双模式沙箱引擎 | C | ✅ |
| `frontend/` — React 管理界面（3 页面） | D | ⬜ |
| `eval/` — 评测框架（22 任务 + 运行器） | B | ✅ |
| `tests/` — 322 单元测试 | 全员 | ✅ |
| `start.sh` — 一键启动脚本 | C | ✅ |
| `demo.py` — 4 模式 Demo 脚本 | B | ✅ |

### 15.2 文档

| 交付物 | 负责人 | 状态 |
|--------|:--:|:--:|
| 项目蓝图（本文档） | 全员 | ✅ |
| `README.md` | A | ✅ |
| `docs/architecture.md` | A | ✅ |
| `docs/api.md` | A | ⬜ |
| `docs/agent-design.md` | B | ✅ |
| `docs/deploy.md` | C | ⬜ |
| `docs/eval-report.md` | D | ⬜ |
| 个人技术贡献说明（4 份） | 每人 | ⬜ |

### 15.3 演示

| 交付物 | 说明 | 状态 |
|--------|------|:--:|
| Demo 脚本 | 4 模式：mock / real / compare / d5 | ✅ |
| 演示视频 | 提交需求 → 全流程 → 结果 → 评测对比 | ⬜ |

---

> **文档维护**：本文档为 DevFlow 两周冲刺版的权威方案文档。P0 阶段由全员共同确认。每日站会后 A 更新进度状态。
>
> **版本历史**：
> - v1.0（2026-07-22）：初版，六周完整版
> - v2.0（2026-07-22）：六周最终版，合并团队讨论
> - v3.0（2026-07-22）：两周冲刺版，范围裁剪，聚焦核心交付
> - v4.0（2026-07-28）：两周冲刺终版，更新 Day 1-7 实际完成状态，移除六周对比内容
