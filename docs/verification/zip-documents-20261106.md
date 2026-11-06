# ZIP 内文档解析验收

日期：2026-11-06。

## 行为与范围

聊天 ZIP 附件新增包内 PDF、DOCX、XLSX、CSV 解析，复用单独上传同类文件的解析器。支持子目录、大小写扩展名及同名不同目录文件；正文保留包内完整路径、PDF 页码、Word 段落、Excel 工作表与单元格、CSV 行号和源码行号。

各文件解析说明随对应正文保存。混合文字和无文本页的 PDF 会使整个 ZIP 标记为部分可读，并保留缺失页说明。损坏、加密、无文字 PDF、空文件、不支持格式及单文件大小超限逐项列出路径和原因，其余文件继续读取；全部不可读则拒绝上传。

保留 32 MB 上传上限、ZIP 内源码/配置文本 2 MB 上限和整个附件 100 万字符上限。ZIP 内四类新增文档单文件上限为 32 MB；DOCX/XLSX 自身的展开体积和条目计入 ZIP 累计 64 MB、2000 项预算。累计正文或展开预算超限时整个附件失败，不降为部分读取成功。路径、加密、符号链接检查继续复用原安全压缩包检查；嵌套 ZIP 不递归读取。

不增加新依赖、数据库字段、OCR、公式重算或内容执行。正式数据库、附件和只读业务源码未用于测试。

## 测试设计与结果

修改前相关后端基线为 **44 passed**。新增 ZIP 单元测试在原实现下为 **21 failed、1 passed**，失败包括新增格式不能读取、部分解析状态缺失及累计预算缺失；现有正文超限反例已经通过。

最终执行后端四个测试文件，**71 passed、0 failed、0 skipped**：

- `backend/tests/unit/chat/test_attachment_parsing.py`：原格式与异常文件回归。
- `backend/tests/unit/chat/test_zip_attachment_parsing.py`：新增 22 项，覆盖四类文档位置标记、混合包、同名不同目录、损坏/空/加密/无文字 PDF、混合 PDF 页、Office 大于旧文本限制、单文件及累计资源限制、嵌套 ZIP、外层和 Office 内部危险路径。
- `backend/tests/integration/chat/test_attachments.py`：新增混合 ZIP 的真实字节上传、正文预览和原件下载，以及四类包内文档驱动测试副本修改；原消息绑定、备份、队列、恢复和工具权限继续回归。
- `backend/tests/integration/chat/test_attachment_access.py`：账号、项目、对话移动和旧库迁移回归。

已有重复 ZIP 文件名反例在构造测试数据时产生 1 条 `Duplicate name` 警告；对应拒绝行为通过。

前端 `frontend/tests/chat/attachments.test.mjs` **6 passed、0 failed、0 skipped**，覆盖格式/大小、批量失败重试、异步草稿归属、重复上传、数量限制及上传期间发送保护。前端提示改为“ZIP”，不再仅称“源码 ZIP”。

本次四个 Python 文件的 Ruff 规则和格式检查、前端改动文件的 Prettier 检查均通过。前端生产构建的源码/模块资料校验、Agent 知识索引、TypeScript 和 Vite 打包全部通过，候选产物位于 `output/zip-document-release/`。

未采集覆盖率。测试质量：在本次格式提取、状态传播、资源限制及附件链路范围内为高；断言检查真实字节解析、具体正文/位置/状态、原件一致性和副本差异，不以非空结果代替正确性。

## 复现命令

在 `backend/` 执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q tests/unit/chat/test_attachment_parsing.py tests/unit/chat/test_zip_attachment_parsing.py tests/integration/chat/test_attachments.py tests/integration/chat/test_attachment_access.py --tb=short
.\.venv\Scripts\ruff.exe check app/modules/chat/attachment_parsing.py tests/helpers/chat_attachments.py tests/unit/chat/test_zip_attachment_parsing.py tests/integration/chat/test_attachments.py
.\.venv\Scripts\ruff.exe format --check app/modules/chat/attachment_parsing.py tests/helpers/chat_attachments.py tests/unit/chat/test_zip_attachment_parsing.py tests/integration/chat/test_attachments.py
```

在 `frontend/` 执行：

```powershell
node --experimental-strip-types --test tests/chat/attachments.test.mjs
npx prettier --check src/features/chat/attachments/files.ts
npm run build -- --outDir ../output/zip-document-release
```

## 验证边界

Agent 图和副本编辑使用确定性测试模型，实际执行附件读取与副本工具，不调用真实模型供应商。未进行浏览器端到端、真实设备、任意复杂 Office 版面或扫描件 OCR 准确率验收。PDF 仍仅读取文本层；OCR 属于后续独立功能。构建产物位于忽略目录，不据此发布或重启正式服务。

格式及生命周期说明见[聊天附件](../features/chat-attachments.md)。
