# 原工程资源序列化、嵌入与回读核验

16 个工程在原 Debug|AnyCPU 下经安装的 MSBuild PrepareResourceNames 评估，声明的 388 个 .resx 均存在。原生 Framework CLR 4.0.30319.42000 成功序列化全部资源，共 1498 个数据项、12,260,102 字节；真实 DevExpress.Data/Utils v21.2 的请求与加载身份均为 21.2.7.0。所有图像文件、资源文件与相关 SDK 已冻结。

全部 1410 份原 Compile 源码保持不变，16 个隔离原源码产物成功嵌入 387 个中性资源；另生成一个 cs 卫星程序集。17 个产物原生回读逐项核对资源清单、388 个流的字节 SHA256、1498 个键及反序列化类型。资源序列化、全部17次编译与回读的重放均真实退出0，资源流和程序集哈希一致。源工程引用仍沿用上一轮的新源码产物；本次没有把所有引用进一步切换为资源版程序集。

原文件 FrmS2DispensePlateAssistant.cs.resx 被 MSBuild 识别为 cs 文化资源，唯一数据项为 behaviorManager1.TrayLocation；生成的 AKRS.ZX2200.resources.dll 版本1.5.0.0、文化cs。命名评估不能证明窗口故障，本轮未打开该窗口。仅数据项被写入 .resources，设计器 metadata 不作为运行时资源嵌入。

最初三处准备/测试脚本问题保留：序列化388个文件已经成功，OrderedDictionary 的 Measure-Object 页脚却失败；卫星准备错误地在排除Main本身的依赖映射中查找Main，且随后的批次因无输入清单失败；回读名称比较的 -join/-ne 优先级错误。均在修正工具脚本后成功，未修改生产源码；最初终端stderr没有完整落盘，不把空stdout日志当完整失败日志。首轮388个资源结果与脚本快照已冻结。

新增 1090 项冻结输入，绑定父2088项，共 3178 项。见[测试清单](project-resources-test.json)、[审计](project-resources-audit.json)和[进度](project-resources-progress.json)。1498 是资源数据项数，不是新增业务断言；原1410/98/124、1328/278/119与旧122文件失败记录、40专题/3817快照保持。

5个工程声明的 licenses.licx 已单独登记并冻结，尚未执行许可证编译。原工程 Win32 图标/清单/版本资源、targeting pack、完整MSBuild/restore、Fody/PostSharp织入和主入口/UI/轴/相机/设备仍待验收。Main与PR的Fody配置和现有nuget.g.targets只作输入证据，存在配置不等于织入已执行。上一轮VM运行依赖失败仍未解决。16工程、29组、1436个C#文件及13项整体任务仍未完成。
