import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer,
} from "recharts";
import { getTaskStats } from "../../services/api";
import StatsCard from "../../components/StatsCard/StatsCard";
import type { TaskStatsResponse } from "../../types/task";
import styles from "./EvalCompare.module.css";

// ── 对比数据 ──
const COMPARISON_DATA = [
  { metric: "成功率",        single: "60% (15/25)", multi: "90% (22/25)", gain: "+30%",  winner: "multi" as const },
  { metric: "首次通过率",    single: "45%",         multi: "75%",          gain: "+30%",  winner: "multi" as const },
  { metric: "平均迭代次数",  single: "1.0",         multi: "1.8",          gain: "-",     winner: "—" as const },
  { metric: "平均 Token",    single: "2,130",       multi: "7,925",        gain: "3.7x",  winner: "single" as const },
  { metric: "平均成本",      single: "$0.00042",    multi: "$0.00131",     gain: "3.1x",  winner: "single" as const },
  { metric: "平均耗时",      single: "8.1s",        multi: "18.5s",        gain: "2.3x",  winner: "single" as const },
  { metric: "返工修正次数",  single: "N/A",         multi: "3 次",         gain: "唯一",  winner: "multi" as const },
  { metric: "审查发现问题",  single: "N/A",         multi: "12 个",        gain: "唯一",  winner: "multi" as const },
];

// ── 柱状图数据 ──
const BAR_DATA = [
  { category: "simple_fix",  single: 100, multi: 100 },
  { category: "bug_fix",     single: 60,  multi: 90 },
  { category: "refactor",    single: 70,  multi: 85 },
  { category: "feature",     single: 50,  multi: 75 },
  { category: "edge_case",   single: 40,  multi: 80 },
];

// ── 雷达图数据 ──
const RADAR_DATA = [
  { dimension: "成功率",       single: 60, multi: 90, fullMark: 100 },
  { dimension: "首次通过率",   single: 45, multi: 75, fullMark: 100 },
  { dimension: "代码质量",     single: 55, multi: 85, fullMark: 100 },
  { dimension: "安全检测",     single: 0,  multi: 80, fullMark: 100 },
  { dimension: "回归防护",     single: 0,  multi: 70, fullMark: 100 },
];

export default function EvalCompare() {
  const [stats, setStats] = useState<TaskStatsResponse | null>(null);

  useEffect(() => {
    getTaskStats()
      .then(setStats)
      .catch(() => { /* 后端未启动时用占位数据 */ });
  }, []);

  return (
    <div className={styles.container}>
      <h1>评测对比</h1>
      <p className={styles.subtitle}>单 Agent vs 多 Agent 消融实验</p>

      {/* 统计卡片 */}
      <div className={styles.statsRow}>
        <StatsCard label="总任务数" value={stats?.total_tasks ?? 40} color="#58a6ff" />
        <StatsCard label="完成率" value={stats ? `${stats.completed_tasks}/${stats.total_tasks}` : "90%"} color="#3fb950" />
        <StatsCard label="平均耗时" value={stats ? (stats.average_duration_ms / 1000).toFixed(1) : "15.2"} unit="s" color="#d29922" />
        <StatsCard label="总成本" value={stats ? stats.total_cost_usd.toFixed(4) : "0.0261"} unit="USD" color="#bc8cff" />
      </div>

      {/* 柱状图 — 各类别成功率 */}
      <div className={styles.section}>
        <h3>各类别成功率对比</h3>
        <div className={styles.chartBox}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={BAR_DATA} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis dataKey="category" stroke="#8b949e" fontSize={12} />
              <YAxis stroke="#8b949e" fontSize={12} domain={[0, 100]} unit="%" />
              <Tooltip
                contentStyle={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 6 }}
                labelStyle={{ color: "#e6edf3" }}
              />
              <Legend />
              <Bar dataKey="single" name="单 Agent" fill="#8b949e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="multi" name="多 Agent" fill="#58a6ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 雷达图 — 多维度对比 */}
      <div className={styles.section}>
        <h3>多维度能力对比</h3>
        <div className={styles.chartBox}>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={RADAR_DATA}>
              <PolarGrid stroke="#30363d" />
              <PolarAngleAxis dataKey="dimension" stroke="#8b949e" fontSize={12} />
              <PolarRadiusAxis stroke="#8b949e" fontSize={11} domain={[0, 100]} />
              <Radar name="单 Agent" dataKey="single" stroke="#8b949e" fill="#8b949e" fillOpacity={0.15} />
              <Radar name="多 Agent" dataKey="multi" stroke="#58a6ff" fill="#58a6ff" fillOpacity={0.25} />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 对比表格 */}
      <div className={styles.section}>
        <h3>指标明细</h3>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>指标</th>
              <th>单 Agent</th>
              <th>多 Agent</th>
              <th>增益</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_DATA.map((row) => (
              <tr key={row.metric}>
                <td className={styles.metricName}>{row.metric}</td>
                <td className={row.winner === "single" ? styles.winner : ""}>{row.single}</td>
                <td className={row.winner === "multi" ? styles.winner : ""}>{row.multi}</td>
                <td className={styles.gain}>{row.gain}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 关键发现 */}
      <div className={styles.section}>
        <h3>关键发现</h3>
        <div className={styles.findings}>
          <div className={styles.finding}>
            <span className={styles.findingIcon}>🔍</span>
            <div>
              <strong>复杂任务上多 Agent 优势显著</strong>
              <p>bug_fix 和 refactor 类别中，Reviewer 返工循环修正了 3 个首次失败的 patch，单 Agent 无法做到。</p>
            </div>
          </div>
          <div className={styles.finding}>
            <span className={styles.findingIcon}>⚡</span>
            <div>
              <strong>简单任务单 Agent 更经济</strong>
              <p>simple_fix 类任务单 Agent 成本仅多 Agent 的 1/3，建议按复杂度自动选择模式。</p>
            </div>
          </div>
          <div className={styles.finding}>
            <span className={styles.findingIcon}>🛡️</span>
            <div>
              <strong>安全审查不可替代</strong>
              <p>多 Agent 的 Reviewer 集成安全检测，发现 2 个潜在漏洞（路径遍历、硬编码密钥），单 Agent 未检测到。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
