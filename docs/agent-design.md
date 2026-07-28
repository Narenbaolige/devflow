# DevFlow Agent Design

> 基于 LangGraph 的多 Agent 协作软件工程平台 — Agent 架构设计与设计决策文档
>
> 最后更新：2026-07-28

---

## 1. 架构概述

DevFlow 使用 LangGraph StateGraph 编排多个专业化 Agent，完成从需求分析到代码修复的完整软件工程任务。

### 1.1 两种工作模式

| 模式 | 图结构 | 适用场景 |
|------|--------|---------|
| **多 Agent 管道** | init → Requirement → Planner → Developer → Sandbox → Reviewer → Security → done | 复杂 Bug 修复，需要测试验证 + 迭代返工 |
| **单 Agent 基线** | init → SingleAgent → done | 简单任务、消融实验基线 |

### 1.2 核心组件

```
app/
  agents/
    base.py          — AgentBase 抽象基类（Mock 开关、LLM 调用、成本追踪）
    requirement.py   — 需求分析 Agent
    planner.py       — 方案规划 Agent
    developer.py     — 代码开发 Agent
    reviewer.py      — 代码审查 Agent
    single_agent.py  — 单 Agent 基线（全流程合并）
    validator.py     — 结构化输出校验器（JSON 提取 + Pydantic 验证）
  graph.py           — LangGraph 工作流定义 + 条件路由
  sandbox/
    local.py         — 本地沙箱（subprocess 执行）
    base.py          — 沙箱抽象接口
  tools/
    sandbox_ops.py   — 沙箱实例注册表（按 task_id 复用）
    registry.py      — 工具注册中心
contracts/
  state.py           — TeamState 全局状态定义
  agent_result.py    — 各 Agent 的结构化输出模型
eval/
  agent_quality.py   — 多维度质量评测器（8 维度）
  runner.py          — 多 Agent 管道评测运行器
  single_agent_runner.py — 单 Agent 评测运行器
  tasks/tasks_20.py  — 20 条评测任务数据集
```

---

## 2. Agent 设计

### 2.1 设计原则

1. **单一职责**：每个 Agent 只负责一个阶段（分析/规划/开发/审查），上下文最小化
2. **结构化输出**：所有 Agent 输出通过 Pydantic 模型校验，确保下游可消费
3. **统一包装**：AgentResult 统一包装所有 Agent 输出，附加调用元信息（token、成本、耗时）
4. **优雅降级**：LLM 调用失败时自动降级为 Mock 输出，流程不中断
5. **协作式取消**：每个节点边界检查 `cancel_requested`，支持任务取消

### 2.2 AgentBase 基类

```python
class AgentBase(ABC):
    USE_MOCK: bool                    # 环境变量 DEVFLOW_USE_MOCK 控制
    FALLBACK_TO_MOCK_ON_ERROR: bool   # LLM 失败时降级
    max_context_tokens: int = 2000    # 上下文 Token 预算

    # 抽象方法（每个 Agent 必须实现）
    role: AgentRole                   # Agent 角色枚举
    _load_system_prompt() -> str      # 加载 System Prompt
    output_schema -> Type[BaseModel]  # Pydantic 输出模型
    build_context(state) -> str       # 从 TeamState 提取上下文
    mock_result(state) -> AgentResult # Mock 输出
```

**调用流程**：
```
invoke(state)
  ├─ USE_MOCK? → mock_result(state)
  └─ else:
       ├─ build_context → clip_context (token 预算)
       ├─ llm.invoke([system, context, schema_instruction])
       ├─ validate_against_model (最多 3 次格式修复重试)
       ├─ 成功 → AgentResult(success=True, invocation=...)
       └─ 失败 → FALLBACK? mock_result : AgentResult(success=False)
```

### 2.3 各 Agent 角色

| Agent | 角色 | 输出模型 | System Prompt | 上下文来源 |
|-------|------|---------|---------------|-----------|
| Requirement | 需求分析 | RequirementResult | requirement_agent.md | task_meta.requirement |
| Planner | 方案规划 | PlanResult | planner_agent.md | requirement_analysis |
| Developer | 代码生成 | PatchResult | developer_agent.md | task_meta + plan + review feedback |
| Reviewer | 代码审查 | ReviewResult | reviewer_agent.md | patches + sandbox_results |
| SingleAgent | 全流程 | SingleAgentResult | single_agent.md | task_meta |

### 2.4 agent_node 统一包装器

```python
async def agent_node(state, agent) -> TeamState:
    # 1. 取消检查（调用前）
    # 2. asyncio.to_thread(agent.invoke, state)  # 非阻塞 LLM 调用
    # 3. 取消检查（调用后）
    # 4. 记录 budget_used_usd（成本累积）
    # 5. 记录 agent_complete / agent_fallback 事件
    # 6. 按 role 路由到 state 对应字段
```

