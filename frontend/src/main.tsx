import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  :root {
    --bg-root: #000000;
    --bg-surface: #0c0c0d;
    --bg-card: #141416;
    --bg-card-hover: #1a1a1d;
    --bg-input: #0f0f10;
    --border-subtle: #1e1e22;
    --border-default: #2a2a30;
    --border-strong: #3a3a42;
    --text-primary: #fafafa;
    --text-secondary: #a0a0a8;
    --text-muted: #6b6b75;
    --accent: #4d94ff;
    --accent-strong: #6aa8ff;
    --accent-subtle: rgba(77, 148, 255, 0.08);
    --accent-glow: rgba(77, 148, 255, 0.15);
    --success: #36c95a;
    --success-subtle: rgba(54, 201, 90, 0.08);
    --danger: #f1464e;
    --danger-subtle: rgba(241, 70, 78, 0.08);
    --warning: #e8a838;
    --warning-subtle: rgba(232, 168, 56, 0.08);
    --purple: #8b6bf7;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.5);
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
    background: var(--bg-root);
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
  }

  a { color: var(--accent); text-decoration: none; }
  code, pre, .mono {
    font-family: "JetBrains Mono", "Fira Code", "SF Mono", "Consolas", monospace;
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
