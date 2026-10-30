# AI 回复富内容展示层

更新：2026-10-30。

同日补充 ARKS 经验回答：经验工具不再限制为文字和原图；无原图时可从已选资料归纳明确标注的示意图。事实核查读取原始组件协议和可读投影，检查图内标签、连线、表格与说明，并在修订时保留无争议图形。实际参数、适用条件、未知单位、固定版本引用、原图关联和失败时的原文降级继续保留。见[蓝膜案例专项验收](../verification/arks-rich-content-20261030.md)。

## 项目分析与集成范围

历史 `Message.content`、`Run.answer` 和 SSE 累积文本都是字符串。已保存消息通过 `MessageBubble → AnswerMarkdown → RichContentRenderer` 展示，运行中回复同样复用 `AnswerMarkdown`。`useConversation` 恢复原始消息，`useRunStream` 接收 `token / answer_replace / done`，`createAnswerBuffer` 按 32ms 合并更新，事件序号负责重连去重。

前端阶段扩展既有 Renderer、校验器和代码块，复用 React Markdown、GFM、`@pierre/diffs` 提供的 Shiki 4.5、`SourceReference` 的证据校验/源码定位、`ToolActivity` 的工具事件、`OriginalMaterialViewer` 的预览下载、现有主题及 820px 阅读宽度。随后同步后端块白名单、模型展示提示和事实核查投影；SSE、消息存储、API 和正式数据不变，没有引入另一套聊天运行时。

