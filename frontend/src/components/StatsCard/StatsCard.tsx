import styles from "./StatsCard.module.css";

interface Props {
  label: string;
  value: string | number;
  unit?: string;
}

export default function StatsCard({ label, value, unit = "" }: Props) {
  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>
        {value}
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>
    </div>
  );
}
