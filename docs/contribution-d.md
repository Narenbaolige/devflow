# 个人技术贡献说明 — D

## 基本信息

- **姓名**：张铭洋
- **角色**：前端与系统评测负责人
- **项目**：DevFlow — 基于 LangGraph 的多 Agent 协同软件工程平台

## 负责模块与量化成果

| 模块 | 文件 | 代码量 |
|------|------|:--:|
| React 前端核心 | `frontend/src/` | ~2800 行 |
| 页面组件（3 页） | `pages/TaskCreate/` `pages/TaskDetail/` `pages/EvalCompare/` | ~600 行 |
| 通用组件（7 个） | `components/Layout/` `StatusBadge/` `StatsCard/` `DiffViewer/` `TestPanel/` `Timeline/` `ApprovalPanel/` `Toast/` | ~900 行 |
| 自定义 Hooks（3 个） | `hooks/useTaskPolling.ts` `useTaskSSE.ts` `useNetworkStatus.ts` | ~120 行 |
| API 服务层 | `services/api.ts` | ~80 行 |
| TypeScript 类型定义 | `types/task.ts` | ~160 行（30+ 接口/类型） |
| 样式（CSS Modules） | 10 个 `.module.css` | ~700 行 |
| 项目配置 | `vite.config.ts` `tsconfig.json` `package.json` | ~50 行 |
| 启动脚本 | `start.bat` `start.ps1` | ~60 行 |
| 评测报告 | `docs/eval-report.md` | ~150 行 |
| 任务清单 | `docs/D-task-checklist.md` | ~150 行 |
| 测试仓库 | `example-wuziqi`（五子棋，11 tests） | ~250 行 |
| **总计** | **~33 文件** | **~5200 行** |

## 关键技术贡献

### 1. React 前端完整实现

独立完成 DevFlow 前端 3 个核心页面的设计与编码：

- **任务创建页**：表单校验 + 高级选项折叠面板 + API 对接 + 提交后自动跳转
- **任务详情页**（核心）：双栏布局，左侧实时进度面板 + 右侧产出物展示
  - 左侧：8 节点状态列表 + 事件时间线 + 统计卡片 + 错误面板
  - 右侧：Diff 代码对比 + 测试结果面板 + 审批交互
- **评测对比页**：统计卡片行 + Recharts 柱状图/雷达图 + 指标对比表 + 关键发现

### 2. 实时数据推送与轮询双通道

- **轮询通道**：`useTaskPolling` Hook，2 秒间隔轮询 `GET /tasks/{id}`，终态自动停止
- **SSE 通道**：`useTaskSSE` Hook，EventSource 订阅 `GET /tasks/{id}/events`，支持断线重连
- 两种方式互补，确保前端实时展示任务执行进度

### 3. Unified Diff 解析与可视化

自研 `DiffViewer` 组件，解析 unified diff 格式字符串：
- 行号追踪（跟踪 `@@ -old,count +new,count @@` hunk 头）
- 红删绿增高亮（删除行红底、新增行绿底）
- 支持 5 种变更类型标记（add/modify/delete/rename）

### 4. 评测对比可视化

使用 Recharts 实现多维度对比图表：
- **柱状图**：5 个任务类别 × 2 种模式的成功率对比
- **雷达图**：5 个维度（成功率/首次通过率/代码质量/安全检测/回归防护）

### 5. 前端工程化

- Vite + TypeScript 严格模式，编译零错误
- 10 个 CSS Modules，组件级样式隔离
- 所有 API 字段名与后端 `snake_case` 对齐
- 错误处理完善：Toast 全局通知 + 网络断开检测 + API 请求重试
- 深色主题 UI（GitHub Dark 风格）

### 6. 测试仓库建设

创建 `example-wuziqi` 五子棋测试仓库：
- 完整游戏逻辑（15×15 棋盘、落子、胜负判断、棋盘状态）
- 11 条 pytest 测试（覆盖正常落子/越界/五连获胜/获胜后不可落子/重置等场景）
- 用于 DevFlow 真实模式端到端验证

### 7. 一键启动脚本

编写 `start.bat` + `start.ps1`，双击即可同时启动前后端，演示友好。

## 评测数据

- Mock 模式：单 Agent 20/20 (100%) vs 多 Agent 20/20 (100%)
- 真实沙箱：单 Agent 15/25 (60%) vs 多 Agent 22/25 (90%)
- 多 Agent 返工修正：3 个首次失败 patch 被 Reviewer 反馈修正
- 安全漏洞发现：2 个（路径遍历、硬编码密钥），单 Agent 未检出
- D5 端到端验证：11/11 tests passed, $0.0004, ~30s
