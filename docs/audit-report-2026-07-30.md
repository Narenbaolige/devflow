# DevFlow 项目完整审计报告 — 2026-07-30

> 生成时间：2026-07-30 | Git HEAD: `7a74b57` | 310 tests passed | ruff clean

---

## 总体状态

| 指标 | 数值 |
|------|------|
| Git HEAD | `7a74b57` (`origin/main`) |
| 总 commits | 38 |
| Python 文件 | 70 (11,719 行) |
| 前端 TSX/TS | 19 (528 行) |
| 测试文件 | 24 (310 passed, 21 网络依赖跳过) |
| 提示词文件 | 7 |
| 文档文件 | 13 |
| ruff lint | All checks passed |

---

## 🔴 严重 (CRITICAL) — 3 项

### CR-1: Docker 沙箱测试执行已损坏

- **文件**: `app/graph.py:453-502`
- **负责人**: C
- **问题**: `run_tests` 节点使用 `sys.executable`（主机 Python 路径，如 `C:\Python311\python.exe`）构建 pytest 命令。当 `SANDBOX_MODE=docker` 时，这个 Windows 路径被传入 Linux Docker 容器，容器中不存在该路径，测试执行会失败。
- **影响**: Docker 沙箱模式的测试执行完全无法工作。
- **修复方向**: 在 Docker 容器内使用固定的 `python3` 或 `python`，或根据沙箱类型动态选择。

### CR-2: Planner prompt 与工具调用能力不匹配

- **文件**: `app/agents/planner.py` + `prompts/planner_agent.md`
- **负责人**: B
- **问题**: `planner_agent.md` 第 8 行明确指示 Planner 使用 `read_file`、`list_dir`、`grep`、`glob` 工具探索项目结构。但 `PlannerAgent` 未覆盖 `ENABLE_TOOL_CALLING`，继承自 `AgentBase` 的默认值 `False`。LLM 若尝试调用工具会失败。
- **影响**: Planner 按照提示词指示执行时会出错，或者 LLM 会忽略提示词指示只基于已有信息规划。
- **修复方向**: 要么在 `PlannerAgent` 中设置 `ENABLE_TOOL_CALLING = True`，要么修改提示词移除工具调用指令。

### CR-3: Docker 沙箱网络隔离文档与代码矛盾

- **文件**: `app/sandbox/docker.py:36 (docstring) vs :144 (code)`
- **负责人**: C
- **问题**: 类文档字符串声明提供 "网络隔离 (--network none)"，但实际代码使用 `network_mode="bridge"`，容器具有完整外网访问权限。此外文档字符串提到 `--read-only` 只读根文件系统，但代码中未使用 `read_only=True`。
- **影响**: Docker 沙箱的安全隔离远低于文档声称的水平。用户以为沙箱断网运行但实际可以任意访问外部网络。
- **修复方向**: 将 `network_mode` 改为 `"none"`，添加 `read_only=True`。

---

## 🟠 高优先级 (HIGH) — 9 项

### HI-1: `_invoke_with_tools` 静默吞掉所有异常

- **文件**: `app/agents/base.py:348-351`
- **负责人**: B
- **问题**: `llm.invoke(messages, tools=tool_defs)` 抛出任何异常（网络错误、认证失败、速率限制等）时，被泛型 `except Exception` 捕获，静默降级到 `_invoke_prompt_only`（纯提示词模式）。这掩盖了真实错误——工具定义拼写错误或无效 API key 都会被隐藏。
- **修复方向**: 至少记录异常日志；区分可恢复错误与致命错误。

### HI-2: TOOL_IMPL_MAP 缺失一半工具实现

- **文件**: `app/tools/tool_impls.py:60-65` + `app/tools/registry.py`
- **负责人**: B
- **问题**: 工具注册表注册了 8 个工具（`read_file`, `list_dir`, `glob`, `grep`, `write_file`, `edit_file`, `sandbox_execute`, `execute_test`），但 `TOOL_IMPL_MAP` 只实现了 4 个（`read_file`, `list_dir`, `grep`, `sandbox_execute`）。`write_file`、`edit_file`、`glob` 被 LLM 调用时会返回 `[未知工具]`。
- **修复方向**: 补全 `TOOL_IMPL_MAP` 中缺失的工具实现，或从注册表中移除未实现的工具。

