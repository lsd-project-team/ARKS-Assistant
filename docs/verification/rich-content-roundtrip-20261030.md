# 新增富内容块的后端同步与端到端验收

日期：2026-10-30。

## 实现

沿用消息字符串中的 `rich-content` v1 围栏，在原有八类块之外支持 `markdown / chart / mermaid / mindmap / file / tool_call`。没有修改 HTTP API、SSE 事件名称/字段、数据库或历史恢复格式，没有新增运行依赖。

Pydantic 与前端使用相同字段、数量限制和关键校验：有限数值、空值与零值区分、标签和系列等长、饼图单系列非负、思维导图单根无环、资料 ID、工具状态、Mermaid 禁止配置覆盖/外链交互/自定义样式。未知字段、数字字符串及可执行图表 option 均拒绝。

模型提示说明每种块的语法和使用场景：数值比较/趋势优先图表，关系用 Mermaid，树状归纳用思维导图；用户要求纯 Markdown 时遵从。图表必须来自用户输入或实际工具返回，文件 ID/版本和工具执行信息不能编造，也不为重复卡片改变既有工具执行逻辑。

新增块进入现有事实核查投影：图表以原值表格表达，思维导图保留父子关系，文件保留资料 ID 与修订号，Mermaid 和工具 JSON 保留字面量。源码引用仍由真实读取证据校验。引用失效时只处理正文和真实来源字段，不篡改 Mermaid 源码、图表数值和工具参数/结果；显式 `arguments:null` 在引用重写后仍保留。

## 变更文件

- `backend/app/modules/chat/rich_content.py`：类型白名单、数据边界和空参数序列化。
- `backend/app/modules/chat/rich_presentation.py`：模型提示、Markdown 别名及新增块投影接入。
- `backend/app/modules/chat/rich_projection.py`：独立的新增块语义投影。
- `backend/app/modules/chat/rich_sources.py`：保护 Mermaid 字面量。
- `backend/tests/unit/chat/test_rich_extended.py`：新块、反例及引用重写回归。
- `backend/tests/integration/chat/test_rich_extended_roundtrip.py`：真实 Agent 装配、HTTP/SSE、文件、历史及前端跨进程渲染。
- `frontend/tests/chat/fixtures/rich-content-extended.json`、`frontend/tests/chat/rich-protocol.test.mjs`：前后端共享契约。
- `frontend/scripts/verification/rich-content-roundtrip.mjs`：读取 API 原始回答，运行前端解析、Renderer、ECharts、Mermaid。
- `frontend/src/features/chat/rich/mermaidRender.ts`、`frontend/src/features/chat/styles/rich-content.css`、`frontend/tests/chat/mermaid-runtime.test.mjs`：真实回复验收发现的 SVG 图片固有尺寸修复及回归。
- `scripts/verification/rich_content_roundtrip.py`：显式真实供应商的隔离验收入口。

## 真实模型验收

使用当前已配置的 `deepseek-flash`，以临时普通账号、临时数据库、临时源码和临时附件调用现有 API。正式配置只在内存中读取，不复制密钥，不读取正式历史，不修改正式源码或资料。图表输入来自本次验收明确提供的甲0、乙7、丙缺失，不是产品内置业务数据。

最终同一对话连续三轮通过：

| 场景 | 模型实际输出 | 核对结果 |
| --- | --- | --- |
| 数值比较 | `chart` | 甲为0、乙为7、丙为null，保留真实缺失 |
| 流程关系与分类 | `mermaid`、`mindmap` | 流程语法和树层级通过实际引擎绘制 |
| 源码与附件 | `source_reference`、`file` | 实际 `read_source`、源码证据核对、文件修订类型及下载原文一致 |

三轮格式事件均为 `passed:true`；HTTP 返回201，SSE 序号递增且 `Last-Event-ID` 重放精确匹配，`done.answer` 与历史消息/运行回答逐字一致；同一会话恢复为2、4、6条消息，临时源码字节未变。最终脚本还将三轮原始回答送入前端解析器、React Renderer 和实际图形引擎，三个图形均成功绘制。

初次真实验收暴露模型把 `file.version` 写成字符串 `"1"` 的问题，后端按严格契约拒绝，连带源码文档无法通过格式校验；没有放宽类型。提示已明确“文件修订号为 JSON 数字、源码版本为字符串哈希”，增加字符串修订号反例测试后重新完成三轮验收。初始失败和最终结果均保留在本机忽略目录 `output/`，不以部分成功代替完整结果。

复现命令（需要已安装的前后端依赖，会消耗供应商额度）：

```powershell
backend/.venv/Scripts/python.exe scripts/verification/rich_content_roundtrip.py --live --output output/rich-content-roundtrip/final-live.json
```

最终报告：`output/rich-content-roundtrip/final-live.json`、`frontend.json`；日志：`output/rich-content-final-live.log`。只需复查前端时，可运行：

```powershell
cd frontend
node --experimental-strip-types scripts/verification/rich-content-roundtrip.mjs ../output/rich-content-roundtrip/final-live.json
```

## 自动回归及限制

相关后端回归共269项通过，包括聊天、富内容、格式、核查、源码证据、提示装配和架构约束；Ruff 通过。新增端到端回归仅替换供应商，实际执行 Agent 图、受认证 API、SSE、临时附件下载和历史恢复，再跨进程调用真实前端引擎。jsdom 仅替代缺失的文字尺寸测量，不替代图形解析、布局或 SVG 生成。

共享工作区同时有其他任务修改问题与经验模块，首次全量前端测试出现该模块8项失败，记录在 `output/rich-backend-adaptation-frontend-tests.log`。本次不覆盖或提交那些改动；隔离工作树仅叠加本次补丁检查，最终前端352项、后端269项全部通过，TypeScript、生产构建和Ruff通过。最后的 SVG 尺寸修复后另重跑端到端用例通过；对应日志为 `output/rich-isolated-final-frontend-tests.log`、`rich-isolated-backend-tests.log`、`rich-isolated-final-e2e.log`、`rich-isolated-final-build.log`。

浏览器回放最终真实回复时发现 Mermaid 的 `width="100%"` 会在图片上下文放大窄竖图，现以经过清理的 SVG `viewBox` 明确图片固有宽高，保留宽图滚动；没有注入模型 HTML。新增尺寸回归测试通过，真实柱图、流程图和思维导图已用当前 Renderer 在 Edge 中核对。离线回放不冒充仍在运行的临时资料服务，源码定位与下载由前面的真实 API 和交互回归单独验证。

未采集覆盖率，未做设备验证。模型自由生成仍可能出错，不能将三轮通过当作所有问法的可靠性保证。正式服务未重启，旧进程需在发布时重新加载后端代码；生产 Cookie、账号、历史和资料不受本次临时验收影响。
