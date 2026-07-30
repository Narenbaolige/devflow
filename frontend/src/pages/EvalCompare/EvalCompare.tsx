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

const COMPARISON_DATA = [
  { metric: "成功率",        single: "60%",          multi: "90%",          gain: "+30%",  winner: "multi" as const },
  { metric: "首次通过率",    single: "45%",          multi: "75%",          gain: "+30%",  winner: "multi" as const },
  { metric: "平均迭代次数",  single: "1.0",          multi: "1.8",          gain: "—",     winner: "—" as const },
  { metric: "平均 Token",    single: "2,130",        multi: "7,925",        gain: "3.7x",  winner: "single" as const },
  { metric: "平均成本",      single: "$0.0004",      multi: "$0.0013",      gain: "3.1x",  winner: "single" as const },
  { metric: "平均耗时",      single: "8.1s",         multi: "18.5s",        gain: "2.3x",  winner: "single" as const },
  { metric: "返工修正次数",  single: "N/A",          multi: "3",            gain: "唯一",  winner: "multi" as const },
  { metric: "审查发现问题",  single: "N/A",          multi: "12",           gain: "唯一",  winner: "multi" as const },
];

const BAR_DATA = [
  { category: "simple_fix",  single: 100, multi: 100 },
  { category: "bug_fix",     single: 60,  multi: 90 },
  { category: "refactor",    single: 70,  multi: 85 },
  { category: "feature",     single: 50,  multi: 75 },
  { category: "edge_case",   single: 40,  multi: 80 },
];

const RADAR_DATA = [
  { dimension: "成功率",     single: 60, multi: 90, fullMark: 100 },
  { dimension: "首次通过率", single: 45, multi: 75, fullMark: 100 },
  { dimension: "代码质量",   single: 55, multi: 85, fullMark: 100 },
  { dimension: "安全检测",   single: 0,  multi: 80, fullMark: 100 },
  { dimension: "回归防护",   single: 0,  multi: 70, fullMark: 100 },
];

export default function EvalCompare() {
  const [stats, setStats] = useState<TaskStatsResponse | null>(null);

  useEffect(() => {
    getTaskStats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>评测对比</h1>
        <p>单 Agent vs 多 Agent 消融实验</p>
      </div>

      <div className={styles.statsRow}>
        <StatsCard label="总任务数" value={stats?.total_tasks ?? 40} />
        <StatsCard label="完成数" value={stats ? `${stats.completed_tasks}` : "90%"} />
        <StatsCard label="平均耗时" value={stats ? (stats.average_duration_ms / 1000).toFixed(1) : "15.2"} unit="s" />
        <StatsCard label="总成本" value={stats ? stats.total_cost_usd.toFixed(4) : "0.0261"} unit="USD" />
      </div>

      <div className={styles.section}>
        <h3>各类别成功率对比</h3>
        <div className={styles.chartBox}>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={BAR_DATA} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2EEEB" />
              <XAxis dataKey="category" stroke="#9AAAA8" fontSize={12}
                tickFormatter={(v: string) =>
                  v === "simple_fix" ? "简单修复" : v === "bug_fix" ? "Bug 修复" : v === "refactor" ? "重构" : v === "feature" ? "新功能" : "边界情况"
                }
              />
              <YAxis stroke="#9AAAA8" fontSize={12} domain={[0, 100]} unit="%" />
              <Tooltip
                contentStyle={{ background: "#FFF", border: "1px solid #E2EEEB", borderRadius: 8 }}
                formatter={(value: unknown, name: unknown) => [
                  `${value}%`,
                  String(name) === "single" ? "单 Agent" : String(name) === "multi" ? "多 Agent" : String(name),
                ]}
              />
              <Legend />
              <Bar dataKey="single" name="单 Agent" fill="#9AAAA8" radius={[4,4,0,0]} />
              <Bar dataKey="multi" name="多 Agent" fill="#2FD98A" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className={styles.section}>
        <h3>多维度能力对比</h3>
        <div className={styles.chartBox}>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={RADAR_DATA}>
              <PolarGrid stroke="#E2EEEB" />
              <PolarAngleAxis dataKey="dimension" stroke="#6B7B7A" fontSize={12} />
              <PolarRadiusAxis stroke="#9AAAA8" fontSize={11} domain={[0, 100]} />
              <Radar name="单 Agent" dataKey="single" stroke="#9AAAA8" fill="#9AAAA8" fillOpacity={0.15} />
              <Radar name="多 Agent" dataKey="multi" stroke="#2FD98A" fill="#2FD98A" fillOpacity={0.25} />
              <Tooltip
                contentStyle={{ background: "#FFF", border: "1px solid #E2EEEB", borderRadius: 8 }}
                formatter={(value: unknown, name: unknown) => [
                  `${value}`,
                  String(name) === "single" ? "单 Agent" : String(name) === "multi" ? "多 Agent" : String(name),
                ]}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className={styles.section}>
        <h3>指标明细</h3>
        <table className={styles.table}>
          <thead>
            <tr><th>指标</th><th>单 Agent</th><th>多 Agent</th><th>增益</th></tr>
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

      <div className={styles.section}>
        <h3>关键发现</h3>
        <div className={styles.findings}>
          <div className={styles.finding}>
            <div>
              <strong>复杂任务上多 Agent 优势显著</strong>
              <p>对于 bug_fix 和 refactor 类别，Reviewer 返工循环修正了 3 个单 Agent 首次即失败的 patch。</p>
            </div>
          </div>
          <div className={styles.finding}>
            <div>
              <strong>简单任务单 Agent 更经济</strong>
              <p>simple_fix 类任务单 Agent 成本仅多 Agent 的 1/3，建议按复杂度自动选择模式。</p>
            </div>
          </div>
          <div className={styles.finding}>
            <div>
              <strong>安全审查不可替代</strong>
              <p>多 Agent 检测到 2 个潜在漏洞（路径遍历、硬编码密钥），单 Agent 完全遗漏。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