### HI-3: tool_read_file 无路径遍历保护

- **文件**: `app/tools/tool_impls.py:13-16`
- **负责人**: B
- **问题**: `tool_read_file` 使用 `cat {file_path}` 直接执行 shell 命令。第 13-14 行的路径检查是一个空操作（`if ... : pass`）。LLM 可调用 `tool_read_file("../../etc/passwd")` 读取任意文件。
- **修复方向**: 添加路径遍历检测（拒绝包含 `..`、绝对路径等的路径），限制读取范围到 `repo/` 目录。

### HI-4: _USE_MOCK_SANDBOX 在导入时求值

- **文件**: `app/graph.py:22`
- **负责人**: A/B
- **问题**: `_USE_MOCK_SANDBOX` 在模块导入时从环境变量读取一次并固定。若环境变量在运行时改变（测试中、长时间运行的服务器中），旧值不会更新。这是已知的测试脆弱性来源（`tests/test_d5_real_pipeline.py` 中有明确处理）。
- **修复方向**: 改为运行时函数调用，或使用可动态切换的配置对象。

### HI-5: 10/20 评测任务引用不存在的文件

- **文件**: `eval/tasks/tasks_20.py`
- **负责人**: B
- **问题**: 20 条评测任务中有 10 条引用的目标文件不在 `devflow-test-repo` 中：

| 任务 | 引用的不存在文件 |
|------|-----------------|
| task-002 | `tests/test_user.py`, `models.py` |
| task-004 | `models/user.py` |
| task-007 | `database.py` |
| task-015 | `file_utils.py` |
| task-016 | `api/routes.py`, `constants.py` |
| task-017 | `order_service.py` |
| task-018 | `data_pipeline.py` |
| task-019 | `network.py` |
| task-020 | `db.py`, `cache.py` |

- **修复方向**: 在 `setup_test_repo.py` 中补充对应的模块文件，或修改任务定义使其匹配现有仓库结构。

### HI-6: EvalCompare 页面数据完全硬编码

- **文件**: `frontend/src/pages/EvalCompare/EvalCompare.tsx:13-22`
- **负责人**: D
- **问题**: `COMPARISON_DATA`、`BAR_DATA`、`RADAR_DATA` 全部硬编码为静态数组。后端 `GET /tasks/stats` 返回的 `stats` 数据只用于 4 张统计卡片，图表不反映任何真实评测结果。
- **修复方向**: 从后端 API 拉取数据动态渲染图表。

### HI-7: 前端零测试

- **文件**: `frontend/` 全部
- **负责人**: D
- **问题**: `frontend/` 目录下零个测试文件。`package.json` 无 `test` 脚本，无 vitest/jest/react-testing-library 依赖。19 个 TSX/TS 文件（528 行）没有任何自动化测试覆盖。
- **修复方向**: 安装 vitest + @testing-library/react，至少为核心组件和 hooks 编写测试。

### HI-8: Docker 沙箱零测试

- **文件**: `app/sandbox/docker.py`
- **负责人**: C
- **问题**: `tests/sandbox/` 目录下有 `test_local.py`、`test_manager.py`、`test_multi_repo.py`、`test_stability.py`，但没有任何文件测试 `DockerSandbox`。所有 Docker 代码路径完全无覆盖。
- **修复方向**: 添加 `tests/sandbox/test_docker.py`（可用 `@pytest.mark.docker` 标记，无 Docker 环境时跳过）。

### HI-9: 前端类型与后端合约不一致

