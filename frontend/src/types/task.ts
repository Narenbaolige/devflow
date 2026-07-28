// ============================================================================
// DevFlow 前端类型定义 — 与后端 contracts/ 完全对齐
// 所有字段名保持 snake_case，与后端 API 返回一致
// ============================================================================

// ── 阶段枚举 ──
export type Phase =
  | "init" | "analyzing" | "planning" | "developing"
  | "testing" | "reviewing" | "security_check"
  | "awaiting_approval" | "done" | "failed" | "cancelled";

// ── 事件类型 ──
export type EventType =
  | "node_start" | "node_complete"
  | "agent_thinking" | "tool_call" | "tool_result"
  | "patch_generated" | "test_result"
  | "approval_required" | "error" | "progress" | "task_complete";

// ── Agent 角色 ──
export type AgentRole = "requirement" | "planner" | "developer" | "reviewer" | "security";

// ── 任务元数据 ──
export interface TaskMeta {
  task_id: string;
  repo_url: string;
  branch: string;
  requirement: string;
  created_at: string;
}

// ── 错误记录 ──
export type ErrorType =
  | "llm_error" | "sandbox_error" | "timeout"
  | "budget_exceeded" | "validation_error" | "unknown";

export interface ErrorRecord {
  node: string;
  error_type: ErrorType;
  message: string;
  timestamp: string;
  recoverable: boolean;
  retry_count: number;
}

// ── 统一事件模型 ──
export interface TaskEvent {
  event_id: string;
  task_id: string;
  event_type: EventType;
  node_name: string | null;
  agent_role: AgentRole | null;
  timestamp: string;
  data: Record<string, unknown> | null;
  message: string;
}

// ── Agent 产出物 ──
export interface RequirementResult {
  summary: string;
  affected_modules: string[];
  acceptance_criteria: string[];
  ambiguity_flags: string[];
  confidence: number;
}

export interface PlanStep {
  step_id: number;
  description: string;
  target_files: string[];
  expected_changes: string;
  depends_on: number[];
}

export interface PlanResult {
  approach: string;
  steps: PlanStep[];
  risk_points: string[];
  alternative_approaches: string[];
  estimated_changed_files: number;
  confidence: number;
}

export type ChangeType = "add" | "modify" | "delete" | "rename";

export interface PatchResult {
  file_path: string;
  original_snippet: string;
  patched_snippet: string;
  diff: string;
  change_description: string;
  change_type: ChangeType;
}

export type IssueSeverity = "critical" | "high" | "major" | "minor" | "suggestion";

export interface ReviewIssue {
  severity: IssueSeverity;
  file_path: string;
  line_range: string | null;
  description: string;
  suggestion: string;
}

export type RiskLevel = "low" | "medium" | "high";

export interface ReviewResult {
  passed: boolean;
  risk_level: RiskLevel;
  issues: ReviewIssue[];
  summary: string;
  actionable_feedback: string;
}

export type SecuritySeverity = "critical" | "high" | "medium" | "low";

export interface SecurityIssue {
  vulnerability_type: string;
  severity: SecuritySeverity;
  file_path: string;
  line_range: string | null;
  description: string;
  remediation: string;
  cwe_id: string | null;
}

export interface SecurityResult {
  passed: boolean;
  issues: SecurityIssue[];
  summary: string;
  requires_approval: boolean;
}

export interface AgentInvocation {
  agent_role: AgentRole;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  duration_ms: number;
  retry_count: number;
  timestamp: string;
}

export interface AgentResult {
  agent_role: AgentRole;
  success: boolean;
  result: Record<string, unknown> | null;
  error: string | null;
  invocation: AgentInvocation | null;
  reasoning: string;
  next_action: string;
}

// ── 沙箱结果 ──
export type SandboxType = "test" | "lint" | "type_check" | "custom";
export type SandboxStatus = "success" | "failure" | "timeout" | "error";
export type FailureType = "assertion" | "error" | "timeout" | "import_error" | "other";

export interface TestSummary {
  total: number;
  passed: number;
  failed: number;
  errors: number;
  skipped: number;
  duration_ms: number;
}

export interface TestFailure {
  test_name: string;
  test_file: string;
  failure_type: FailureType;
  message: string;
  traceback: string;
  is_new_failure: boolean;
}

export interface SandboxResult {
  execution_id: string;
  task_id: string;
  sandbox_type: SandboxType;
  status: SandboxStatus;
  exit_code: number;
  timed_out: boolean;
  duration_ms: number;
  stdout: string;
  stderr: string;
  test_summary: TestSummary | null;
  test_failures: TestFailure[];
  max_memory_mb: number | null;
  max_cpu_percent: number | null;
  started_at: string;
  finished_at: string;
}

// ── API 请求模型 ──
export interface CreateTaskRequest {
  requirement: string;
  repo_url: string;
  branch?: string;
  max_iterations?: number;
  timeout_seconds?: number;
  budget_limit_usd?: number | null;
}

export interface ApproveRequest {
  feedback?: string;
}

// ── API 响应模型 ──
export interface TaskResponse {
  task_id: string;
  phase: Phase;
  requirement: string;
  repo_url: string;
  iteration: number;
  errors: ErrorRecord[];
  created_at: string;
  approval_required: boolean;
  approval_granted: boolean;
  cancel_requested: boolean;
  current_node: string | null;
  deadline_at: string | null;
  budget_limit_usd: number | null;
  budget_used_usd: number;
}

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
}

export interface TaskStatsResponse {
  total_tasks: number;
  phase_counts: Record<string, number>;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  cancelled_tasks: number;
  awaiting_approval_tasks: number;
  average_iterations: number;
  average_duration_ms: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
}

// ── 节点配置（前端展示用）─ ──
export interface NodeConfig {
  key: string;
  label: string;
  icon: string;
  agentRole: AgentRole | null;
}

export const WORKFLOW_NODES: NodeConfig[] = [
  { key: "init_task",          label: "初始化",     icon: "🚀", agentRole: null },
  { key: "analyze_requirement", label: "需求分析",   icon: "📋", agentRole: "requirement" },
  { key: "create_plan",        label: "方案规划",   icon: "📝", agentRole: "planner" },
  { key: "develop_changes",    label: "代码生成",   icon: "💻", agentRole: "developer" },
  { key: "run_tests",          label: "运行测试",   icon: "🧪", agentRole: null },
  { key: "review_changes",     label: "代码审查",   icon: "🔍", agentRole: "reviewer" },
  { key: "security_check",     label: "安全检查",   icon: "🛡️", agentRole: "security" },
  { key: "await_approval",     label: "等待审批",   icon: "⏸️", agentRole: null },
];

// ── 阶段显示配置 ──
export const PHASE_CONFIG: Record<Phase, { label: string; color: string }> = {
  init:                { label: "初始化",       color: "#8b949e" },
  analyzing:           { label: "需求分析中",   color: "#58a6ff" },
  planning:            { label: "方案规划中",   color: "#bc8cff" },
  developing:          { label: "代码生成中",   color: "#d29922" },
  testing:             { label: "测试执行中",   color: "#d29922" },
  reviewing:           { label: "代码审查中",   color: "#bc8cff" },
  security_check:      { label: "安全检查中",   color: "#f0883e" },
  awaiting_approval:   { label: "等待审批",     color: "#f85149" },
  done:                { label: "已完成",       color: "#3fb950" },
  failed:              { label: "失败",         color: "#f85149" },
  cancelled:           { label: "已取消",       color: "#8b949e" },
};
