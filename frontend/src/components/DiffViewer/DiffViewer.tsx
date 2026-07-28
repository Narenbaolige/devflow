import styles from "./DiffViewer.module.css";
import type { PatchResult } from "../../types/task";

interface Props {
  patch: PatchResult;
}

/**
 * Unified Diff 解析与高亮展示。
 * 支持 diff 字符串解析，红删绿增，side-by-side 可选。
 */
export default function DiffViewer({ patch }: Props) {
  const lines = parseDiffLines(patch.diff);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.filePath}>{patch.file_path}</span>
        <span className={`${styles.changeType} ${styles[patch.change_type]}`}>
          {patch.change_type}
        </span>
      </div>
      <div className={styles.description}>{patch.change_description}</div>
      <div className={styles.diffBox}>
        {lines.length === 0 ? (
          <pre className={styles.noDiff}>{patch.diff || "(无 diff 内容)"}</pre>
        ) : (
          <table className={styles.diffTable}>
            <tbody>
              {lines.map((line, i) => (
                <tr
                  key={i}
                  className={`${styles.diffLine} ${line.type === "add" ? styles.addLine : ""} ${line.type === "del" ? styles.delLine : ""} ${line.type === "header" ? styles.headerLine : ""}`}
                >
                  <td className={styles.lineNum}>{line.oldNum}</td>
                  <td className={styles.lineNum}>{line.newNum}</td>
                  <td className={styles.lineMarker}>
                    {line.type === "add" ? "+" : line.type === "del" ? "-" : " "}
                  </td>
                  <td className={styles.lineContent}>{line.content}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

interface DiffLine {
  type: "add" | "del" | "header" | "normal";
  oldNum: string;
  newNum: string;
  content: string;
}

function parseDiffLines(diff: string): DiffLine[] {
  if (!diff) return [];
  const rawLines = diff.split("\n");
  const result: DiffLine[] = [];
  let oldNum = 0;
  let newNum = 0;

  for (const line of rawLines) {
    if (line.startsWith("@@")) {
      result.push({ type: "header", oldNum: "", newNum: "", content: line });
      const match = line.match(/@@ -(\d+),\d+ \+(\d+),\d+ @@/);
      if (match) {
        oldNum = parseInt(match[1]) - 1;
        newNum = parseInt(match[2]) - 1;
      }
    } else if (line.startsWith("+")) {
      newNum++;
      result.push({ type: "add", oldNum: "", newNum: String(newNum), content: line });
    } else if (line.startsWith("-")) {
      oldNum++;
      result.push({ type: "del", oldNum: String(oldNum), newNum: "", content: line });
    } else {
      oldNum++;
      newNum++;
      result.push({
        type: "normal",
        oldNum: String(oldNum),
        newNum: String(newNum),
        content: line,
      });
    }
  }
  return result;
}
