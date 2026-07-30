import { NavLink } from "react-router-dom";
import { Zap, PlusCircle, BarChart3 } from "lucide-react";
import styles from "./Layout.module.css";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.wrapper}>
      <nav className={styles.nav}>
        <NavLink to="/" className={styles.brand}>
          <div className={styles.logoBox}>
            <Zap size={16} className={styles.logoIcon} />
          </div>
          <span className={styles.title}>DevFlow</span>
          <span className={styles.subtitle}>Multi-Agent Platform</span>
        </NavLink>
        <div className={styles.links}>
          <NavLink
            to="/"
            end
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
          >
            <PlusCircle size={15} />
            创建任务
          </NavLink>
          <NavLink
            to="/eval"
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
          >
            <BarChart3 size={15} />
            评测对比
          </NavLink>
        </div>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
