import { useEffect, useState } from "react";
import styles from "./Toast.module.css";

export interface ToastMessage {
  id: number;
  type: "error" | "warning" | "success" | "info";
  message: string;
  detail?: string;
}

interface Props {
  messages: ToastMessage[];
  onDismiss: (id: number) => void;
}

export default function Toast({ messages, onDismiss }: Props) {
  return (
    <div className={styles.container}>
      {messages.map((msg) => (
        <ToastItem key={msg.id} msg={msg} onDismiss={() => onDismiss(msg.id)} />
      ))}
    </div>
  );
}

function ToastItem({ msg, onDismiss }: { msg: ToastMessage; onDismiss: () => void }) {
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setFading(true);
      setTimeout(onDismiss, 300);
    }, 6000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className={`${styles.toast} ${styles[msg.type]} ${fading ? styles.fadeOut : ""}`}
      onClick={onDismiss}
    >
      <span className={styles.icon}>
        {msg.type === "error" ? "❌" : msg.type === "warning" ? "⚠️" : msg.type === "success" ? "✅" : "ℹ️"}
      </span>
      <div className={styles.body}>
        <div className={styles.message}>{msg.message}</div>
        {msg.detail && <div className={styles.detail}>{msg.detail}</div>}
      </div>
      <button className={styles.close} onClick={onDismiss}>×</button>
    </div>
  );
}
