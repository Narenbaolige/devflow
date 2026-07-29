import styles from "./Timeline.module.css";
import type { TaskEvent } from "../../types/task";

interface Props {
  events: TaskEvent[];
}

const EVENT_CONFIG: Record<string, { label: string; color: string }> = {
  node_start:          { label: "开始",   color: "#58a6ff" },
  node_complete:       { label: "完成",   color: "#3fb950" },
  agent_thinking:      { label: "推理",   color: "#bc8cff" },
  agent_complete:      { label: "Agent",  color: "#3fb950" },
  tool_call:           { label: "工具",   color: "#d29922" },
  tool_result:         { label: "结果",   color: "#d29922" },
  patch_generated:     { label: "Patch",  color: "#f0883e" },
  test_result:         { label: "测试",   color: "#58a6ff" },
  approval_required:   { label: "审批",   color: "#f85149" },
  error:               { label: "错误",   color: "#f85149" },
  progress:            { label: "进度",   color: "#8b949e" },
  task_complete:       { label: "完成",   color: "#3fb950" },
};

export default function Timeline({ events }: Props) {
  if (events.length === 0) {
    return <div className={styles.empty}>尚无事件记录</div>;
  }

  const recent = [...events].reverse().slice(0, 30);

  return (
    <div className={styles.container}>
      <h4 className={styles.title}>事件时间线</h4>
      <div className={styles.line}>
        {recent.map((event) => {
          const cfg = EVENT_CONFIG[event.event_type] ?? { label: event.event_type, color: "#8b949e" };
          return (
            <div key={event.event_id} className={styles.item}>
              <div className={styles.dot} style={{ background: cfg.color }} />
              <div className={styles.content}>
                <span className={styles.tag} style={{ color: cfg.color, borderColor: cfg.color }}>
                  {cfg.label}
                </span>
                {event.node_name && <span className={styles.node}>{event.node_name}</span>}
                {event.message && <span className={styles.message}>{event.message}</span>}
              </div>
              <span className={styles.time}>{formatTime(event.timestamp)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    if (diff < 60000) return `${Math.floor(diff / 1000)}s`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}