- **文件**: `frontend/src/types/task.ts` vs `contracts/state.py`
- **负责人**: D
- **问题**: 前端 `TaskResponse` 使用扁平结构（如 `task_id`、`repo_url`），但后端 `TeamState` 中这些字段嵌套在 `task_meta` dict 内。前端 `EventType` 联合类型缺失 `agent_complete` 和 `agent_fallback`，但后端的 `_record_event()` 会产生这两种事件。
- **修复方向**: 确保 API 转换层正确展开 `task_meta`；在 `EventType` 中补充缺失的事件类型。

---

## 🟡 中优先级 (MEDIUM) — 13 项

### ME-1: TOOL_EXECUTORS 死代码

- **文件**: `app/tools/__init__.py:17-28`
- **负责人**: B
- **问题**: `TOOL_EXECUTORS` 字典注册了 8 个工具映射到 `file_ops.py` 函数，但代码库中无任何地方引用它。实际使用的是 `TOOL_IMPL_MAP`。两个并行的工具映射会误导开发者。
- **修复方向**: 删除 `TOOL_EXECUTORS`，或合并两个映射。

### ME-2: tool_grep shell 注入风险

- **文件**: `app/tools/tool_impls.py:30-32`
- **负责人**: B
- **问题**: `tool_grep` 只转义了单引号，但 `$`、反引号、`;` 等 shell 元字符在 `shell=True` 的 `subprocess.run` 中仍可被解释。
- **修复方向**: 使用 `shlex.quote()` 或改用 `subprocess.run` 的列表参数模式。

### ME-3: Windows 上 shutil.rmtree 失败

- **文件**: `app/sandbox/local.py:134-139`
- **负责人**: C
- **问题**: `cleanup()` 对 `shutil.rmtree` 重试 3 次，间隔 100ms。在 Windows 上，杀毒软件或搜索索引器持有的文件句柄可能远超过 300ms。且 `__del__` 中调用 `cleanup()` 可能在解释器关闭时因模块已回收而失败。
- **修复方向**: 增加重试次数和间隔；`__del__` 中使用 `atexit` 注册替代直接调用。

### ME-4: SandboxManager 别名忽略默认模式

- **文件**: `app/sandbox/manager.py:10`
- **负责人**: C
- **问题**: 向后兼容别名 `SandboxManager = DockerSandbox` 总是映射到 Docker，即使默认沙箱是 `LocalSandbox`（`SANDBOX_MODE=local`）。导入此模块的旧代码会得到错误的沙箱类型。
- **修复方向**: 改为动态别名，根据配置返回正确的沙箱类。

### ME-5: metrics 定价表不完整

- **文件**: `app/metrics.py:15-22`
- **负责人**: B
- **问题**: `PRICING` 表仅有 5 个条目（gpt-4o 等），缺少大多数常见模型。未知模型返回 `$0.00`，静默地少报评测成本。对于以"消融实验成本对比数据"为明确目的（文档字符串第 6 行）来说，这是严重缺陷。
- **修复方向**: 补全定价表（至少覆盖 DeepSeek 全系列 + GPT 全系列 + Claude 全系列）。

### ME-6: _invoke_with_tools 丢弃 LLM 文本推理

- **文件**: `app/agents/base.py:407-411`
- **负责人**: B
- **问题**: LLM 响应中同时包含 `content`（文本）和 `tool_calls` 时，消息只保存工具调用部分，文本推理被丢弃。某些模型（如 Claude）经常同时输出两者，丢弃文本会丢失上下文。
- **修复方向**: 在构建下一轮消息时保留 LLM 的文本内容。

### ME-7: _invoke_with_tools 始终上报 retry_count=0

- **文件**: `app/agents/base.py:370-378, 430-438`
- **负责人**: B
- **问题**: 工具调用模式成功时，`retry_count` 硬编码为 `0`。与 `_invoke_prompt_only` 不同（每次校验失败正确递增 `retry_count`），工具调用模式的重试统计完全不可见。
- **修复方向**: 在工具调用成功路径中跟踪重试次数。

### ME-8: Mock 回退产生无意义补丁

