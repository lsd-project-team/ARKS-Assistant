# Archify verification receipt

Source analysis only; ZX2200 was not executed.

Rendered screenshots reviewed in dark at 1440×900 and light at 2048×1320. Labels, routes, node fit and page composition were inspected. Interactive controls and exports were not manually exercised.

## workflow

- Output: `automation-workflow.html`
- Specification SHA-256: `e4dea3974ca162844b35225a94265c6d1f893460a284f2952e8c3489ec2da9b7`
- Artifact SHA-256: `de4c54c8cd634a12d9795807288e28497617759bf70f52b2668dd28ab6e64795`
- Validation: 9/9 showcase checks; 0 errors; 0 warnings.
- Browser evidence: passed (Edge Chromium).
- Viewports: 1440×900, 1600×1000, 1920×1080, 2048×1320; no page overflow.
- Visual review: passed for the screenshot scope above.
- Visual correction rounds: 1.

## sequence

- Output: `automation-sequence.html`
- Specification SHA-256: `625227f2b40f3d29194835b937afebb52a8ab1f221b7130d5a9f65940f0efaf0`
- Artifact SHA-256: `42cb28e2d9803582cccb5b77c320085c35dcbb50ae99dd8485331a9c0920545a`
- Validation: 9/9 showcase checks; 0 errors; 0 warnings.
- Browser evidence: passed (Edge Chromium).
- Viewports: 1440×900, 1600×1000, 1920×1080, 2048×1320; no page overflow.
- Visual review: passed for the screenshot scope above.
- Visual correction rounds: 1.

## 2026-09-24 扩展分析交付

- 新增完整中文分析、离线源码导航、8 个流程章节。
- 54 处原始代码片段已逐项核对内容及源文件 SHA-256。
- SignalPool 23 项声明、137 处未注释引用已输出为 Markdown 和 JSON；清单包含手动/调试路径，不当作全部都属于生产主线。
- 新增启动图：9/9 showcase 校验通过，0 errors / 0 warnings；Edge visual-check 通过 1440×900、1600×1000、1920×1080、2048×1320。
- 图像复核：实际查看启动图 2048×1320 light 与 1440×900 dark 截图，节点、箭头、文字无明显遮挡。未人工测试导出按钮。机器 receipt 中 visualReview=pending 保留原状，本段单独记录截图复核。
- 启动图 JSON SHA-256：`91429d7edc5842c52addde0d6d6f386972b61ffbac232cb3345a8733e4b531a1`
- 启动图 HTML SHA-256：`8f01fcd14e79fc9a5a46a9c79119e1514498086a47692f347b960e66a5d4c190`

### 图形交付状态

运输、S1、供晶、S2 调度、取晶、固晶及恢复共 7 张子图已完成布局修正，均已输出 HTML 和 JSON，并通过 showcase 校验（9/9 checks，0 errors，0 warnings）。

每张图都保留 validation、delivery 和 browser-run receipt；可从导航页打开独立交互图或下载可编辑 JSON。

### 导航页验证边界

`index.html` 的内嵌 JavaScript 通过 `node --check`；离线 JSDOM 验证了 11 个章节跳转、97 个分支链接、源码折叠、信号搜索和本地文件链接。真实浏览器打开 file URL 受安全策略限制，因此 portal-verification.json 明确记录其验证范围。独立 Archify 图已用 Edge visual-check 验证。

没有运行 ZX2200 程序、驱动或机械控制动作。结论是静态源码分析，不是现场行为验证。

## 软件总体架构扩展

- 新增 `zx2200-architecture.html` 和 `zx2200-architecture.archify.json`。
- 架构图通过 Archify showcase：9/9 checks，0 errors，0 warnings。
- 新增说明：[zx2200-architecture-analysis.md](zx2200-architecture-analysis.md)。
- 导航页增加“软件总体架构”章节和入口。

- 新增配置与配方生命周期图：`recipe-lifecycle-workflow.html`，通过 9/9 showcase checks。
- 新增说明：[recipe-lifecycle-analysis.md](recipe-lifecycle-analysis.md)。

- 新增视觉、运动与补偿图：`vision-motion-workflow.html`，通过 9/9 showcase checks。
- 新增说明：[vision-motion-analysis.md](vision-motion-analysis.md)。

- 新增运行数据与持久化图：`runtime-dataflow.html`，通过 9/9 showcase checks。
- 新增说明：[runtime-dataflow-analysis.md](runtime-dataflow-analysis.md)。

- 新增手动维护、报警与标定图：maintenance-calibration-workflow.html，通过 9/9 showcase checks，0 errors / 0 warnings。
- 该图覆盖报警暂停、GuideMove 点动、视觉灯光/模板调整、标定补偿、参数保存与 Continue 恢复；源码证据见 maintenance-calibration-analysis.md。

- 新增框架运行时图：framework-runtime-architecture.html，通过 9/9 showcase checks，0 errors / 0 warnings；补充 Signal 的 Pause/Stop/SingleStep、RuntimeProvider.ThreadFlag、MachineConfigContext 和空的 MachineService 证据。

- 新增 business-branch-coverage.md：按枚举与 switch 证据登记输送、S1/S2、取晶、搜晶、视觉、失败结果和设备状态分支；未把注释分支或外部驱动内部行为当成已实现路径。

- 新增标定任务细化图：calibration-task-workflow.html，通过 9/9 showcase checks，0 errors / 0 warnings；源码说明覆盖 CalibrateTask 的点胶、Bond、上视、晶圆台和只标定相机入口。

- 本轮新增图的 isual-check 已执行；Archify 返回 chrome-unavailable，因此浏览器自动证据为 skipped，未伪称通过。两张图的确定性 deliver 与全部 9/9 showcase 校验均已通过。临时 visual-check sidecar 已清理。

- 新增整合总报告：zx2200-final-integrated-report.md，统一主流程、框架、业务分支、数据面、边界和全部图表入口。

- 新增 software-build-validation.md：记录实际 dotnet build 失败原因、71 个 HintPath 中 5 个缺失依赖和缺失 Parameters 工程引用；未将静态分析冒充编译/运行验收。

- 追加系统 MSBuild 构建尝试：MSBuild 4.8 可启动但主工程未成功构建；失败证据包括缺少 .NET Framework 4.8 reference assemblies、LangVersion=latest 不受旧编译器支持、缺少 LC.exe、MWArray 和架构/相机依赖冲突。

- 新增 build-dependency-inventory.md：扫描 17 个项目，记录 8 项缺失引用以及 .NET Framework/Windows SDK/Visual Studio 构建机要求。

- 使用系统 Edge Chromium 完成框架运行时图和标定任务图的 visual-check：1440×900、1600×1000、1920×1080、2048×1320 均通过 containment/readability/viewerChrome；浅色与深色截图检查均通过。临时截图和 sidecar 已清理。
