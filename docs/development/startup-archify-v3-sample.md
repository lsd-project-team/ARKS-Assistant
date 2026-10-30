# 启动、回零与生产放行：Archify 3.2 样例

日期：2026-10-27。

## 样例入口与范围

[打开独立 HTML](../../resources/knowledge/flows/startup-v3-sample/startup.html)。页面包含开机加载、回零返回、生产放行三张交互图，以及任务调用条件表；步骤与节点联动，完整阅读器支持节点详情和固定版本源码链接。

这是独立阅读样例，尚未替换正式“功能与图谱”入口。主程序、正式数据、原有图谱和 trunk 均未修改。

说明依据沿用现有启动专题，并逐字核对当前 trunk 的 12 段源码。由于 trunk 不纳入 Git，另存[片段快照](../../resources/knowledge/flows/startup-v3-sample/source-snapshot.md)，保留业务文件路径、原始行号及文件 SHA-256。Archify 引用固定在快照提交 `07ad3c75e9ce100f274807f88e23bf11f2e4367d`；引用对象是已提交的片段快照，未将 trunk 原文件标成 Git 固定版本。

范围限定为当前外层控制流，不包括驱动内部、全部自检子方法、真实机械到位或设备生产验收。特别区分 Main 的回零返回、Load 门控、Prepare 副作用、Working 赋值和任务入口调用。

## 工具与重新生成

使用官方 [Archify v3.2.0](https://github.com/tt-a1i/archify/releases/tag/v3.2.0) 的 `archify.zip`。下载文件 SHA-256 为 `70e210265c59f24dcbdf2a502ff671104b5454e7ee7d3554aecd86bad32384f5`，与 GitHub 发布资产摘要一致。工具解压到本地 `.tools/archify-v3.2.0/`，不随项目提交，不修改全局技能配置。

草稿、三份图规格、源码快照和最终 HTML 均位于 `resources/knowledge/flows/startup-v3-sample/`。分行布局避免横向缩图导致文字过小，图例使用界面入口、程序动作、条件返回和任务调用等业务名称。`.gitattributes` 仅对这个样例目录关闭换行转换，保证检出后的字节仍与交付回执一致；Git 暂存的 HTML 和五个输入文件摘要已逐项核对。

在项目根目录执行；每轮使用新的检查目录，保留前轮证据：

```powershell
node .tools/archify-v3.2.0/archify/bin/archify.mjs finalize explainer resources/knowledge/flows/startup-v3-sample/candidate.archify.md resources/knowledge/flows/startup-v3-sample/startup.html --repo-root . --browser-check --out-dir output/startup-v3-sample/review-next --json
```

本地预览仅公开样例目录：

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory resources/knowledge/flows/startup-v3-sample
```

浏览器访问 `http://127.0.0.1:8766/startup.html`；单独打开 HTML 也可阅读。

## 实际检查

- 最终 `finalize` 的 validate、deliver、check、browser-check 均通过，0 条诊断。
- 浏览器自动检查覆盖 1280×900、1440×900 的浅色与深色；包含横向容纳、文字可读性、引用、交互、无 JavaScript 和打印检查。
- 在应用内浏览器目视开机、回零、生产三张图，实测完整阅读器、节点详情中的固定版本来源、逐步阅读和下一步节点高亮。
- `knowledge:check` 通过：65 项图谱/资料及 65 项资源链接；其源码检查通过：6 专题、107 条流程、403 节点、658 条说明，72 个文件、540 段依据与当前 trunk 一致。
- 本次只增加样例资源与记录，未修改应用逻辑；未执行后端测试、全量前端测试或生产构建。

[可携带的验证摘要](../../resources/knowledge/flows/startup-v3-sample/verification.json) 记录最终 HTML 和输入文件摘要；完整本地回执位于 `output/startup-v3-sample/review-5/`。自动检查与上述目视范围都不替代设备运行验收。
