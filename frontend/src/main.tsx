import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  :root {
    /* ── 雨夜背景 ── */
    --bg-root: #0f1620;
    --bg-gradient: linear-gradient(170deg, #1a2332 0%, #141d2a 40%, #0f1620 100%);

    /* ── 实色表面（详情页卡片/图表容器） ── */
    --bg-solid: #161f2b;
    --bg-solid-hover: #1b2634;
    --bg-input: #111923;

    /* ── 玻璃表面（导航栏/创建页卡片） ── */
    --glass-bg: rgba(255,255,255,0.05);
    --glass-border: rgba(255,255,255,0.1);
    --glass-blur: 14px;

    /* ── 边框 ── */
    --border-subtle: rgba(255,255,255,0.06);
    --border-default: rgba(255,255,255,0.1);
    --border-strong: rgba(255,255,255,0.16);

    /* ── 文字（高对比度） ── */
    --text-primary: #E8EDF2;
    --text-secondary: #9BA7B5;
    --text-muted: #6B7887;

    /* ── 强调色 ── */
    --accent: #3EE8A0;
    --accent-strong: #5CF0B4;
    --accent-subtle: rgba(62,232,160,0.1);
    --accent-glow: rgba(62,232,160,0.18);

    /* ── 次强调色 ── */
    --blue: #6BA4F8;
    --blue-subtle: rgba(107,164,248,0.1);

    /* ── 语义色（保持鲜明） ── */
    --success: #3EE8A0;
    --success-subtle: rgba(62,232,160,0.12);
    --danger: #F0626E;
    --danger-subtle: rgba(240,98,110,0.12);
    --warning: #F5B642;
    --warning-subtle: rgba(245,182,66,0.12);

    /* ── 圆角/阴影 ── */
    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 18px;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
    --shadow-md: 0 8px 24px rgba(0,0,0,0.4);

    /* ── 字体 ── */
    --font-brand: "Plus Jakarta Sans", sans-serif;
    --font-ui: "Inter", sans-serif;
    --font-mono: "JetBrains Mono", monospace;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--font-ui);
    background: var(--bg-root);
    background-image: var(--bg-gradient);
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
  }

  /* 柔光色块 — 模拟雨夜路灯 */
  body::before {
    content: "";
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 60% 50% at 20% 30%, rgba(120,140,220,0.06), transparent),
      radial-gradient(ellipse 50% 40% at 75% 70%, rgba(180,140,220,0.05), transparent);
  }

  a { color: var(--blue); text-decoration: none; }
  code, pre, .mono { font-family: var(--font-mono); font-size: 0.9em; }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.14); }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
