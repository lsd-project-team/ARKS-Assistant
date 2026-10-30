# 日志测试模块：手动提交与外部日志库边界

更新：2026-09-28。部分复核；未执行测试程序，未把测试日志当作生产运行证据。

## 流程摘要

Program.Main → FrmLogTest 构造 → InitializeComponent → 创建 UcLogControl 并加入 GclLog → 设置 LogsManager.IsLogInfo/IsLogWarn 为 true → 等待用户点击两个独立按钮 → 顺序调用 LogHelper.Post。没有在已读窗体执行代码中发现周期调度、后台 Task 或生产任务启动。

## 步骤与源码

|步骤|实际行为|证据|
|---|---|---|
|入口|运行日志测试窗体|[Program.cs:14](../../trunk/AKRS.Galaxy2.LogTest/Program.cs#L14)|
|初始化|创建日志控件，开启 Info/Warn 标志|[FrmLogTest.cs:14](../../trunk/AKRS.Galaxy2.LogTest/FrmLogTest.cs#L14)|
|异常按钮|创建 Exception 对象作为参数，而不是 throw；按源码顺序提交18种 Level，分类 Global，目标参数 InFileAndUI|[BtnAnomalies_Click:28](../../trunk/AKRS.Galaxy2.LogTest/FrmLogTest.cs#L28)|
|普通日志按钮|依次向 Hardware、MainSoftWare、PR、Dispense、Global 各提交 Info/Warn/Error，共15次调用；Process、Detection、MeasureHeight 的调用被注释|[BtnLogs_Click:56](../../trunk/AKRS.Galaxy2.LogTest/FrmLogTest.cs#L56)|
|触发绑定|两个 Click 分别绑定对应处理函数，不互相调用|[Designer:57](../../trunk/AKRS.Galaxy2.LogTest/FrmLogTest.Designer.cs#L57)、[66](../../trunk/AKRS.Galaxy2.LogTest/FrmLogTest.Designer.cs#L66)|

## 输入、输出及失败边界

输入为用户点击及代码内固定消息、级别、类别，异常按钮另含构造的 Exception。输出在可见源码中只能确认是向 LogHelper.Post 提交的请求。InFileAndUI 表示传入的目标参数，不等于文件已写入、UI已显示；Level.Off/All 等特殊级别也不能据调用次数推算实际日志条数。处理函数没有局部 catch、重试、结果检查或完成确认；若调用同步抛错，后续调用可能不再执行。库内部是否排队、过滤、吞异常或异步写盘仍未证实。

## 依赖与配置闭环

[csproj:39–53](../../trunk/AKRS.Galaxy2.LogTest/AKRS.Galaxy2.LogTest.csproj#L39)指定启动对象并引用 ZX2200/libs 下 AKRS.Galaxy2.Log.dll 和 log4net.dll。两文件在本轮检查中存在，但未加载或验证二进制兼容性。还依赖 DevExpress。对 trunk 排除 bin/obj 的 C# 搜索未找到 LogHelper、LogsManager、UcLogControl 的 class 定义，因此当前调用追踪在外部程序集边界停止。

[Log4Net.config:1](../../trunk/AKRS.Galaxy2.LogTest/Log4Net.config#L1)存在独立 log4net 配置，包含类别 logger 和滚动文件 appender 声明；但本项目入口、窗体和 AssemblyInfo 未发现显式 XmlConfigurator/Configure 加载。项目将该文件作为 None 项登记，未见该项配置 CopyToOutputDirectory，见 [csproj:89](../../trunk/AKRS.Galaxy2.LogTest/AKRS.Galaxy2.LogTest.csproj#L89)。不能据配置文件存在断言运行时读取它；是否由外部库加载仍待确认。

[App.config:8](../../trunk/AKRS.Galaxy2.LogTest/App.config#L8)将 log4net 0.0.0.0–2.0.17.0 重定向到 2.0.14.0，而项目 Reference 标注1.2.15.0且 SpecificVersion=False；这是待核对的声明差异，不直接判定运行失败。

## 未完成项与验收

- 外部日志库真实过滤、排队、文件/UI写入和失败策略缺少可见实现。
- Log4Net.config 全部 appender 和实际加载位置、构建复制行为仍需专项验证。
- Properties生成资源未完整复核；未执行构建、版本绑定或日志运行试验。
- 后续隔离运行需核对实际输出条数、输出目录、权限失败以及关闭时是否刷盘；当前记录不算生产自动化测试通过。
