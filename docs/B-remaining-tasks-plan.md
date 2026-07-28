# B 剩余任务执行方案

> 日期：2026-07-28 | 不含 D 的前端任务 | 5 项任务，预计 6.5h

---

## 任务总览

| # | 任务 | 预计 | 产出物 | 优先级 |
|:--:|------|:--:|------|:--:|
| 1 | 真实沙箱对比实验 | 1h | `eval/real_sandbox_compare.py` + CSV | 🔴 |
| 2 | Agent 工具调用集成 | 3h | `app/agents/base.py` + `developer.py` + `tool_impls.py` | 🔴 |
| 3 | 失败案例深度分析 | 1h | 分析笔记 → 写入 eval-report | 🟡 |
| 4 | docs/eval-report.md | 1h | `docs/eval-report.md` | 🟡 |
| 5 | 个人技术贡献说明 | 0.5h | `docs/contribution-b.md` | 🟡 |

---

## 任务 1：真实沙箱对比实验

### 目标

在真实沙箱（LocalSandbox）下跑单 Agent vs 多 Agent 对比，获取**真实通过率 + 返工效率**数据，为答辩提供"多 Agent > 单 Agent"的量化证据。

### 为什么 Mock 数据不够

当前对比数据来自 Mock 沙箱（始终返回 10/10 通过），无法触发多 Agent 管道的返工循环。只有在真实沙箱中实际运行 pytest，才能体现 Reviewer 审查 → Developer 返工的价值。

### 实验设计

```
任务选择：从 22 条中选 10 条（覆盖全部 5 类别 × 4 难度）

  simple_fix:  task-001 (参数校验)
  simple_fix:  task-011 (docstring)
  bug_fix:     task-003 (除零保护)
  bug_fix:     task-014 (binary_search off-by-one)
  refactor:    task-006 (提取校验函数)
  refactor:    task-017 (简化嵌套 if)
  feature:     task-008 (power 方法)
  feature:     task-019 (重试机制)
  edge_case:   task-021 (空列表)
  edge_case:   task-022 (Unicode 文件名)

每组对比：
  单 Agent 组：build_single_agent_graph() → 生成 patch → 真实沙箱 apply+test
  多 Agent 组：build_graph() → 完整管道 → 真实沙箱 apply+test+返工
```

### 需要准备的测试仓库

当前 `D:\Dev\devflow-test-repo` 只有 math_utils.py + test_math_utils.py（1 个 bug）。需要扩展到覆盖以上 10 条任务所需的文件。

**方案**：不创建 10 个不同仓库。创建一个统一的测试仓库，包含所有需要的模块：

```
devflow-test-repo/
├── math_utils.py          # factorial (bug: 缺参数校验) + fibonacci
├── test_math_utils.py
├── calculator.py          # 缺 power 方法 → task-008
├── test_calculator.py
├── item_processor.py      # process_items 空列表 bug → task-021
├── test_item_processor.py
├── search.py              # binary_search off-by-one → task-014
├── test_search.py
├── config_loader.py       # parse_config 文件不存在 → task-005
├── test_config_loader.py
├── user_service.py        # 提取校验函数 → task-006
├── validators.py          # (待创建)
├── test_user_service.py
└── file_handler.py        # Unicode 文件名 → task-022
    test_file_handler.py
```

写一个 `setup_test_repo.py` 脚本，一键生成这个仓库。

### 评测脚本

写 `eval/real_sandbox_compare.py`：

```python
"""
真实沙箱对比评测。
用法：python -m eval.real_sandbox_compare --tasks 10 --output real_compare.csv
"""

class RealSandboxComparator:
    def __init__(self, repo_url, tasks):
        self.repo_url = repo_url
        self.tasks = tasks
        self.results = []

    async def run(self):
        for task in self.tasks:
            # ── Single Agent ──
            sa_result = await self._run_single_agent(task)
            
            # ── Multi Agent ──
            ma_result = await self._run_multi_agent(task)
            
            self.results.append({
                "task_id": task["id"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                # Single Agent
                "sa_success": sa_result.test_passed,
                "sa_iterations": 1,
                "sa_cost": sa_result.cost,
                "sa_time": sa_result.time,
                # Multi Agent
                "ma_success": ma_result.test_passed,
                "ma_iterations": ma_result.iterations,
                "ma_cost": ma_result.cost,
                "ma_time": ma_result.time,
                # 增益
                "ma_better": ma_result.test_passed and not sa_result.test_passed,
                "rework_saved": ma_result.iterations > 1 and ma_result.test_passed,
            })
        
        return self.results
```

