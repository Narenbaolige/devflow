import { useState } from "react";
import { approveTask, rejectTask } from "../../services/api";
import styles from "./ApprovalPanel.module.css";

interface Props {
  taskId: string;
}

export default function ApprovalPanel({ taskId }: Props) {
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<"approved" | "rejected" | null>(null);

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await approveTask(taskId, feedback);
      setResult("approved");
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    setSubmitting(true);
    try {
      await rejectTask(taskId, feedback);
      setResult("rejected");
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className={`${styles.container} ${result === "approved" ? styles.approvedBox : styles.rejectedBox}`}>
        <span className={styles.resultIcon}>{result === "approved" ? "✅" : "🔄"}</span>
        <span>{result === "approved" ? "已批准，继续执行" : "已拒绝，返回修改"}</span>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.warnIcon}>⏸️</span>
        <div>
          <h4>需要人工审批</h4>
          <p className={styles.hint}>系统检测到高风险操作，请审查后决定是否继续</p>
        </div>
      </div>

      <textarea
        className={styles.textarea}
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="审批意见（选填）..."
        rows={3}
        disabled={submitting}
      />

      <div className={styles.buttons}>
        <button
          className={styles.approveBtn}
          onClick={handleApprove}
          disabled={submitting}
        >
          ✅ 批准通过
        </button>
        <button
          className={styles.rejectBtn}
          onClick={handleReject}
          disabled={submitting}
        >
          ❌ 拒绝，返回修改
        </button>
      </div>
    </div>
  );
}
