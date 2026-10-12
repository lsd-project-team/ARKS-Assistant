# 组件演示：定时随机曲线，不是设备压力采集

更新：2026-09-28。部分复核；未运行界面。

## 流程摘要

项目文件名为 AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj，目录及程序集名仍为 AKRS.Galaxy2.Component.TestDemo。[项目:8](../../trunk/AKRS.Galaxy2.Component.TestDemo/AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj#L8)声明 Library，StartupObject 为空；[Program:17](../../trunk/AKRS.Galaxy2.Component.TestDemo/Program.cs#L17)含 Run(new FrmRealtimeCurve())，但不能据 Main 存在宣称类库默认可执行。

若窗体被实例化：InitializeComponent → ChartService.InitChartControl → 设置 Y 范围0到20 →启用 timer1 →每次 Tick 生成随机数和时间戳→向第一个系列提交一个点→清除/新增当前时间参考线→调整X轴显示范围。窗体进入 Dispose 时释放 components 容器。

## 触发、顺序与数据

|步骤|实际行为|源码|
|---|---|---|
|构造|初始化图表，SetYRange(0,20)，timer1.Enabled=true|[FrmRealtimeCurve:22](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.cs#L22)|
|调度|Windows.Forms.Timer 创建于 components；Interval=1000，Tick 绑定处理函数。该设置不等于硬实时采样周期保证|[Designer:36–47](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.Designer.cs#L36)|
|每次回调|new Random，Next(10)，DateTime.Now 与随机数构成 SeriesPoint，AddPoint 到 Series[0]|[Tick:37–42](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.cs#L37)|
|第二随机数|Next(20) 构造 p2，但后续没有将 p2 添加到任何系列，不能画成第二路曲线输入|[44–46](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.cs#L44)|
|参考线和范围|清除垂直常量线，按 dt 加 current value 线，AutoSetXWholeRange(chart,1,5)|[47–51](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.cs#L47)|
|释放|disposing 且 components 非空时调用 Dispose，然后 base.Dispose|[Designer:14](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.Designer.cs#L14)|

界面系列名 force value、标题 Bond force 只是标签，见 [Designer:57–65](../../trunk/AKRS.Galaxy2.Component.TestDemo/FrmRealtimeCurve.Designer.cs#L57)。已读输入来自随机数，不来自压力传感器或运动控制器，不能把图表标题当作生产采集证据。

## 输出、依赖与失败边界

有效输出是图表点/参考线/显示范围的服务调用。未见该窗体文件/数据库写入、网络API、持久队列或设备读取。没有点数上限、数据清理或保存结果的本地实现；ChartService内部是否截断点数仍未知。回调没有局部catch或重试，也没有检查Series[0]是否存在，不能保证每次回调成功。

[项目:41–60](../../trunk/AKRS.Galaxy2.Component.TestDemo/AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj#L41)声明 Component.Simple、Infrastructure DLL 和 DevExpress Charts 等引用；trunk 排除bin/obj的C#搜索未找到 class ChartService，其初始化、加点和坐标范围行为在本轮仍属外部服务边界。AutoSetXWholeRange 的1和5不能仅凭名字解释为已证实的时间单位。

## 待完成

- 真实加载/调用方未证明；显式窗体名称搜索只命中自身和Program，不能据此排除动态加载。
- ChartService实现、外部库兼容性和全量生成资源未复核。
- 未执行构建、UI刷新/关闭或长期内存行为测试；当前不算生产压力监控验证通过。
- 本专题用于标记辅助演示边界，不纳入自动生产工作步骤图。
