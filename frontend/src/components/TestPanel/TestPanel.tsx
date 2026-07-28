import styles from "./TestPanel.module.css";
import type { SandboxResult } from "../../types/task";

interface Props {
  result: SandboxResult;
}

export default function TestPanel({ result }: Props) {
  const summary = result.test_summary;
  if (!summary) {
    return (
      <div className={styles.container}>
        <div className={styles.status}>
          <span className={`${styles.badge} ${styles[result.status]}`}>
            {result.status}
          </span>
          <span>exit code: {result.exit_code}</span>
          <span>耗时: {result.duration_ms}ms</span>
        </div>
        {result.stderr && (
          <pre className={styles.stderr}>{result.stderr}</pre>
        )}
      </div>
    );
  }

  const passRate = summary.total > 0
    ? Math.round((summary.passed / summary.total) * 100)
    : 0;

  return (
    <div className={styles.container}>
      {/* 测试汇总 */}
      <div className={styles.summary}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum} style={{ color: "#e6edf3" }}>{summary.total}</span>
          <span className={styles.summaryLabel}>总计</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum} style={{ color: "#3fb950" }}>{summary.passed}</span>
          <span className={styles.summaryLabel}>通过</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum} style={{ color: "#f85149" }}>{summary.failed}</span>
          <span className={styles.summaryLabel}>失败</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum} style={{ color: "#d29922" }}>{summary.errors}</span>
          <span className={styles.summaryLabel}>错误</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum} style={{ color: "#8b949e" }}>{summary.skipped}</span>
          <span className={styles.summaryLabel}>跳过</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryNum}>{passRate}%</span>
          <span className={styles.summaryLabel}>通过率</span>
        </div>
      </div>

      {/* 进度条 */}
      <div className={styles.progressBar}>
        <div className={styles.progressPass} style={{ width: `${passRate}%` }} />
        <div className={styles.progressFail} style={{ width: `${100 - passRate}%` }} />
      </div>

      {/* 失败详情 */}
      {result.test_failures.length > 0 && (
        <div className={styles.failures}>
          <h4>失败详情 ({result.test_failures.length})</h4>
          {result.test_failures.map((f, i) => (
            <div key={i} className={styles.failureItem}>
              <div className={styles.failureHeader}>
                <span className={styles.failureTest}>{f.test_name}</span>
                <span className={`${styles.failureBadge} ${f.is_new_failure ? styles.newFailure : styles.existingFailure}`}>
                  {f.is_new_failure ? "新引入" : "原有失败"}
                </span>
              </div>
              <div className={styles.failureMsg}>{f.message}</div>
              {f.traceback && (
                <pre className={styles.traceback}>{f.traceback.slice(0, 500)}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