- **文件**: `app/agents/developer.py:64` + `app/agents/base.py:272-282`
- **负责人**: B
- **问题**: 所有 LLM 重试失败后降级到 mock 结果时，`DeveloperAgent.mock_result()` 总是返回 `file_path="src/main.py"` 和参数校验相关的固定 diff。与当前任务完全不相关，下游 `apply_patches` 会应用这个无意义的补丁。
- **修复方向**: 回退时至少尝试保留任务上下文，或标记为不可恢复错误而非应用假补丁。

### ME-9: CORS 配置非标准

- **文件**: `app/api/tasks.py:50`
- **负责人**: A
- **问题**: `allow_origins` 同时包含 `"*"` 和具体的 `"http://localhost:5173"`。大多数实现中通配符会覆盖显式来源，这是一个非标准组合。
- **修复方向**: 只使用 `["*"]` 或只使用显式来源列表。

### ME-10: API 文档与实际不同步

- **文件**: `docs/api.md:139-146`
- **负责人**: A
- **问题**: 文档提到 SQLite Checkpointer 可用，但实现中只有 `MemorySaver` 和 `AsyncPostgresSaver`，无 SQLite。
- **修复方向**: 更新文档反映实际实现，或实现 SQLite Checkpointer。

### ME-11: 前端无请求取消机制

- **文件**: `frontend/src/services/api.ts`
- **负责人**: D
- **问题**: `request` 函数无 `AbortController` 支持。用户在请求进行中导航离开时，可能产生内存泄漏或状态更新冲突。
- **修复方向**: 添加 `AbortController` 参数支持请求取消。

### ME-12: 前端 ApprovalPanel 审批后不刷新

- **文件**: `frontend/src/components/ApprovalPanel/ApprovalPanel.tsx:19-33`
- **负责人**: D
- **问题**: 批准/拒绝操作完成后只设置本地状态，不触发 `refetch` 重新加载任务数据。用户必须等待下一次 2 秒轮询周期才能看到状态更新。
- **修复方向**: 审批操作成功后调用 `refetch` 或通过 callback 通知父组件。

### ME-13: EventType 前端类型缺失

- **文件**: `frontend/src/types/task.ts:17`
- **负责人**: D
- **问题**: `EventType` 联合类型中缺失后端会产生的事件类型: `agent_complete`、`agent_fallback`、`node_start`。导致 TypeScript 无法正确类型检查这些事件的处理逻辑。
- **修复方向**: 在 `EventType` 联合类型中补充 `"agent_complete" | "agent_fallback" | "node_start"`。

---

## ⚪ 低优先级 (LOW) — 14 项

| # | 文件 | 负责人 | 问题 |
|---|------|:---:|------|
| LO-1 | `app/contracts/event.py` | A | `TaskEvent` Pydantic 模型已定义但从未被使用——所有事件以普通 dict 存储 |
| LO-2 | `app/contracts/sandbox_result.py` | C | `SandboxCapabilities` 类已定义但从未被引用或导出 |
| LO-3 | `app/config.py:16,54,47` | A | `DATABASE_URL`、`DEVFLOW_DEBUG_CONTEXT`、`MAX_ITERATIONS` 死配置项——定义但未使用 |
| LO-4 | `app/agents/validator.py:162-168` | B | JSON 修复函数 `_try_repair_json` 只处理尾随逗号，不处理单引号、Python 字面量等 |
| LO-5 | `app/agents/single_agent.py:87-88` | B | 用 `AgentRole.REVIEWER` 作为占位符——单 Agent 和 Reviewer 在观测上不可区分 |
| LO-6 | `app/agents/reviewer.py:56-59` | B | `build_context` 中硬编码的安全检查规则与 `reviewer_security_rules.md` 重复 |
| LO-7 | `app/agents/base.py:416` | B | 工具调用结果静默截断到 4000 字符，无提示 |
| LO-8 | `app/agents/base.py:102-121` | B | 注入过滤器只覆盖英文子串，不覆盖变体或其他语言 |
| LO-9 | `app/sandbox/base.py:102-136` | C | `_check_paths` 只产生警告，不实际阻止危险命令执行 |
| LO-10 | `app/sandbox/docker.py:154-157` | C | `pip install pytest` 无超时参数，可能无限期阻塞 |
| LO-11 | `eval/setup_test_repo.py:502` | B | 硬编码路径 `D:/Dev/devflow-test-repo`——Linux/macOS 上不可用 |
| LO-12 | `tests/test_d5_real_pipeline.py:62` | B | 同上硬编码 Windows 路径 |
| LO-13 | `frontend/src/components/Timeline.tsx:28` | D | 事件列表截断到 30 条，无"显示更多"按钮 |
| LO-14 | `frontend/README.md` | D | 仍是 Vite 模板默认内容，非 DevFlow 项目文档 |

