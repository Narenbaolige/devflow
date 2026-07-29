import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { createTask, listTasks } from "../../services/api";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import type { TaskResponse } from "../../types/task";
import styles from "./TaskCreate.module.css";

const DEFAULT_VALUES = {
  repo_url: "https://github.com/example/demo-repo",
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
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskResponse[]>([]);

  // Load recent tasks
  useEffect(() => {
    listTasks(5, 0)
      .then((res) => setRecentTasks(res.tasks))
      .catch(() => { /* ignore */ });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requirement.trim()) { setError("请输入需求描述"); return; }
    if (!repoUrl.trim()) { setError("请输入仓库 URL"); return; }

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
      });
      navigate(`/tasks/${task.task_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败，请检查后端");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>创建新任务</h1>
        <p>描述你的需求，系统将自动完成分析 → 规划 → 编码 → 测试 → 审查</p>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label}>需求描述 <span className={styles.required}>*</span></label>
          <textarea className={styles.textarea} value={requirement} onChange={(e) => setRequirement(e.target.value)}
            placeholder="例如：给 factorial 函数添加参数校验" rows={4} disabled={submitting} />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>仓库 URL <span className={styles.required}>*</span></label>
          <input className={styles.input} type="text" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/..." disabled={submitting} />
        </div>

        <details className={styles.advanced}>
          <summary className={styles.advancedTitle}>⚙️ 高级选项</summary>
          <div className={styles.advancedGrid}>
            <div className={styles.field}>
              <label className={styles.label}>目标分支</label>
              <input className={styles.input} type="text" value={branch} onChange={(e) => setBranch(e.target.value)} disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>最大迭代次数</label>
              <input className={styles.input} type="number" min={1} max={10} value={maxIterations} onChange={(e) => setMaxIterations(Number(e.target.value))} disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>超时时间（秒）</label>
              <input className={styles.input} type="number" min={1} max={3600} value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(Number(e.target.value))} disabled={submitting} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>预算上限（美元）</label>
              <input className={styles.input} type="number" min={0} step={0.001} value={budgetLimit} onChange={(e) => setBudgetLimit(e.target.value)} placeholder="不限制" disabled={submitting} />
            </div>
          </div>
        </details>

        {error && <div className={styles.error}>{error}</div>}

        <button className={styles.submitBtn} type="submit" disabled={submitting}>
          {submitting ? <><span className={styles.spinner} />正在创建...</> : "🚀 创建任务"}
        </button>
      </form>

      {/* 最近任务 — 解决导航后找不到之前任务的问题 */}
      {recentTasks.length > 0 && (
        <div className={styles.recentSection}>
          <h3>最近任务</h3>
          <div className={styles.recentList}>
            {recentTasks.map((t) => (
              <div key={t.task_id} className={styles.recentItem} onClick={() => navigate(`/tasks/${t.task_id}`)}>
                <span className={styles.recentId}>#{t.task_id}</span>
                <StatusBadge phase={t.phase} />
                <span className={styles.recentReq}>{t.requirement.slice(0, 40)}{t.requirement.length > 40 ? "..." : ""}</span>
                <span className={styles.recentTime}>{formatTime(t.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}
