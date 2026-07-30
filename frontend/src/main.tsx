import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  :root {
    /* ── 背景 ── */
    --bg-root: #F5F9F8;
    --bg-surface: #EDF4F2;
    --bg-card: #FFFFFF;
    --bg-card-hover: #F7FBFA;
    --bg-input: #F7FBFA;

    /* ── 边框 ── */
    --border-subtle: #E2EEEB;
    --border-default: #D0E0DC;
    --border-strong: #B8CFC9;

    /* ── 文字 ── */
    --text-primary: #1F2A2E;
    --text-secondary: #6B7B7A;
    --text-muted: #9AAAA8;

    /* ── 强调色 ── */
    --accent: #2FD98A;
    --accent-strong: #22C57A;
    --accent-subtle: rgba(47, 217, 138, 0.08);
    --accent-glow: rgba(47, 217, 138, 0.2);

    /* ── 次强调色（天蓝） ── */
    --blue: #5B8DEF;
    --blue-subtle: rgba(91, 141, 239, 0.08);
    --blue-glow: rgba(91, 141, 239, 0.15);

    /* ── 语义色 ── */
    --success: #2FD98A;
    --success-subtle: rgba(47, 217, 138, 0.08);
    --danger: #F0556B;
    --danger-subtle: rgba(240, 85, 107, 0.08);
    --warning: #F5A623;
    --warning-subtle: rgba(245, 166, 35, 0.08);

    /* ── 圆角 ── */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;

    /* ── 阴影 ── */
    --shadow-xs: 0 1px 2px rgba(31, 42, 46, 0.04);
    --shadow-sm: 0 2px 8px rgba(31, 42, 46, 0.06);
    --shadow-md: 0 8px 24px rgba(31, 42, 46, 0.08);
    --shadow-lg: 0 16px 40px rgba(31, 42, 46, 0.1);

    /* ── 字体 ── */
    --font-brand: "Plus Jakarta Sans", sans-serif;
    --font-ui: "Inter", sans-serif;
    --font-mono: "JetBrains Mono", monospace;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--font-ui);
    background: var(--bg-root);
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
  }

  a { color: var(--blue); text-decoration: none; }
  code, pre, .mono {
    font-family: var(--font-mono);
    font-size: 0.9em;
  }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
