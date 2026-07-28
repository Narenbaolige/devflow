import { useState, useEffect, useRef, useCallback } from "react";
import type { TaskEvent } from "../types/task";

/**
 * SSE 事件流订阅。
 * 连接后先回放历史事件，再推送新事件。
 * 任务到达终态时自动关闭连接。
 */
export function useTaskSSE(taskId: string | undefined) {
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const close = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    // 关闭之前的连接
    eventSourceRef.current?.close();
    setEvents([]);
    setConnected(false);

    const url = `/tasks/${taskId}/events`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onerror = () => {
      setConnected(false);
      // EventSource 会自动重连
    };

    // 监听所有 SSE 事件类型，统一追加到 events 数组
    const handler = (e: MessageEvent) => {
      try {
        const event: TaskEvent = JSON.parse(e.data);
        setEvents((prev) => {
          // 去重（按 event_id）
          if (prev.some((ev) => ev.event_id === event.event_id)) return prev;
          return [...prev, event];
        });
        // 终态时关闭
        if (event.event_type === "task_complete") {
          es.close();
          setConnected(false);
        }
      } catch {
        // 解析失败忽略
      }
    };

    // 注册常见事件类型
    const eventTypes = [
      "progress", "node_start", "node_complete",
      "agent_thinking", "tool_call", "tool_result",
      "patch_generated", "test_result",
      "approval_required", "error", "task_complete",
    ];
    eventTypes.forEach((type) => es.addEventListener(type, handler));

    return () => {
      es.close();
      eventSourceRef.current = null;
      setConnected(false);
    };
  }, [taskId]);

  return { events, connected, close };
}
