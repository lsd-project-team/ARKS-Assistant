# 任务：Python CSV → JSON 命令行工具

在工作区从零实现一个命令行工具 `csvjson.py`：

1. 用法：`python csvjson.py <输入.csv> <输出.json> [--indent N]`
2. 读取带表头的 CSV，输出 JSON 数组；每行一个对象，键为表头。
3. 支持引号包裹的逗号、空字段、CRLF/LF；空文件输出 `[]`。
4. `--indent` 控制缩进（默认 2）；参数缺失或文件不存在时向 stderr 报错并返回退出码 2。
5. 写 `tests/test_csvjson.py`（pytest，至少 5 个用例：基础转换、引号逗号、空文件、缺文件退出码、indent）。
6. 写 README.md（用法与示例）。

完成前运行 `python -m compileall -q .` 与 `python -m pytest -q`，两项都通过；不要留 TODO/占位。
