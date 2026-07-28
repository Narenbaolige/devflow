import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// 全局重置样式
const style = document.createElement("style");
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #0d1117;
    color: #e6edf3;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  a { color: #58a6ff; }
  code, pre, .mono { font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace; }
`;
document.head.appendChild(style);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