### 预期输出

```
Task          SingleAgent    MultiAgent     增益
─────────────────────────────────────────────────
task-001      ✅ 7/7          ✅ 7/7 (iter=1) —
task-011      ✅ 加入 doc     ✅ (iter=1)     —
task-003      ❌ patch 失败   ✅ (iter=2)     🔥 返工修正
task-014      ❌ 逻辑错       ❌ (iter=3)     —
task-006      ✅              ✅ (iter=1)     —
task-017      ❌ 缩进问题     ✅ (iter=2)     🔥 返工修正
...

总结：SingleAgent 6/10 (60%)，MultiAgent 9/10 (90%)
     多 Agent 返工循环修正了 3 个首次失败的 patch
```

---

## 任务 2：Agent 工具调用集成

### 目标

让 Developer Agent 能在沙箱中**实际执行命令**（读文件、搜索代码、跑测试）后再生成 patch，而不是纯粹从 Prompt 推断。这是 Agent 层最重要的架构升级。

### 当前问题

```
蓝图描述：                        当前实现：
Agent 用 read_file 读源码   →   Prompt 中描述 repo_url，Agent 猜代码结构
Agent 用 grep 搜索项目      →   不调用任何工具
Agent 先跑 pytest 看基线    →   graph.py 节点代为执行
```

后果：Developer 生成的 diff 行号与实际文件不匹配，需要三层兜底才能 apply。

### 实现方案

#### 2.1 工具可执行化

当前 `registry.py` 只定义了工具的**元数据**（名称、权限、可用 Agent），没有可调用的**执行函数**。需要给每个工具绑定实际执行逻辑。

新增 `app/tools/tool_impls.py`（工具的具体实现）：

```python
"""工具的实际执行函数。Agent 通过 tool-calling 调用。"""

from app.tools.sandbox_ops import sandbox_execute as _sandbox_exec

def tool_read_file(file_path: str, task_id: str = "default") -> str:
    """读取沙箱中的文件内容。"""
    return _sandbox_exec(f"cat {file_path}", task_id=task_id).data

def tool_list_dir(path: str = ".", task_id: str = "default") -> str:
    """列出目录。"""
    return _sandbox_exec(f"ls -la {path}", task_id=task_id).data

def tool_grep(pattern: str, path: str = ".", task_id: str = "default") -> str:
    """在代码中搜索模式。"""
    return _sandbox_exec(f"grep -rn '{pattern}' {path}", task_id=task_id).data

def tool_sandbox_execute(command: str, cwd: str = "/workspace",
                         timeout: int = 60, task_id: str = "default") -> str:
    """通用沙箱命令执行。"""
    return _sandbox_exec(command, cwd=cwd, timeout=timeout, task_id=task_id).data

# 工具注册表 → 执行函数映射
TOOL_IMPL_MAP = {
    "read_file": tool_read_file,
    "list_dir": tool_list_dir,
    "grep": tool_grep,
    "sandbox_execute": tool_sandbox_execute,
}
```

#### 2.2 AgentBase 改造

在 `app/agents/base.py` 中新增 tool-calling 分支：

