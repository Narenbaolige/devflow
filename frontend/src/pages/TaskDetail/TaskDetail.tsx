import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw, XCircle, WifiOff, CheckCircle2 } from "lucide-react";
import { useTaskPolling } from "../../hooks/useTaskPolling";
import { useTaskSSE } from "../../hooks/useTaskSSE";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useToast } from "../../components/Toast/ToastContext";
import { cancelTask } from "../../services/api";
import StatusBadge from "../../components/StatusBadge/StatusBadge";
import StatsCard from "../../components/StatsCard/StatsCard";
import DiffViewer from "../../components/DiffViewer/DiffViewer";
import TestPanel from "../../components/TestPanel/TestPanel";
import Timeline from "../../components/Timeline/Timeline";
import ApprovalPanel from "../../components/ApprovalPanel/ApprovalPanel";
import { WORKFLOW_NODES } from "../../types/task";
import type { SandboxResult, PatchResult } from "../../types/task";
import styles from "./TaskDetail.module.css";

const NODE_ICONS: Record<string, string> = {
  init_task: "○",
  analyze_requirement: "①",
  create_plan: "②",
  develop_changes: "③",
  run_tests: "④",
  review_changes: "⑤",
  security_check: "⑥",
  await_approval: "⑦",
};

export default function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { task, loading, error, refetch } = useTaskPolling(taskId);
  const { events } = useTaskSSE(taskId);
  const online = useNetworkStatus();
  const { error: showError, success: showSuccess } = useToast();
  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    if (!taskId || cancelling) return;
    setCancelling(true);
    try {
      await cancelTask(taskId);
      showSuccess("任务已取消");
    } catch (err) {
      showError("取消失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setCancelling(false);
    }
  };

  if (!online) {
    return (
      <div className={styles.center}>
        <WifiOff size={40} className={styles.centerIcon} />
        <h2>网络已断开</h2>
        <p className={styles.errorMsg}>请检查网络连接后刷新页面</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.loadingSpinner} />
        <p>加载任务中...</p>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className={styles.center}>
        <div className={styles.centerIconMuted}>!</div>
        <h2>无法加载任务</h2>
        <p className={styles.errorMsg}>{error || "任务不存在"}</p>
        <div className={styles.retryRow}>
          <button className={styles.backBtn} onClick={() => navigate("/")}>
            <ArrowLeft size={14} /> 返回
          </button>
          <button className={styles.retryBtn} onClick={refetch}>
            <RefreshCw size={14} /> 重试
          </button>
        </div>
      </div>
    );
  }

  const completedNodes = new Set(events.map((e) => e.node_name));
  const sandboxResults = events
    .filter((e) => e.event_type === "test_result")
    .map((e) => e.data as unknown as SandboxResult);
  const patches = events
    .filter((e) => e.event_type === "patch_generated")
    .map((e) => e.data as unknown as PatchResult);
  const isTerminal = ["done", "failed", "cancelled"].includes(task.phase);

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <button className={styles.backLink} onClick={() => navigate("/")}>
          <ArrowLeft size={15} /> 返回
        </button>
        <div className={styles.taskId}>#{task.task_id}</div>
        <StatusBadge phase={task.phase} />
        {!isTerminal && (
          <button className={styles.cancelBtn} onClick={handleCancel} disabled={cancelling}>
            <XCircle size={14} />
            {cancelling ? "取消中..." : "取消任务"}
          </button>
        )}
      </div>

      <div className={styles.statsRow}>
        <StatsCard label="迭代次数" value={`${task.iteration}`} />
        <StatsCard label="需求" value={task.requirement.length > 40 ? task.requirement.slice(0, 40) + "…" : task.requirement} />
        <StatsCard label="仓库" value={task.repo_url.split("/").pop() || task.repo_url} />
      </div>

      <div className={styles.twoCol}>
        <div className={styles.leftPanel}>
          <h3 className={styles.panelTitle}>执行进度</h3>
          <div className={styles.nodeList}>
            {WORKFLOW_NODES.map((node) => {
              const isCompleted = completedNodes.has(node.key);
              const isCurrent = task.current_node === node.key;
              return (
                <div key={node.key}
                  className={`${styles.nodeItem} ${isCompleted ? styles.nodeDone : ""} ${isCurrent ? styles.nodeActive : ""}`}>
                  <span className={styles.nodeStep}>{NODE_ICONS[node.key] || node.key[0]}</span>
                  <span className={styles.nodeLabel}>{node.label}</span>
                  {isCurrent && <span className={styles.currentBadge}>进行中</span>}
                  {isCompleted && <CheckCircle2 size={13} className={styles.nodeCheck} />}
                </div>
              );
            })}
          </div>
          <Timeline events={events} />
          {task.errors.length > 0 && (
            <div className={styles.errorSection}>
              <h4>错误 ({task.errors.length})</h4>
              {task.errors.map((err, i) => (
                <div key={i} className={styles.errorItem}>
                  <strong>{err.node}</strong>: {err.message}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={styles.rightPanel}>
          {task.phase === "awaiting_approval" && taskId && <ApprovalPanel taskId={taskId} />}

          {patches.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.panelTitle}>代码修改</h3>
              {patches.map((p, i) => <DiffViewer key={i} patch={p} />)}
            </div>
          )}

          {sandboxResults.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.panelTitle}>测试结果</h3>
              {sandboxResults.map((r, i) => <TestPanel key={i} result={r} />)}
            </div>
          )}

          {!isTerminal && patches.length === 0 && sandboxResults.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>...</div>
              <p>等待 Agent 产出结果...</p>
              <p className={styles.emptyHint}>节点完成后，Diff 和测试结果将显示在这里</p>
            </div>
          )}

          {task.publication && task.publication.status === "pushed" && (
            <div className={`${styles.section} ${styles.successBox}`}>
              <h3>已推送到远程仓库</h3>
              {Boolean(task.publication.branch) && <p>分支：{String(task.publication.branch)}</p>}
            </div>
          )}
          {task.publication && task.publication.status === "skipped" && (
            <div className={`${styles.section} ${styles.publishError}`}>
              <h3>推送跳过</h3>
              <p>{String(task.publication.error || "未知原因")}</p>
            </div>
          )}

          {task.phase === "done" && (
            <div className={`${styles.section} ${styles.successBox}`}>
              <h3><CheckCircle2 size={18} style={{verticalAlign:"middle",marginRight:6}} />
                任务完成</h3>
              <p>所有测试通过，代码修改已完成</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
