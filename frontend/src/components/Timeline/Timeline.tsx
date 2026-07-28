import styles from "./Timeline.module.css";
import type { TaskEvent } from "../../types/task";

interface Props {
  events: TaskEvent[];
}

const EVENT_ICONS: Record<string, string> = {
  node_start: "▶️",
  node_complete: "✅",
  agent_thinking: "🧠",
  tool_call: "🔧",
  tool_result: "📋",
  patch_generated: "📝",
  test_result: "🧪",
  approval_required: "⏸️",
  error: "❌",
  progress: "📌",
  task_complete: "🏁",
};

export default function Timeline({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className={styles.empty}>
        <p>尚无事件记录</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h4 className={styles.title}>事件时间线 ({events.length})</h4>
      <div className={styles.list}>
        {[...events].reverse().slice(0, 20).map((event) => (
          <div key={event.event_id} className={styles.item}>
            <span className={styles.icon}>
              {EVENT_ICONS[event.event_type] || "•"}
            </span>
            <div className={styles.content}>
              <div className={styles.header}>
                {event.node_name && (
                  <span className={styles.node}>{event.node_name}</span>
                )}
                <span className={styles.type}>{event.event_type}</span>
              </div>
              {event.message && (
                <div className={styles.message}>{event.message}</div>
              )}
            </div>
            <span className={styles.time}>
              {formatTime(event.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}
