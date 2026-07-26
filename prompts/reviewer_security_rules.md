# Reviewer 安全检测规则

> 两周版：Security Agent 合并入 Reviewer。Reviewer 在审查代码时，必须逐项检查以下三类安全问题。

---

## 规则 1：SQL 注入检测 (CWE-89)

### 检测模式

审查所有数据库操作代码，标记以下危险模式：

| 危险模式 | 示例 | 修复 |
|------|------|------|
| 字符串拼接 SQL | `f"SELECT * FROM users WHERE id={uid}"` | 参数化查询 |
| `%` 格式化 SQL | `"SELECT * FROM users WHERE id=%s" % uid` | 参数化查询 |
| `.format()` 拼接 | `"SELECT * FROM users WHERE id={}".format(uid)` | 参数化查询 |
| 裸 `execute()` | `cursor.execute(query)` 其中 `query` 来自变量拼接 | `cursor.execute(query, params)` |

### 安全示例

```python
# 正确：参数化查询
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# 正确：ORM 方式
User.objects.filter(id=user_id)
```

### 判定规则

- 发现字符串拼接/格式化 SQL → `severity: critical`
- 动态表名/列名（可能是业务需要）→ `severity: high`，标注"确认是否来自可信输入"

---

## 规则 2：硬编码密钥检测 (CWE-798)

### 检测模式

搜索以下关键字的赋值语句：

| 关键字 | 示例 |
|------|------|
| `password` | `password = "admin123"` |
| `secret` | `SECRET_KEY = "abc..."` |
| `api_key` | `API_KEY = "sk-..."` |
| `token` | `AUTH_TOKEN = "eyJ..."` |
| `private_key` | `PRIVATE_KEY = "-----BEGIN RSA..."` |
| `connection_string` | `CONN_STR = "mysql://user:pass@host"` |

### 安全示例

```python
# 正确：从环境变量读取
SECRET_KEY = os.environ.get("SECRET_KEY")

# 正确：从配置文件读取（不提交到 Git）
from app.config import settings
api_key = settings.API_KEY
```

### 判定规则

- 密钥/密码/Token 硬编码在源码中 → `severity: critical`
- 连接字符串含密码 → `severity: high`
- 注释中的示例密钥（如 `# SECRET_KEY = "your-key-here"`）→ `severity: low`（提示）

---

## 规则 3：路径遍历检测 (CWE-22)

### 检测模式

审查所有文件操作代码，标记以下危险模式：

| 危险模式 | 示例 |
|------|------|
| 用户输入直接拼接路径 | `open(f"/data/{user_input}")` |
| `os.path.join` 含用户输入 | `os.path.join(base, request.args.get("file"))` |
| 未校验的 `..` 穿越 | `Path(base) / user_path` 其中 user_path 含 `../` |
| 压缩包解压未校验 | `zipfile.extractall()` 无路径检查 |

### 安全示例

```python
# 正确：校验后使用
resolved = os.path.realpath(os.path.join(base_dir, user_file))
if not resolved.startswith(os.path.realpath(base_dir)):
    raise ValueError("路径穿越检测")

# 正确：白名单
ALLOWED_FILES = {"a.txt", "b.txt"}
if filename not in ALLOWED_FILES:
    raise ValueError("非法文件")
```

### 判定规则

- 用户输入直接控制文件路径且无校验 → `severity: critical`
- 有部分校验但可绕过 → `severity: high`
- zip/tar 解压未做路径检查 → `severity: major`

---

## 严重程度速查

| severity | 含义 | 是否阻断通过 |
|------|------|:--:|
| `critical` | 可直接利用的安全漏洞 | ✅ 阻断 |
| `high` | 高风险，很可能被利用 | ✅ 阻断 |
| `major` | 中等风险，需要修复 | ❌ 不阻断 |
| `minor` | 低风险，建议修复 | ❌ 不阻断 |
| `suggestion` | 最佳实践建议 | ❌ 不阻断 |

**阻断规则**：存在任何 `critical` 或 ≥1 个 `high` → `passed=False`。
