import { NavLink } from "react-router-dom";
import styles from "./Layout.module.css";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.wrapper}>
      <nav className={styles.nav}>
        <div className={styles.brand}>
          <div className={styles.logo}>⚡</div>
          <span className={styles.title}>DevFlow</span>
          <span className={styles.subtitle}>Multi-Agent Platform</span>
        </div>
        <div className={styles.links}>
          <NavLink
            to="/"
            end
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
          >
            创建任务
          </NavLink>
          <NavLink
            to="/eval"
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
          >
            评测对比
          </NavLink>
        </div>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
