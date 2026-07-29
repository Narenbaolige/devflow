// ============================================================================
// DevFlow API 服务层 — 封装所有后端调用
// ============================================================================

import type {
  TaskResponse,
  TaskListResponse,
  TaskStatsResponse,
  CreateTaskRequest,
  ApproveRequest,
} from "../types/task";

const API_BASE = "/tasks";

// ── 结构化错误 ──
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ── 通用 fetch 封装 ──
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError("网络连接失败，请检查后端服务是否启动", 0);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || `请求失败: ${res.status} ${res.statusText}`, res.status);
  }
  return res.json();
}

// ── 任务 CRUD ──

/** 创建新任务 */
export async function createTask(data: CreateTaskRequest): Promise<TaskResponse> {
  return request<TaskResponse>(API_BASE, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** 查询任务状态 */
export async function getTask(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`${API_BASE}/${taskId}`);
}

/** 列出所有任务 */
export async function listTasks(limit = 20, offset = 0): Promise<TaskListResponse> {
  return request<TaskListResponse>(`${API_BASE}?limit=${limit}&offset=${offset}`);
}

/** 获取任务统计 */
export async function getTaskStats(): Promise<TaskStatsResponse> {
  return request<TaskStatsResponse>(`${API_BASE}/stats`);
}

// ── 任务控制 ──

/** 审批通过 */
export async function approveTask(taskId: string, feedback = ""): Promise<TaskResponse> {
  return request<TaskResponse>(`${API_BASE}/${taskId}/approve`, {
    method: "POST",
    body: JSON.stringify({ feedback } satisfies ApproveRequest),
  });
}

/** 审批拒绝 */
export async function rejectTask(taskId: string, feedback = ""): Promise<TaskResponse> {
  return request<TaskResponse>(`${API_BASE}/${taskId}/reject`, {
    method: "POST",
    body: JSON.stringify({ feedback } satisfies ApproveRequest),
  });
}

/** 取消任务 */
export async function cancelTask(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`${API_BASE}/${taskId}/cancel`, {
    method: "POST",
  });
}

/** 健康检查 */
export async function healthCheck(): Promise<{ status: string; version: string; service: string }> {
  return request("/health");
}