```python
class AgentBase(ABC):
    # 新增：是否启用工具调用（默认关闭，Developer 覆盖为 True）
    ENABLE_TOOL_CALLING: bool = False
    MAX_TOOL_ROUNDS: int = 5

    def invoke(self, state, llm=None) -> AgentResult:
        if self.USE_MOCK:
            return self.mock_result(state)

        if llm is None:
            llm = get_llm()

        # ── Tool-calling 路径 ──
        if self.ENABLE_TOOL_CALLING:
            return self._invoke_with_tools(state, llm)

        # ── 纯 Prompt 路径（当前行为，其他 Agent 不变）──
        return self._invoke_prompt_only(state, llm)

    def _invoke_with_tools(self, state, llm) -> AgentResult:
        """带工具调用的 Agent 执行。"""
        from app.tools.registry import get_tools_for_agent
        from app.tools.tool_impls import TOOL_IMPL_MAP

        tools = get_tools_for_agent(self.role.value)
        if not tools:
            return self._invoke_prompt_only(state, llm)

        # 构建消息
        context = self._clip_context(self.build_context(state))
        task_id = state.get("task_meta", {}).get("task_id", "default")

        # 工具定义（OpenAI function-calling 格式）
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters or {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
            for t in tools
        ]

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context},
        ]

        for round_num in range(self.MAX_TOOL_ROUNDS):
            response = llm.invoke(messages, tools=tool_defs)

            # 检查是否有 tool_calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # 没有工具调用 → 应该是最终输出
                return self._parse_response(response)

            # 执行工具并追加结果
            for tc in tool_calls:
                func_name = tc.get("name", "")
                func_args = tc.get("arguments", {})
                impl = TOOL_IMPL_MAP.get(func_name)

                if impl:
                    try:
                        result = impl(task_id=task_id, **func_args)
                    except Exception as e:
                        result = f"[工具执行失败] {e}"
                else:
                    result = f"[未知工具] {func_name}"

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": str(result)[:4000],  # 截断保护
                })

        # 超过最大轮次，要求 LLM 强制输出
        messages.append({
            "role": "user",
            "content": "已达到最大工具调用轮次。请基于已获取的信息，输出最终 JSON 结果。",
        })
        response = llm.invoke(messages)
        return self._parse_response(response)

    def _invoke_prompt_only(self, state, llm) -> AgentResult:
        """纯 Prompt 路径（当前行为，重构自现有 invoke 方法）。"""
        # ... 现有的 LLM 调用 + 校验 + 重试逻辑 ...

    def _parse_response(self, response) -> AgentResult:
        """从 LLM 响应中提取并校验结构化输出。"""
        raw_text = response.content if hasattr(response, "content") else str(response)
        from app.agents.validator import validate_against_model
        result = validate_against_model(raw_text, self.output_schema)
        return AgentResult(
            agent_role=self.role,
            success=True,
            result=result.model_dump(),
            invocation=AgentInvocation(
                agent_role=self.role,
                model=getattr(response, "model", "unknown"),
            ),
            reasoning=f"{self.role.value} Agent 调用完成",
        )
```

#### 2.3 Developer Agent 覆盖

```python
class DeveloperAgent(AgentBase):
    ENABLE_TOOL_CALLING = True  # 🆕 开启工具调用

    def _load_system_prompt(self) -> str:
        base = (PROMPTS_DIR / "developer_agent.md").read_text("utf-8")
        # 追加工具使用说明
        return base + "\n\n" + (PROMPTS_DIR / "developer_tools.md").read_text("utf-8")
```

#### 2.4 新增 Prompt：`prompts/developer_tools.md`

```markdown
## 可用工具

你可以在沙箱中执行以下操作来了解目标代码：

1. **sandbox_execute(command, cwd, timeout)**
   - `cat <file>` — 读取文件内容
   - `ls -la` — 列出目录
   - `python -m pytest -v --tb=short` — 运行测试看基线
   - `grep -rn '<pattern>' .` — 搜索代码

2. **工具使用策略**
   - 生成 patch 之前，**先读取目标文件**了解当前代码
   - 如果 Planner 指定的文件路径不确定，先用 ls 探索目录结构
   - 可选：先跑一遍 pytest，确认哪些测试本来就会失败
   - 修改代码后不需要再跑测试（由管道自动执行）

3. **约束**
   - 每次工具调用计入上下文，最多 5 轮
   - 最终必须输出符合 JSON Schema 的 patch 对象
   - 读取文件后，original_snippet 必须是文件中复制出来的真实代码
```

#### 2.5 改动文件清单

| 文件 | 改动 | 行数 |
|------|------|:--:|
| `app/agents/base.py` | +`ENABLE_TOOL_CALLING`、`_invoke_with_tools()`、`_parse_response()`，重构现有 invoke | +80 |
| `app/agents/developer.py` | +`ENABLE_TOOL_CALLING = True` | +1 |
| `app/tools/tool_impls.py` | **新建**，4 个工具执行函数 + TOOL_IMPL_MAP | +60 |
| `prompts/developer_tools.md` | **新建**，工具使用说明 | +25 |
| `prompts/developer_agent.md` | 微调（`_load_system_prompt` 改为动态拼接） | 无需改 |

**向后兼容**：`ENABLE_TOOL_CALLING` 默认 `False`，Requirement/Planner/Reviewer/SingleAgent 完全不受影响。

#### 2.6 验证方式

