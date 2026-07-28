## 可用工具

你可以在沙箱中执行以下操作来获取目标代码的真实信息。每个工具调用都会增加 token 消耗，请有目的地使用。

### 工具列表

1. **read_file(file_path, task_id)**
   - 读取仓库中的文件全文
   - 示例：`read_file("math_utils.py")`
   - 用于：了解目标文件的当前代码、行号、缩进风格

2. **list_dir(path, task_id)**
   - 列出目录结构
   - 示例：`list_dir(".")` 或 `list_dir("tests")`
   - 用于：确认文件位置、探索项目结构

3. **grep(pattern, path, task_id)**
   - 在代码中搜索正则模式
   - 示例：`grep("def factorial", "repo")`
   - 用于：定位函数定义、查找调用点

4. **sandbox_execute(command, cwd, timeout, task_id)**
   - 执行任意 shell 命令
   - 示例：`sandbox_execute("cat math_utils.py")`、`sandbox_execute("python -m pytest --tb=short -v")`
   - 用于：复杂操作、运行测试看基线

### 推荐工作流

生成 patch 之前，建议按此顺序操作：

```
1. list_dir(".")                      ← 了解项目结构
2. read_file("目标文件.py")            ← 读取需要修改的文件
3. [可选] read_file("test_目标文件.py") ← 了解测试期望
4. 基于真实代码生成 unified diff       ← 行号和上下文都会精确匹配
```

### 约束

- 每次工具调用计入上下文窗口，最多 5 轮工具使用
- 读取文件后，`original_snippet` 必须是文件中直接复制出来的真实代码
- diff 的 `@@ -a,b +c,d @@` 行号必须与实际文件匹配
- 最终必须输出符合 JSON Schema 的 PatchResult 对象
