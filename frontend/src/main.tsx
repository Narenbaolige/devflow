import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const style = document.createElement("style");
style.textContent = `
  :root {
    /* ── 冷凝玻璃背景（灰阶垂直渐变） ── */
    --bg-gradient: linear-gradient(180deg,
      #E8E9EA 0%, #C9CDCF 25%, #9BA0A3 45%,
      #6B7073 65%, #3A3D40 85%, #1C1E20 100%
    );

    /* ── 卡片玻璃 ── */
    --glass-bg: rgba(255,255,255,0.75);
    --glass-border: rgba(255,255,255,0.5);
    --glass-blur: 16px;
    --glass-shadow: 0 8px 24px rgba(20,22,24,0.12);

    /* ── 高可读性卡片（详情页 diff/测试/时间线） ── */
    --glass-bg-solid: rgba(255,255,255,0.87);
    --glass-blur-solid: 12px;

    /* ── 输入框 ── */
    --input-bg: rgba(255,255,255,0.65);
    --input-border: rgba(0,0,0,0.1);

    /* ── 边框 ── */
    --border-subtle: rgba(0,0,0,0.06);
    --border-default: rgba(0,0,0,0.1);
    --border-strong: rgba(0,0,0,0.16);

    /* ── 文字（深灰，保证对比度） ── */
    --text-primary: #1A1E20;
    --text-secondary: #3E4447;
    --text-muted: #6B7175;

    /* ── 状态色（在灰阶背景上醒目） ── */
    --accent: #2FAE73;
    --accent-strong: #259B63;
    --accent-subtle: rgba(47,174,115,0.1);

    --blue: #3E8EDE;
    --blue-subtle: rgba(62,142,222,0.1);

    --success: #2FAE73;
    --success-subtle: rgba(47,174,115,0.1);
    --danger: #E0576B;
    --danger-subtle: rgba(224,87,107,0.1);
    --warning: #E0A339;
    --warning-subtle: rgba(224,163,57,0.1);

    /* ── 圆角/阴影 ── */
    --radius-sm: 12px;
    --radius-md: 14px;
    --radius-lg: 18px;
    --shadow-sm: 0 4px 16px rgba(20,22,24,0.08);
    --shadow-md: 0 8px 24px rgba(20,22,24,0.14);

    /* ── 字体 ── */
    --font-brand: "Plus Jakarta Sans", sans-serif;
    --font-ui: "Inter", sans-serif;
    --font-mono: "JetBrains Mono", monospace;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--font-ui);
    background: var(--bg-gradient);
    background-attachment: fixed;
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    position: relative; overflow-x: hidden;
  }

  /* SVG 玻璃扭曲滤镜层 */
  #root {
    position: relative; z-index: 2;
  }

  a { color: var(--blue); text-decoration: none; }
  code, pre, .mono { font-family: var(--font-mono); font-size: 0.9em; }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }

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
