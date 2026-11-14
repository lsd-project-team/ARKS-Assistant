# 任务：单页任务看板（原生 HTML/CSS/JS，无框架）

在工作区从零实现一个小型任务看板：

1. `index.html`：输入框、添加按钮、任务列表、全部/未完成/已完成筛选、剩余计数；以 `type="module"` 引入 `app.js`。
2. `logic.mjs`（ES module）导出纯函数：
   - `addTask(tasks, title)`：trim 标题，空标题抛错；返回新数组，任务形如 `{id, title, done:false}`，id 唯一。
   - `toggleTask(tasks, id)`：返回新数组，目标 `done` 取反；id 不存在时原样返回。
   - `filterTasks(tasks, mode)`：`all`/`active`/`done`。
   - `formatTime(seconds)`：`mm:ss`；负数抛错。
3. `app.js`（module）绑定 DOM 与 localStorage；`styles.css` 提供基本样式。
4. `package.json` 至少包含 `{"type":"module"}`。
5. `tests/logic.test.mjs`：使用 `node:test`，至少 6 个用例（添加、切换、筛选、格式化、空标题、负数）。
6. `README.md`：运行与测试命令。

完成前在 PowerShell 中逐条运行（不要用 `&&` 连接）：
`node --check app.js`、`node --check logic.mjs`、`node --test tests/logic.test.mjs`，全部通过；不要留 TODO/占位。
`index.html`、`app.js`、`styles.css` 三个界面文件必须真实存在，缺一不可。
不要安装 Playwright/浏览器或其它大依赖（验收环境按离线处理，安装会超时）；测试只用 `node:test`。
