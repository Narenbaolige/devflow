import { useState, useEffect, useCallback } from "react";
import { getTask } from "../services/api";
import type { TaskResponse } from "../types/task";

/**
 * 轮询任务状态（2 秒间隔）。
 * 任务到达终态（done/failed/cancelled）后自动停止。
 */
export function useTaskPolling(taskId: string | undefined) {
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTask = useCallback(async () => {
    if (!taskId) return;
    try {
      const data = await getTask(taskId);
      setTask(data);
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "获取任务失败");
      return null;
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;

    let active = true;
    const terminalPhases = new Set(["done", "failed", "cancelled"]);

    const poll = async () => {
      const data = await fetchTask();
      if (!active || !data) return;
      if (terminalPhases.has(data.phase)) return; // 停止轮询
    };

    // 立即获取一次
    poll();

    // 每 2 秒轮询
    const interval = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [fetchTask, taskId]);

  return { task, loading, error, refetch: fetchTask };
}
