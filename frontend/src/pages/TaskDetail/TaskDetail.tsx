import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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

  // ── 离线提示 ──
  if (!online) {
    return (
      <div className={styles.center}>
        <div className={styles.errorIcon}>🔌</div>
        <h2>网络已断开</h2>
        <p className={styles.errorMsg}>请检查网络连接后刷新页面</p>
      </div>
    );
  }

  // ── 加载态 ──
  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.loadingSpinner} />
        <p>加载任务中...</p>
      </div>
    );
  }

  // ── 错误态 ──
  if (error || !task) {
    return (
      <div className={styles.center}>
        <div className={styles.errorIcon}>⚠️</div>
        <h2>无法加载任务</h2>
        <p className={styles.errorMsg}>{error || "任务不存在"}</p>
        <div className={styles.retryRow}>
          <button className={styles.backBtn} onClick={() => navigate("/")}>
            返回创建页
          </button>
          <button className={styles.retryBtn} onClick={refetch}>
            🔄 重试
          </button>
        </div>
      </div>
    );
  }

  // ── 提取产出物 ──
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
      {/* 顶部栏 */}
      <div className={styles.topBar}>
        <button className={styles.backLink} onClick={() => navigate("/")}>
          ← 返回
        </button>
        <div className={styles.taskId}>任务 #{task.task_id}</div>
        <StatusBadge phase={task.phase} />
        {!isTerminal && (
          <button
            className={styles.cancelBtn}
            onClick={handleCancel}
            disabled={cancelling}
          >
            {cancelling ? "取消中..." : "取消任务"}
          </button>
        )}
      </div>

      {/* 统计卡片 */}
      <div className={styles.statsRow}>
        <StatsCard label="迭代次数" value={`${task.iteration}`} />
        <StatsCard label="LLM 费用" value={task.budget_used_usd.toFixed(4)} unit="USD" color="#d29922" />
        <StatsCard label="需求" value={task.requirement.length > 40 ? task.requirement.slice(0, 40) + "..." : task.requirement} />
        <StatsCard label="仓库" value={task.repo_url.split("/").pop() || task.repo_url} />
      </div>

      {/* 双栏布局 */}
      <div className={styles.twoCol}>
        {/* 左侧：进度面板 */}
        <div className={styles.leftPanel}>
          <h3 className={styles.panelTitle}>执行进度</h3>
          <div className={styles.nodeList}>
            {WORKFLOW_NODES.map((node) => {
              const isCompleted = completedNodes.has(node.key);
              const isCurrent = task.current_node === node.key;
              return (
                <div
                  key={node.key}
                  className={`${styles.nodeItem} ${isCompleted ? styles.nodeDone : ""} ${isCurrent ? styles.nodeActive : ""}`}
                >
                  <span className={styles.nodeIcon}>
                    {isCompleted ? "✅" : isCurrent ? "🔄" : node.icon}
                  </span>
                  <span className={styles.nodeLabel}>{node.label}</span>
                  {isCurrent && <span className={styles.currentBadge}>进行中</span>}
                </div>
              );
            })}
          </div>

          {/* 时间线 */}
          <Timeline events={events} />

          {/* 错误信息 */}
          {task.errors.length > 0 && (
            <div className={styles.errorSection}>
              <h4>⚠️ 错误 ({task.errors.length})</h4>
              {task.errors.map((err, i) => (
                <div key={i} className={styles.errorItem}>
                  <strong>{err.node}</strong>: {err.message}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 右侧：产出物展示 */}
        <div className={styles.rightPanel}>
          {/* 审批面板 */}
          {task.phase === "awaiting_approval" && taskId && (
            <ApprovalPanel taskId={taskId} />
          )}

          {/* Diff 展示 */}
          {patches.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.panelTitle}>📝 代码修改</h3>
              {patches.map((p, i) => (
                <DiffViewer key={i} patch={p} />
              ))}
            </div>
          )}

          {/* 测试结果 */}
          {sandboxResults.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.panelTitle}>🧪 测试结果</h3>
              {sandboxResults.map((r, i) => (
                <TestPanel key={i} result={r} />
              ))}
            </div>
          )}

          {/* 空态提示 */}
          {!isTerminal && patches.length === 0 && sandboxResults.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>⏳</div>
              <p>等待 Agent 产出结果...</p>
              <p className={styles.emptyHint}>节点完成后，Diff 和测试结果将显示在这里</p>
            </div>
          )}

          {/* 已完成 */}
          {task.publication && (
            <div className={`${styles.section} ${task.publication.status === "pushed" ? styles.successBox : styles.publishError}`}>
              <h3>{task.publication.status === "pushed" ? "已推送到远程仓库" : "远程发布失败"}</h3>
              {Boolean(task.publication.branch) && <p>分支：{String(task.publication.branch)}</p>}
              {Boolean(task.publication.error) && <p>{String(task.publication.error)}</p>}
            </div>
          )}

          {task.phase === "done" && (
            <div className={`${styles.section} ${styles.successBox}`}>
              <h3>✅ 任务完成</h3>
              <p>所有测试通过，代码修改已完成。</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