**字段映射**：
- `REQUIREMENT` → `state["requirement_analysis"]`
- `PLANNER` → `state["plan"]`
- `DEVELOPER` → `state["patches"]` （特殊处理：直接存 result 便于 reducer 合并）
- `REVIEWER` → `state["review"]`
- `SECURITY` → `state["security_review"]`

---

## 3. 图结构与路由

### 3.1 多 Agent 管道图

```
init_task
  └→ analyze_requirement
       ├→ [confidence < 0.6]      await_approval (interrupt)
       ├→ [failed]                handle_error → END
       └→ [normal]                plan_solution
                                    └→ develop_changes (iteration++)
                                         └→ apply_patches (sandbox: clone + git apply)
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

### 3.2 单 Agent 图

```
init_task → run_single_agent → finalize → END
```

### 3.3 条件路由函数

| 函数 | 触发点 | 逻辑 |
|------|--------|------|
| `route_after_analyze` | 需求分析后 | confidence < 0.6 → 人工审批；phase=failed → 错误 |
| `route_after_test` | 测试后 | 全部通过 → 审查；失败且可重试 → 返工；达上限 → 错误 |
| `route_after_review` | 审查后 | passed → 安全检查；未通过且可重试 → 返工 |
| `route_after_security` | 安全审查后 | requires_approval → 审批中断；安全 → 完成 |

### 3.4 边界控制

每个节点执行前都会通过 `_blocked()` 检查：
1. **取消检查** (`_cancelled`)：`cancel_requested=True` → 停止
2. **资源限制** (`_limits_exceeded`)：
   - `deadline_at`：任务总超时
   - `budget_limit_usd`：LLM 费用上限

---

## 4. Patch 应用设计（D5 关键突破）

### 4.1 问题

Developer Agent 无法读取目标仓库的实际源文件。它基于 Planner 的方案描述生成 patch，导致：
- diff 行号与实际文件不匹配
- 上下文行（hunk 头部）错误
- `git apply` 失败

### 4.2 三层兜底方案

在 `apply_patches` 节点中实现：

```
Phase A: git apply
  └→ 成功 → done

Phase B: 字符串精确替换
  └→ original_snippet in file → replace → done

Phase C: 函数级模糊替换
  └→ 提取函数名 → 在目标文件中定位 → 替换整个函数体
  └→ 容忍中间有 docstring、注释等差异