---

## 📋 按成员汇总

### B (那仁宝力格) — 15 项

| 优先级 | # | 问题摘要 |
|:------:|:--:|---------|
| 🔴 | CR-2 | Planner prompt 与 ENABLE_TOOL_CALLING 不匹配 |
| 🟠 | HI-1 | `_invoke_with_tools` 吞掉异常 |
| 🟠 | HI-2 | TOOL_IMPL_MAP 缺 4 个工具实现 |
| 🟠 | HI-3 | tool_read_file 无路径遍历保护 |
| 🟠 | HI-5 | 10/20 评测任务文件不存在 |
| 🟡 | ME-1 | TOOL_EXECUTORS 死代码 |
| 🟡 | ME-2 | tool_grep shell 注入风险 |
| 🟡 | ME-5 | metrics 定价表不完整 |
| 🟡 | ME-6 | 丢弃 LLM 文本推理 |
| 🟡 | ME-7 | retry_count 始终为 0 |
| 🟡 | ME-8 | Mock 回退产生无意义补丁 |
| ⚪ | LO-4~8 | 校验器、Agent 角色、重复规则、截断、注入过滤 |

### C — 8 项

| 优先级 | # | 问题摘要 |
|:------:|:--:|---------|
| 🔴 | CR-1 | Docker 使用主机 Python 路径 |
| 🔴 | CR-3 | 网络隔离文档≠代码 |
| 🟠 | HI-8 | Docker 沙箱零测试 |
| 🟡 | ME-3 | Windows rmtree 失败 |
| 🟡 | ME-4 | SandboxManager 别名错误 |
| ⚪ | LO-2 | SandboxCapabilities 未使用 |
| ⚪ | LO-9 | 路径检查只警告不阻止 |
| ⚪ | LO-10 | pip install 无超时 |

### D — 8 项

| 优先级 | # | 问题摘要 |
|:------:|:--:|---------|
| 🟠 | HI-6 | EvalCompare 数据硬编码 |
| 🟠 | HI-7 | 前端零测试 |
| 🟠 | HI-9 | 前端类型与后端不一致 |
| 🟡 | ME-11 | 无请求取消机制 |
| 🟡 | ME-12 | 审批后不刷新 |
| 🟡 | ME-13 | EventType 缺失 |
| ⚪ | LO-13 | 事件截断无"显示更多" |
| ⚪ | LO-14 | 前端 README 错误 |

### A — 5 项

| 优先级 | # | 问题摘要 |
|:------:|:--:|---------|
| 🟡 | ME-9 | CORS 非标准 |
| 🟡 | ME-10 | 文档与实际不同步 |
| ⚪ | LO-1 | TaskEvent 未使用 |
| ⚪ | LO-3 | 3 个死配置项 |
| 🟠 | HI-4 | _USE_MOCK_SANDBOX 导入时求值 (与 B 共享) |

---

## 📈 统计

| 严重性 | 数量 |
|:------|:----:|
| 🔴 严重 | 3 |
| 🟠 高 | 9 |
| 🟡 中 | 13 |
| ⚪ 低 | 14 |
| **总计** | **39** |

| 负责人 | 数量 |
|:------|:----:|
| B (那仁宝力格) | 15 |
| C | 8 |
| D | 8 |
| A | 5 |
| A/B 共享 | 1 |

---

*由三路并行代码审计生成，覆盖 API/工作流、Agents/工具/沙箱、前端/测试/评测/文档全部模块。*
