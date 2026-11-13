# 聊天图片输入验收（2026-11-13）

## 目标与范围

聊天附件支持 PNG/JPG/GIF/WebP 图片：可以“＋”上传，也可以直接粘贴截图；界面显示缩略图并按原图预览；图片作为用户消息的多模态内容发送给支持视觉的 `deepseek-flash`，用于识别报错截图、软件界面和设备/现场照片。

本范围不包含：用 OCR 代替模型看图（扫描 PDF 的 OCR 保持原样）、Word/Excel 内嵌图片、ZIP 内图片随消息发送、问题与经验原图接入对话。

## 实现

| 位置 | 内容 |
| --- | --- |
| `backend/app/modules/chat/image_attachments.py` | 按文件内容校验格式、单边 8192 像素上限、发送前压缩（长边 2048、4 MB）、`<attachment-image>` 标记与请求边界展开 |
| `backend/app/modules/chat/attachment_parsing.py` | 图片进入附件白名单，生成占位正文与解析说明；ZIP 内图片逐项跳过并说明原因 |
| `backend/app/modules/chat/attachments.py` | 元数据新增 `kind`；图片校验原件 SHA256 后按真实格式返回 |
| `backend/app/modules/chat/attachment_router.py` | 新增 `GET /api/attachments/{id}/image`，只对真实图片声明图片类型并允许内联显示 |
| `backend/app/agents/runtime/engine.py` | 用户消息正文写入图片标记，文档清单不再混入图片 |
| `backend/app/agents/runtime/images.py` | `ImageAttachments` 中间件在每次模型请求前展开图片，检查点只保留文本标记 |
| `backend/app/agents/tools/attachments.py` | 提示模型图片已直接提供、不要用附件工具读图，文档工具只开放文档 |
| `backend/app/agents/context/tokens.py` | 每张图按 1024 tokens 预留上下文预算 |
| `frontend/src/features/chat/attachments/*` | 图片可选、缩略图、原图预览、粘贴截图生成可辨认文件名 |
| `frontend/src/features/chat/components/ChatComposer.tsx` | 输入框仅在有图片文件时接管粘贴，文字粘贴保持不变 |

## 验证结果

1. `pytest tests/integration/chat/test_image_attachments.py`：9 项通过。覆盖上传/预览/下载/内联类型、损坏图片与超边图片拒绝、图片不进入文档工具清单、正文标记、请求边界展开为 `image_url`（data URL）、缺失图片说明、ZIP 内图片跳过、图片 token 预算、`ImageAttachments` 中间件。
2. `pytest tests/integration/chat`：163 项通过。
3. `pytest tests/integration/agents tests/unit/agents tests/unit/chat`：409 项通过；1 项 `test_retrieval_budget[openai]` 因本机 `NO_PROXY` 含 `[::1]` 触发 httpx2 解析失败，清理代理变量后该文件 8 项全部通过，属环境问题，与本次改动无关。
4. 前端 `npm test`：422 项通过；`tsc -b` 与 `npm run build` 通过。
5. 真实模型端到端：独立临时数据目录、8766 端口、复制本机模型配置，上传 900×380 截图（红框红色 X、“错误代码 E-2331”“请检查供料传感器”），提问“只读取这张截图里的错误代码和提示文字”。`deepseek-flash` 回答：

   > 截图（报错截图.png）中的文字：错误代码：**E-2331**；提示文字：**请检查供料传感器**；左侧红框内是一个红色“X”图标。

   截图文字由视觉模型直接读取（当前流程没有把 OCR 文本放进消息），说明图片确实随用户消息发送。
6. 运行服务：重启后 `/api/health` 正常，新构建资产 200，`/api/attachments/{id}/image` 未登录返回 401，与下载接口一致。

## 边界与未覆盖

- 图片不做 OCR，文字识别依赖模型的视觉能力；看不清的内容按实际可见程度说明。
- 历史对话中的图片每轮重发，多图按张计费并占用上下文；单请求仍受供应商 48 MiB 请求体限制。
- `deepseek-v4-pro` 等不支持视觉的模型会由供应商返回错误，界面显示错误信息；当前配置的 `deepseek-flash` 支持视觉。
- 未在浏览器里人工点击缩略图/预览/粘贴，页面验证由用户在实际使用时确认；后端与组件测试、生产构建已覆盖渲染路径。
- 本会话 Shell 的 `NO_PROXY` 含 `[::1]` 时 httpx2 报 `Invalid port`，服务已用清理重复代理变量后的环境启动；普通桌面启动不受影响。

## 补充：编码代理查看项目图片（view_image）

用户提出“让助手自己去看它运行后的界面截图”，此前编码工具只能返回文本，代理看不到自己生成的 PNG。

实现：`view_image` 工具读取项目内 PNG/JPG/GIF/WebP（按内容校验，单边 ≤8192 像素、≤32 MB），返回工具结果并追加一条只含 `<attachment-image path=… />` 标记的用户消息；`ImageAttachments` 中间件在模型请求边界把标记展开为图片块。检查点、摘要与历史正文不保存 base64；图片缺失、路径越界或格式不符时明确告诉模型“未能发送”，不会假装看过。

验证：

1. `pytest tests/unit/coding`：45 项通过，覆盖图片读取与路径校验、`view_image` 工具在工具节点内返回 ToolMessage + HumanMessage 标记、失败/缺失图片提示、含引号文件名、助手消息不展开图片。
2. `pytest tests/unit/coding tests/unit/agents tests/unit/chat tests/integration/chat/test_image_attachments.py`：304 项通过。
3. `pytest tests/integration/agents tests/integration/chat/test_api.py tests/integration/chat/test_conversation_workflows.py`：170 项通过；`test_retrieval_budget[openai]` 仍因本机 `NO_PROXY` 的 `[::1]` 报错，清理代理变量后通过。
4. 真实模型端到端：隔离数据目录 + 8767 端口，创建临时项目并放入截图（“界面截图 / VIEW-OK 7788”，左侧蓝色方框），提问“用 view_image 打开 screenshots/app.png，告诉我图中黑色文字和蓝色方框的位置”。`deepseek-flash` 回答“黑色文字有两行：界面截图、VIEW-OK 7788；蓝色方框位于图片左侧”，说明工具注入与图片展开在真实代理运行中生效。

限制：`view_image` 只读项目目录内的图片；截图需要先保存到项目内。历史轮次会重新携带已查看图片，占用上下文按 1024 tokens/张预留。