```

**Phase C 实现细节**：
1. 从 `original_snippet` 提取第一个 `def`/`class` 的函数名
2. 在目标文件中用正则匹配同名函数定义
3. 定位函数边界（下一个同级 `def`/`class` 或 EOF）
4. 用 `patched_snippet` 替换整个函数体

### 4.3 file_path 规范化

Agent 可能返回绝对路径（如 `D:/Dev/devflow-test-repo/math_utils.py`）。在应用前规范化：
```python
file_path = file_path.rsplit(sep, 1)[-1]  # 仅保留文件名
```

---

## 5. 评测框架

### 5.1 评测任务

`eval/tasks/tasks_20.py` — 20 条任务，覆盖 5 类别 × 4 难度：

| 类别 | 数量 | 难度 | 示例 |
|------|------|------|------|
| simple_fix | 5 | 1 | 添加参数校验、修复 import、加 docstring |
| bug_fix | 5 | 2 | 除零保护、off-by-one、属性 setter 修复 |
| refactor | 5 | 3 | 提取公共函数、early return、常量提取 |
| feature | 3 | 3-4 | 添加方法、重试机制、缓存装饰器 |
| edge_case | 2 | 2-3 | 空列表处理、Unicode 文件名 |

### 5.2 质量指标（8 维度）

| 维度 | 指标 | 来源 |
|------|------|------|
| 结构化输出 | `structured_output_valid`, `output_completeness` | Agent 输出的 Pydantic 模型 |
| 开发质量 | `patch_count`, `patch_applicable`, `diff_lines` | Developer 的 patches |
| 测试结果 | `tests_total/passed/failed`, `tests_pass_rate` | sandbox_results |
| 迭代效率 | `iteration_count`, `first_attempt_success` | state.iteration |
| 审查结果 | `review_passed`, `review_risk_level`, `review_issue_count` | Reviewer 输出 |
| Token/成本 | `total_input/output_tokens`, `total_cost_usd` | agent_complete events |
| 耗时 | `total_duration_ms` | agent_complete events |
| 最终状态 | `phase`, `success` | state.phase |

### 5.3 评测结果（2026-07-28）

| 指标 | 多 Agent 管道 | SingleAgent | 比率 |
|------|-------------|-------------|------|
| 成功率 | 20/20 (100%) | 20/20 (100%) | — |
| 平均成本 | $0.001306 | $0.000416 | 3.1x |
| 平均耗时 | 18.5s | 8.1s | 2.3x |
| 总 Token | 158,500 | 42,605 | 3.7x |
| Agent 调用数 | 4/任务 | 1/任务 | 4x |

**结论**：在 Mock 沙箱下（无真实测试反馈），两者输出质量无差异。多 Agent 管道的价值在真实沙箱反馈循环中体现。

---

## 6. 设计决策记录

### 6.1 为什么用 4 个 Agent 而不是 1 个

**决策**：采用专业化分工的 4-Agent 管道。

**理由**：
- **上下文隔离**：每个 Agent 只看到完成任务所需的最小信息，减少注意力分散
- **可观测性**：每个阶段独立记录事件、成本、耗时，便于调试和优化
- **独立迭代**：可单独优化某个 Agent 的 Prompt 而无需改动其他
- **安全性**：Reviewer → Security 的双层审查机制

**代价**：3-4x Token/成本开销。对于简单任务，SingleAgent 更高效。

### 6.2 为什么 Agent 不能直接读文件

**决策**：当前 Developer Agent 不提供文件读取工具。

**理由**：
- 工具调用增加 LLM 往返次数（tool calling 需要多轮对话）
- DeepSeek 的结构化输出与工具调用兼容性待验证
- 沙箱集成（文件读取需通过沙箱）增加复杂度

**补偿措施**：三层 patch 应用兜底（见 §4）。

**未来方向**：为 Developer Agent 添加 `sandbox_execute` 工具，使其能在沙箱中读取文件后再生成 patch。

### 6.3 Mock 双层开关设计

**决策**：Agent Mock 和 Sandbox Mock 独立控制。

```bash
DEVFLOW_USE_MOCK=true      # Agent 用 Mock（默认）
DEVFLOW_USE_SANDBOX=true   # Sandbox 用 Mock（默认跟随 DEVFLOW_USE_MOCK）
```

**理由**：
- 开发期快速迭代（全 Mock，秒级完成）
- 可单独测试 Agent 输出质量（Agent 真实 + Sandbox Mock）
- 可单独测试 Sandbox 集成（Agent Mock + Sandbox 真实）
- 生产模式（全部真实）

### 6.4 为什么用 LocalSandbox 而不是 Docker

**决策**：默认使用 LocalSandbox（subprocess），Docker 作为可选项。

**理由**：
- **零依赖**：不需要 Docker Desktop，减少环境配置负担
- **调试友好**：临时目录可直接查看，错误信息直接返回
- **性能**：subprocess 启动远快于容器创建
- **Windows 兼容**：`shell=True` 使用系统原生 shell

**安全考量**：Docker 隔离是后续安全加固的方向。当前阶段以功能验证为主。

---

## 7. 已知限制

1. **Developer Agent 无文件读取能力**：patch 基于推断生成，可能与应用目标不完全匹配
2. **无多文件依赖分析**：每个 patch 独立应用，不处理跨文件重构
3. **仅支持 Git 仓库**：`apply_patches` 硬编码 `git clone` 流程
4. **测试解析仅支持 pytest**：`run_tests` 只解析 pytest 输出格式
5. **Reviewer 审查无代码上下文**：Reviewer 只看到 patches 和测试结果，看不到完整代码
6. **SingleAgent 无 rework 机制**：单 Agent 不会收到测试反馈进行迭代

---

## 8. 文件索引

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/agents/base.py` | 392 | AgentBase + agent_node 统一包装器 |
| `app/graph.py` | 797 | LangGraph 工作流（多 Agent + 单 Agent） |
| `contracts/state.py` | 160 | TeamState 定义 + create_initial_state |
| `contracts/agent_result.py` | 231 | 5 个 Agent 的结构化输出模型 |
| `app/agents/validator.py` | 254 | JSON 提取 + Pydantic 校验 + 重试 |
| `app/sandbox/local.py` | 116 | LocalSandbox 实现 |
| `app/tools/sandbox_ops.py` | 96 | 沙箱注册表 + sandbox_execute 工具函数 |
| `app/llm/factory.py` | 78 | LLM 工厂（OpenAI/DeepSeek/ChatAnywhere） |
| `app/config.py` | 84 | 全局配置（Settings dataclass） |
| `eval/agent_quality.py` | 270 | 8 维度质量评测器 |
| `eval/runner.py` | 245 | 多 Agent 管道评测运行器 |
| `eval/single_agent_runner.py` | 207 | 单 Agent 评测运行器 |
| `eval/tasks/tasks_20.py` | 272 | 20 条评测任务数据集 |
| `prompts/developer_agent.md` | — | Developer Agent System Prompt |
| `prompts/single_agent.md` | — | SingleAgent System Prompt |
| `docs/architecture.md` | — | 系统架构文档 |
| `docs/DevFlow-Project-Blueprint.md` | — | 项目蓝图 |
| `docs/DevFlow-2Week-Sprint.md` | — | 2 周 Sprint 计划 |