用 D5 相同的 factorial bug，对比改进前后：

```
改进前：
  Developer 生成 patch（行号 @@ -1,4 +1,8 @@）
  → git apply 失败（行号不匹配）
  → 字符串替换失败（original_snippet 不含 docstring）
  → 函数级模糊替换成功（按函数名定位）

改进后：
  Developer 先 sandbox_execute("cat math_utils.py") 读取文件
  → 看到真实代码结构和行号
  → 生成 patch（行号 @@ -6,5 +6,9 @@）
  → git apply 第一次就成功 ✅
```

---

## 任务 3：失败案例深度分析

### 目标

从 22 条评测中抽查 Agent 生成的实际输出质量，区分"格式正确"和"逻辑正确"。

### 方法

1. 从 `multi-agent-real-20.csv`（已有）提取每个任务的 patch diff
2. 按类别各抽 1-2 条：`simple_fix ×2 + bug_fix ×2 + refactor ×2 + feature ×1 + edge_case ×1 = 8 条`
3. 人工判断：

```
每条任务检查：
  [ ] diff 语法是否正确？（unified diff 格式有效？）
  [ ] 修改位置是否在正确的文件中？
  [ ] 逻辑是否解决了需求描述的问题？
  [ ] 是否引入了明显的副作用？
  [ ] original_snippet 与典型代码模式的差距？

评级：
  A — 语法正确 + 逻辑正确 + 可直接 apply
  B — 语法正确 + 逻辑基本正确 + 需微调
  C — 语法问题 / 逻辑错误 / 完全不可用
```

### 输出

一份简短分析表，写入 `docs/eval-report.md` 的"典型案例分析"章节。

---

## 任务 4：docs/eval-report.md

### 内容框架

```markdown
# DevFlow 评测报告

> 日期：2026-07-28 | 基于 22 条评测任务

## 1. 实验设计
- 22 条任务，5 类别（simple_fix/bug_fix/refactor/feature/edge_case）× 4 难度
- 两组对比：单 Agent 基线 vs 多 Agent 管道
- 评测指标：成功率、首次通过率、迭代次数、Token 消耗、成本

## 2. Mock 沙箱结果
| 指标 | SingleAgent | MultiAgent | 比率 |
|------|:----------:|:----------:|:----:|
| 成功率 | 22/22 | 20/20 | — |
| 平均成本 | $0.000416 | $0.001306 | 3.1x |
| 平均耗时 | 8.1s | 18.5s | 2.3x |
| 总 Token | 42,605 | 158,500 | 3.7x |

结论：Mock 模式下两者无质量差异。多 Agent 成本是单 Agent 的 3 倍。

## 3. 真实沙箱结果 ← 填入任务①的数据
[任务①的对比表格 + 分析]

## 4. 案例深度分析 ← 填入任务③的分析
### 4.1 成功案例
### 4.2 失败案例
### 4.3 多 Agent 返工修正案例

## 5. D5 里程碑验证
- 任务：修复 factorial 参数校验 bug
- 结果：phase=done, 7/7 tests, 1 次迭代, $0.0015
- 关键突破：三层 patch 兜底 → OK_FUNCTION 模糊替换

## 6. 结论与建议
- 简单任务用 SingleAgent（成本低 3x）
- 复杂 Bug 用多 Agent（返工循环提供安全网）
- 下一步：Agent 工具调用集成可提升首次通过率
```

---

## 任务 5：个人技术贡献说明

### 格式

