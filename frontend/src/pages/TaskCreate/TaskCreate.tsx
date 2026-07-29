import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createTask } from "../../services/api";
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requirement.trim()) {
      setError("请输入需求描述");
      return;
    }
    if (!repoUrl.trim()) {
      setError("请输入仓库 URL");
      return;
    }

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
        publish_to_remote: true,
      });
      navigate(`/tasks/${task.task_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败，请检查后端服务是否启动");
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
        {/* 核心字段 */}
        <div className={styles.field}>
          <label className={styles.label}>
            需求描述 <span className={styles.required}>*</span>
          </label>
          <textarea
            className={styles.textarea}
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            placeholder='例如：给 factorial 函数添加参数校验，输入为负数时抛出 ValueError'
            rows={4}
            disabled={submitting}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>
            仓库 URL <span className={styles.required}>*</span>
          </label>
          <input
            className={styles.input}
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/..."
            disabled={submitting}
          />
        </div>

        {/* 高级选项 */}
        <details className={styles.advanced}>
          <summary className={styles.advancedTitle}>⚙️ 高级选项</summary>
          <div className={styles.advancedGrid}>
            <div className={styles.field}>
              <label className={styles.label}>目标分支</label>
              <input
                className={styles.input}
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>最大迭代次数</label>
              <input
                className={styles.input}
                type="number"
                min={1}
                max={10}
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                disabled={submitting}
              />
              <span className={styles.hint}>测试失败时最多返工 3 次</span>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>超时时间（秒）</label>
              <input
                className={styles.input}
                type="number"
                min={1}
                max={3600}
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                disabled={submitting}
              />
              <span className={styles.hint}>默认 900 秒（15 分钟）</span>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>预算上限（美元）</label>
              <input
                className={styles.input}
                type="number"
                min={0}
                step={0.001}
                value={budgetLimit}
                onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder="不限制"
                disabled={submitting}
              />
              <span className={styles.hint}>留空表示不限制 LLM 调用费用</span>
            </div>
          </div>
        </details>

        {error && <div className={styles.error}>{error}</div>}

        <button className={styles.submitBtn} type="submit" disabled={submitting}>
          {submitting ? (
            <>
              <span className={styles.spinner} />
              正在创建...
            </>
          ) : (
            "🚀 创建任务"
          )}
        </button>
      </form>
    </div>
  );
}
