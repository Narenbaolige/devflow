# 工作日志 — 2026-07-24

## 负责人

C（执行环境与可靠性）

## 完成内容

### 1. 沙箱架构重构：从聪明流水线到工具原语

**之前的设计**：沙箱是一个"聪明"的 Python 测试流水线
- `SandboxManager.execute_pytest(task_id, repo_url, branch, patches)` — 内置 clone → pip → pytest → 解析
- 沙箱懂 Python、懂 pip、懂 pytest 输出格式
- 遇到 `tox`、`make test`、`npm test` 全部无效
- 逻辑 400+ 行，难以扩展

**之后的设计**：沙箱是一个"笨"工具 — Agent 是大脑，沙箱是手
- `sandbox.execute(command, cwd, timeout) -> CommandResult` — 唯一核心方法
- 沙箱不解析、不判断、不决策，只执行命令
- Agent 自行决定测试策略、解读结果
- `execute_pytest` 降级为便捷方法，内部调用 `execute()` 组合实现

**接口对比**：

```
之前：                   现在：
sandbox.execute_pytest(   sandbox.execute("git clone ...")
    task_id,             sandbox.execute("pip install -e .")
    repo_url,            sandbox.execute("pytest -v")
    branch,              # Agent 自己读 stdout 判断结果
    patches,             # 或者一行搞定：
)                        result = sandbox.execute_pytest(...)
```

### 2. 新增文件

| 文件 | 说明 |
|------|------|
| `app/sandbox/base.py` | 重写 — `CommandResult` 模型 + `BaseSandbox` 抽象基类。`execute()` 是唯一抽象方法。`execute_pytest` 是便捷实现 |
| `app/sandbox/local.py` | 重写 — 只实现 `execute()`（subprocess），40 行核心逻辑 |
| `app/sandbox/docker.py` | 重写 — 只实现 `execute()`（Docker SDK），100 行核心逻辑 |

### 3. 修改文件

| 文件 | 改动 |
|------|------|
| `app/sandbox/__init__.py` | 导出 `CommandResult`，`create_sandbox()` 不变 |
| `app/sandbox/manager.py` | 保持 `SandboxManager = DockerSandbox` 别名 |
| `app/graph.py` | 更新 `run_tests` 注释，说明新接口用法 |
| `app/config.py` | `SANDBOX_MODE` 配置（上轮已完成） |
| `.env.example` | `SANDBOX_MODE=local`（上轮已完成） |
| `README.md` | 前置要求砍掉 Docker，快速开始 4 步（上轮已完成） |

### 4. 验证结果

- 23 个单元测试全绿 ✅
- `LocalSandbox.execute()` 在 markupsafe 仓库真实跑通：79 passed, 0 failed, 1.1s
- `LocalSandbox.execute_pytest()` 便捷方法同样正常
- Docker 模式导入可用（未实际执行，需要 Docker Desktop）

### 5. 架构影响（告知队友）

| 成员 | 影响 | 行动 |
|------|------|------|
| **A** | `run_tests` 节点需要从固定流水线改为 Agent 循环 | Day 3 和 Agent 节点切换一起做，注释已写好 |
| **B** | Developer Agent 获得 `sandbox.execute` 工具 | 以前是固定的 `execute_test`，现在 Agent 可以跑任意命令。Prompt 需要加一段"如何决定测试策略" |
| **D** | 零影响 | `SandboxResult` 不变，`CommandResult` 是新增模型 |
| **C（自己）** | 后续补 Local/Docker 沙箱的集成测试 | Day 3 以后 |

### 6. 设计决策记录

1. **相对路径策略**：`execute_pytest` 便捷方法使用 `cwd="repo"` 而非 `/workspace/repo`，确保 Windows/Linux 兼容
2. **CommandResult 不放 contracts/**：放在 `app/sandbox/base.py`，避免 P0 冻结流程。后续稳定了再迁
3. **`_parse_pytest_output` 保留在 base.py**：作为便捷方法的一部分，Agent 如果自己用 `execute()` 跑 pytest，需要自己解析 — 这是有意为之（Agent 是大脑）

## 依赖与阻塞

- 无阻塞
- Docker Desktop 已就绪（`docker info` 显示 29.6.2）
- 镜像 `python:3.11-slim` 待拉取