参考了 [assistant-ui](https://www.assistant-ui.com/) 的组件组合、[Streamdown](https://streamdown.ai/) 的流式阅读与代码操作，以及用户提供的 [Lingxi AiRichContent](https://jxdoub.github.io/lingxi-ui/components/ai-rich-content.html)。思维导图评估了 [React Flow](https://reactflow.dev/learn/tutorials/mind-map-app-with-react-flow)：当前只读展示不需要节点编辑器，采用已新增 ECharts 的树布局，支持拖动、缩放、点击折叠和文字层级替代，不增加 React Flow 依赖。

## 支持内容

| 内容 | 实现 |
| --- | --- |
| Markdown | 六级标题、段落、嵌套列表、引用、GFM 表格、任务列表、删除线、安全链接；保留中英文和工艺参数的单波浪号 |
| 代码 | Shiki 双主题高亮、语言/文件名、复制、长代码折叠、横向滚动、可选自动换行；复制保留缩进、CRLF 和末尾空行 |
| 数学 | `$...$` 行内、`$$...$$` 独立 KaTeX；错误显示可读源码，关闭信任扩展，限制展开次数与尺寸 |
| 图表 | ECharts 柱图、折线图、饼图；显式标签与数值、空值不补零、原始数据表、响应容器变化及主题切换 |
| 流程图 | 普通 `mermaid` 围栏或结构化 Mermaid；串行渲染、SVG 清理、图片上下文展示、语法错误保留源码 |
| 思维导图 | 单根节点树，拒绝循环与孤立父节点；拖动/缩放/折叠及文字层级 |
| 文件 | 现有交接资料 ID 对应的文件卡片；点击后走原有受认证接口及预览下载组件 |
| 源码引用 | 独立卡片显示文件、路径、行号；保留原版本/目录元数据、证据检查、预览与右侧源码定位 |
| 工具调用 | 独立折叠项，名称、原工具名、运行/成功/失败/跳过、参数与结果；参数和结果始终为文字 |

## 类型与兼容性

沿用消息内的显式 `rich-content` JSON 围栏及 `{version: 1, blocks: [...]}`。`ContentBlock` 使用 TypeScript 判别联合和明确 switch 分发。旧 `text / overview_grid / step_flow / source_reference / code / table / diagram / collapsible` 全部保留。

新增块字段：

| type | 字段 |
| --- | --- |
| `markdown` | `id, content`，与历史 `text` 共用安全 Markdown |
| `chart` | `id, title?, chart_type: bar/line/pie, labels: string[], series: {id, name, values: (number/null)[]}[]` |
| `mermaid` | `id, title?, content` |
| `mindmap` | `id, title?, nodes: {id, label, parent_id?}[]` |
| `file` | `id, record_id, name, version?` |
| `tool_call` | `id, tool: ToolEvent`，字段沿用现有工具事件 |

未知/坏块仅在自身位置展示错误与原始 JSON，相邻合法内容继续展示。文档版本、JSON 语法、重复块 ID 或整体大小等顶层错误仍降级整段协议原文，前后 Markdown 保留。严格 `parseDocument` 校验接口保留，消息解析显式开启局部恢复。`unsupported` 只能由前端校验器生成。

图表配置由程序根据白名单字段构造，不接受模型的任意 ECharts option、formatter、回调、URL 或可执行代码；表格和图表数据均来自收到的消息，产品中没有示例业务数据。图表限 500 标签、12 系列，思维导图限 60 节点，文档仍限制 256 KiB、128 块和嵌套深度。重依赖按内容懒加载。

不启用 `rehype-raw`、动态 JSX 或 JavaScript 执行。Mermaid 禁止配置覆盖、外链交互及自定义样式指令，全局及流程图均禁用 HTML 标签；生成结果经 DOMPurify 清理，移除脚本、事件、HTML、图片及链接，再以 SVG 图片显示，不绑定 Mermaid 事件。

## 流式与历史恢复

普通 Markdown 保持增量展示。未闭合代码围栏仍显示已接收的纯文本，完成后高亮。未闭合 Mermaid 在流式期间保留源码并等待完成，错误时不丢原文。结构化 JSON 围栏完整闭合后才创建交互块；断流或取消保留不完整原文。

沿用围栏位置作为段 ID、块自身 ID 作为 React key。已完成文档按原始文本缓存；追加文本不重建旧块，代码展开、自动换行、工具折叠状态保持。`answer_replace` 变更原文时清除解析缓存，错误边界允许新块恢复。历史普通 Markdown、旧八类块、分页、重新生成和多轮会话不迁移数据。整条回复复制支持新增块的文字/表格/源码投影，异常块保留 JSON。

## 依赖与组件

新增运行依赖：`remark-math 6.0.0`、`rehype-katex 7.0.1`、`katex 0.16.47`、`echarts 6.1.0`、`mermaid 12.2.0`、`dompurify 3.4.17`。KaTeX 样式与解析器版本一致。新增测试依赖 `jsdom 30.1.3`。Shiki 继续由已存在的 `@pierre/diffs` 共享，不重复安装。

新增组件：`BasicBlocks.tsx` 中的 `CodeContent / SourceReferenceBlock / ToolCall / UnsupportedContent`；`ChartBlock / ChartSurface / MermaidBlock / MindmapBlock / FileBlock`。Markdown 块复用现有独立 `TextBlock`，表格复用 `DataTable`，旧业务块继续各自独立组件。

修改文件：

- `frontend/package.json`、`frontend/package-lock.json`
- `frontend/src/app/components/Markdown.tsx`
- `frontend/src/shared/ui/markdown/CodeBlock.tsx`
- `frontend/src/features/chat/components/ToolActivity.tsx`
- `frontend/src/features/chat/lib/runCompletion.ts`
- `frontend/src/features/chat/rich/{types.ts,schema.ts,parseContent.ts,RichContentRenderer.tsx,BlockBoundary.tsx,SourceReference.tsx,contentToMarkdown.ts}`
- `frontend/src/features/chat/styles/{answer-content.css,rich-content.css}`
- `frontend/tests/chat/{rich-protocol.test.mjs,rich-renderer.test.mjs}`

新增文件：

- `frontend/src/features/chat/rich/{BasicBlocks.tsx,ChartBlock.tsx,ChartSurface.tsx,FileBlock.tsx,MermaidBlock.tsx,MindmapBlock.tsx,chartOptions.ts,mermaidRender.ts,visualValidation.ts}`
- `frontend/tests/chat/{code-interaction.test.mjs,rich-interaction.test.mjs,rich-visuals.test.mjs,mermaid-runtime.test.mjs}`
- 本说明及 `agent.md` 中的本轮进度。

## 验证结果

分阶段执行相关测试、`npx tsc --noEmit` 和 `npm run build`：第一阶段定向 23 项通过，第二阶段富内容定向 34 项通过，第三阶段全量 347 项通过，最终全量 **350 项通过、0 失败、0 跳过**。四阶段均通过类型检查和生产构建。日志保存在本地 `output/rich-stage*-build.log` 和 `output/rich-final-tests.log`。

覆盖用户要求的普通 Markdown、千行代码、未闭合代码流、表格转义及对齐、行内/独立/损坏公式、真实 Mermaid、异常图表数据、未知块、源码点击、工具状态和历史恢复。ECharts 实际生成柱/线/饼/树 SVG；Mermaid 实际运行解析、布局、SVG 生成与清理，jsdom 仅替代不具备的文字尺寸测量。交互测试实际挂载 React，断言源码跳转参数、组件身份、折叠状态、文件版本校验及文字安全。外部接口使用边界替身，不读写正式库；原有源码导航测试继续验证真实 store 的行号定位行为。

浏览器隔离验收使用当前真实 Renderer 和既有样式，已核对浅色、深色、350px 内容区域、Shiki、KaTeX、Mermaid、ECharts，以及未核实源码和未知块的安全降级。测试输入明确标为非业务数据，仅保存在忽略的 `output/`，不注入正式产品或模型。

## 边界与人工验收

- 后端已同步全部六类新增块，模型收到相同字段及使用条件；图表、导图、Markdown 正文进入原有核查投影。源码卡片仍需已读证据，工具和文件只能引用实际返回数据。文件修订号必须为 JSON 整数，源码版本仍为字符串；非法格式继续保留原文并降级，不做隐式类型转换。真实模型三轮 API/SSE 与前端渲染已通过，见[后端同步与端到端验收](../verification/rich-content-roundtrip-20261030.md)。模型生成具有不确定性，单次验收不表示所有问法都能产生正确结构。
- 文件能力限已有交接资料；附件接口只提供当前文件，指定旧版本而当前版本不符时明确拒绝预览，不冒充历史附件。任意本机路径和外部下载 URL 不受支持。
- 真实供应商通过临时账号、资料和源码完成端到端验收；正式业务长回答、生产 CSP、浏览器剪贴板权限、实际移动设备和跨浏览器兼容性仍需人工核对。Mermaid 12 对现代浏览器有要求，加载/绘制失败会保留源码。
- 前端阶段未运行后端测试；后端同步阶段已执行相关后端回归。没有采集覆盖率或进行设备验证；未改正式登录、数据库或源码，也未重启已有后端服务。
