import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Send, ChevronDown } from "lucide-react";
import { createTask, listTasks } from "../../services/api";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import type { TaskResponse } from "../../types/task";
import styles from "./TaskCreate.module.css";

const DEFAULT_VALUES = {
  repo_url: "https://github.com/Narenbaolige/devflow-test-repo",
  branch: "main",
  max_iterations: 3,
  timeout_seconds: 900,
};

export default function TaskCreate() {
  const navigate = useNavigate();
  const [requirement, setRequirement] = useState("");
  const [repoUrl, setRepoUrl] = useState(DEFAULT_VALUES.repo_url);
  const [branch, setBranch] = useState(DEFAULT_VALUES.branch);
  const [maxIterations, setMaxIterations] = useState(DEFAULT_VALUES.max_iterations);
  const [timeoutSeconds, setTimeoutSeconds] = useState(DEFAULT_VALUES.timeout_seconds);
  const [budgetLimit, setBudgetLimit] = useState("");
  const [publishToRemote, setPublishToRemote] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskResponse[]>([]);

  useEffect(() => {
    listTasks(5, 0)
      .then((res) => setRecentTasks(res.tasks))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requirement.trim()) { setError("Please describe your requirement"); return; }
    if (!repoUrl.trim()) { setError("Please enter a repository URL"); return; }
    setSubmitting(true);
    setError(null);
    try {
      const task = await createTask({
        requirement: requirement.trim(),
        repo_url: repoUrl.trim(),
        branch: branch.trim() || "main",
        max_iterations: maxIterations,
        timeout_seconds: timeoutSeconds,
        budget_limit_usd: budgetLimit ? parseFloat(budgetLimit) : undefined,
        publish_to_remote: publishToRemote,
      });
      navigate(`/tasks/${task.task_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      {/* 渐变装饰 */}
      <div className={styles.gradientBar} />

      <div className={styles.header}>
        <h1>Start a new task</h1>
        <p>Describe what you need — the agent pipeline will analyze, plan, code, test, and review automatically.</p>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label}>Requirement</label>
          <textarea className={styles.textarea} value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            placeholder="e.g. Add input validation to the factorial function"
            rows={3} disabled={submitting} />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>Repository URL</label>
          <input className={styles.input} type="text" value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/..." disabled={submitting} />
        </div>

        <details className={styles.advanced}>
          <summary className={styles.advancedTitle}>
            <ChevronDown size={14} /> Advanced options
          </summary>
          <div className={styles.advancedGrid}>
            <div className={styles.field}>
              <label className={styles.label}>Branch</label>
              <input className={styles.input} type="text" value={branch}
                onChange={(e) => setBranch(e.target.value)} disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Max iterations</label>
              <input className={styles.input} type="number" min={1} max={10}
                value={maxIterations} onChange={(e) => setMaxIterations(Number(e.target.value))}
                disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Timeout (seconds)</label>
              <input className={styles.input} type="number" min={1} max={3600}
                value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Budget limit (USD)</label>
              <input className={styles.input} type="number" min={0} step={0.001}
                value={budgetLimit} onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder="Unlimited" disabled={submitting} />
            </div>
          </div>
          <label className={styles.publishOption}>
            <input type="checkbox" checked={publishToRemote}
              onChange={(e) => setPublishToRemote(e.target.checked)} disabled={submitting} />
            Push to remote repository after verification
          </label>
        </details>

        {error && <div className={styles.error}>{error}</div>}

        <button className={styles.submitBtn} type="submit" disabled={submitting}>
          <Send size={16} />
          {submitting ? "Creating..." : "Create task"}
        </button>
      </form>

      {recentTasks.length > 0 && (
        <div className={styles.recentSection}>
          <h3>Recent tasks</h3>
          <div className={styles.recentList}>
            {recentTasks.map((t) => (
              <div key={t.task_id} className={styles.recentItem}
                onClick={() => navigate(`/tasks/${t.task_id}`)}>
                <span className={styles.recentId}>#{t.task_id}</span>
                <StatusBadge phase={t.phase} />
                <span className={styles.recentReq}>
                  {t.requirement.slice(0, 45)}{t.requirement.length > 45 ? "…" : ""}
                </span>
                <span className={styles.recentTime}>{fmtTime(t.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}
