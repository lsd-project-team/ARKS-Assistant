# Trunk Agent

Windows 本机运行、浏览器访问的源码助手。使用 Deep Agents，支持源码阅读问答、普通聊天、多轮对话、跨会话长期记忆和上下文压缩。

## 启动

已安装 Node.js 22.12+ 与 uv 后，在项目根目录执行：

```powershell
.\Setup.ps1
.\Start.ps1
```

依赖已准备好时可直接双击 `Start.cmd`，默认打开 http://127.0.0.1:8765。`Stop.ps1` 关闭由启动脚本创建的后台服务。应用只监听本机地址。

## 使用

1. 左侧浏览会话并提问；右侧文件树打开 `trunk` 内的源码，支持多标签与文件名筛选。Ctrl+P 可按文件名或路径快速打开，方向键选择、Enter 确认。
2. 在编辑器拖选代码，点击“将选区加入对话”，输入问题。引用包含文件、行列、内容快照和文件版本。
3. 回复中的源码引用可点击定位；工具调用可展开查看。Enter 发送，Shift + Enter 换行。
4. 问答与文件树的分隔线均可拖动或用方向键调整，布局和文件阅读位置自动保存。输入草稿与代码选区按会话保存；切换会话、刷新后恢复。流式回复时向上读历史不会被拉回，点击“回到最新”恢复跟随。
5. 回复可复制；最近完成的回复支持重新生成，原问题、选区与旧版回复保留。失败可重试，停止后可继续，进行中的回复从持久化事件重放。
6. “长期记忆”查看、编辑、删除项目事实和用户偏好，显示更新时间并支持跳转到来源对话。源码变化后，对应记忆标记为需核对。回复旁“上下文”显示本轮实际带入的记忆版本和资料记录。
7. 上下文接近容量时自动压缩；聊天标题旁的压缩按钮可请求提前压缩。上下文过短时原生工具会说明无需压缩。“对话上下文”可查看、纠正实际压缩摘要，纠正后用于后续回复；原始消息继续保留，Agent 可通过历史检索工具找回。

设置页可配置 OpenAI Chat Completions 或 Anthropic Messages 协议、供应商地址、模型、密钥、上下文容量和压缩模型。当前供应商的 Anthropic 地址可直接使用。DeepWiki MCP 使用 Streamable HTTP；仓库配置为 `lsd-ff/AKRS.ZX2200`。

## 数据与边界

- `trunk/` 为只读源码，不包含应用生成文件；默认排除 `.git`、`.vs`、`bin`、`obj`、`packages` 等生成目录。
- `data/app.sqlite3` 保存完整对话、选区、运行事件和记忆来源；`data/checkpoints.sqlite3` 保存 Agent 检查点。
- `data/memories/` 保存跨会话 Markdown 记忆；`data/scratch/` 保存大工具结果和压缩档案。
- 密钥保存在本机 `data/settings.private.json`，接口返回掩码，Git 和导出备份排除密钥配置。
- 备份通过设置 → 数据 → 导出。恢复时先停止服务，将 ZIP 解压至 `data/`，再启动并填写密钥。
- 同一会话串行执行，全局最多三个运行。断线不取消任务；停止或重启后的运行可点击“继续运行”。
- 同一个数据目录只运行一个服务实例，避免并发服务干扰检查点和恢复状态。
- C# 符号定位使用 Tree-sitter 语法解析。首版支持阅读和分析，自动修改源码与执行构建留作后续扩展。

开发时后端在 `backend` 中运行 `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765`；前端在 `frontend` 中运行 `npm run dev`，Vite 将 `/api` 代理至后端。API 文档位于 `/docs`。

## 检查

```powershell
cd backend
uv run pytest -q
uv run ruff check app tests migrations
cd ../frontend
npm test
npm run build
npx prettier --check src vite.config.ts
```

测试模型用于确定性的框架回归，真实供应商和 DeepWiki 的验收另记在 `docs/development.md`。所有开发遵循根目录 `SKILL.md`，关键边界逻辑使用中文注释。

最新验收：后端 35 项测试通过、1 项因 Windows 符号链接权限跳过；前端状态测试、构建、格式检查以及真实模型、DeepWiki、记忆和上下文压缩验证通过。完整记录见 [开发与验收记录](docs/development.md)。