```markdown
# 个人技术贡献说明 — B

## 基本信息
- 姓名：[B 的真实姓名]
- 角色：Agent 与工具负责人
- 项目：DevFlow — 基于 LangGraph 的多 Agent 协同软件工程平台

## 负责模块与量化成果
| 模块 | 文件 | 代码量 |
|------|------|:--:|
| Agent 体系 | app/agents/ (8 文件) | ~1,500 行 |
| 工具系统 | app/tools/ (4 文件) | ~400 行 |
| LLM 集成 | app/llm/factory.py + app/metrics.py | ~200 行 |
| 评测框架 | eval/ (5 文件) | ~800 行 |
| Prompt 工程 | prompts/ (6 文件) | ~460 行 |
| 测试 | tests/agents/ + tests/tools/ (10 文件) | ~1,200 行 |
| 文档 | docs/agent-design.md | ~340 行 |
| Demo | demo.py | ~370 行 |
| **总计** | **~30 文件** | **~5,270 行** |

## 关键技术贡献
1. **AgentBase 统一框架**：Mock/Fallback/Token预算/上下文裁剪/事件记录
2. **结构化输出校验器**：JSON 提取 + Pydantic 校验 + 3 次重试 + JSON 修复
3. **LLM 多 Provider 工厂**：DeepSeek/OpenAI/ChatAnywhere，单例缓存
4. **三层 Patch 兜底**：git apply → 字符串替换 → 函数级模糊替换（D5 关键突破）
5. **消融实验框架**：22 条评测任务 + 8 维质量评分 + 双运行器
6. **Mock 双层开关**：Agent/Sandbox 独立控制，开发测试灵活切换
7. **5 个 Agent 实现**：Requirement / Planner / Developer / Reviewer / SingleAgent

## 评测数据
- 4 Agent 真实 DeepSeek 调用成功率：100%（22/22 评测任务）
- D5 端到端验证：7/7 tests, $0.0015, 22.4s
- 单 Agent 基线：22/22 (100%), $0.008 总计
- 多 Agent 管道：20/20 (100%), $0.026 总计
- 测试覆盖：322 tests 全部通过
```

### 产出文件

`docs/contribution-b.md`

---

## 执行顺序与依赖

```
9:00 ─┬─ 任务① 真实沙箱对比实验 (1h)
      │   ├─ 扩展 devflow-test-repo（补充 5-8 个模块）
      │   ├─ 写 eval/real_sandbox_compare.py
      │   └─ 跑实验 → 产出 CSV 数据
      │
10:00 ─┬─ 任务② Agent 工具调用集成 前半 (1.5h)
       │   ├─ 新建 app/tools/tool_impls.py
       │   ├─ 新建 prompts/developer_tools.md
       │   └─ 修改 app/agents/base.py（_invoke_with_tools）
       │
11:30 ─┬─ 任务⑤ 个人技术贡献说明 (0.5h)
       │   └─ 写 docs/contribution-b.md
       │
12:00 ──┼─ 午休
       │
13:00 ─┬─ 任务② Agent 工具调用集成 后半 (1.5h)
       │   ├─ 修改 app/agents/developer.py
       │   ├─ 联调 + 用 D5 验证改进效果
       │   └─ 跑全量测试确保无回归
       │
14:30 ─┬─ 任务③ 失败案例分析 (1h)
       │   ├─ 从 CSV 提取 8 条任务的 patch
       │   └─ 人工评级 A/B/C + 写分析笔记
       │
15:30 ─┬─ 任务④ docs/eval-report.md (1h)
       │   ├─ 套用框架
       │   ├─ 填入任务①的实验数据
       │   ├─ 填入任务③的案例分析
       │   └─ 完稿
       │
16:30 ─── 提交所有改动 + push
```

### 依赖关系

```
任务① ─────────────┐
(无依赖)           ├──→ 任务④ (eval-report 需要实验数据)
                   │
任务② ─────────────┤
(无依赖)           │
                   │
任务③ ─────────────┤
(无依赖，可并行)    ├──→ 任务④ (eval-report 需要案例分析)
                   │
任务④ ─────────────┘
(依赖 ①③ 的数据)

任务⑤ — 任意时间可做，无依赖
```

---

## 交付清单

| 文件 | 状态 | 说明 |
|------|:--:|------|
| `eval/real_sandbox_compare.py` | **新建** | 真实沙箱对比评测脚本 |
| `D:\Dev\devflow-test-repo/` | **扩展** | 补充 5-8 个模块（calculator/item_processor/search/config_loader/user_service/file_handler） |
| `eval/setup_test_repo.py` | **新建** | 一键生成测试仓库脚本 |
| `app/tools/tool_impls.py` | **新建** | 工具执行函数 + TOOL_IMPL_MAP |
| `prompts/developer_tools.md` | **新建** | Developer 工具使用说明 |
| `app/agents/base.py` | **修改** | +`_invoke_with_tools()` + `_parse_response()` |
| `app/agents/developer.py` | **修改** | +`ENABLE_TOOL_CALLING = True` |
| `docs/eval-report.md` | **新建** | 评测报告 |
| `docs/contribution-b.md` | **新建** | B 个人技术贡献说明 |
| `eval/real-compare-results.csv` | **新建** | 实验原始数据 |
