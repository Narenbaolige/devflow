import styles from "./StatusBadge.module.css";
import { PHASE_CONFIG } from "../../types/task";
import type { Phase } from "../../types/task";

interface Props {
  phase: Phase;
}

export default function StatusBadge({ phase }: Props) {
  const config = PHASE_CONFIG[phase] ?? { label: phase, color: "#8b949e" };
  return (
    <span className={styles.badge} style={{ "--badge-color": config.color } as React.CSSProperties}>
      {config.label}
    </span>
  );
}
