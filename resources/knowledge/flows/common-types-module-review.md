# Common.cs：数据类型声明边界

更新：2026-09-28。部分复核。

2026-09-29配置核对：本机MSBuild求值的Debug/Release AnyCPU均未将此文件纳入Compile。下述声明结论只描述仓库文件，不证明当前产物包含这些类型。详见[编译项基准](msbuild-evaluation-review.md)与[影响范围](compile-scope-impact.md)。构建期间动态添加项及其他构建环境仍需检查。

[Common.cs:12](../../trunk/AKRS.ZX2200/Common.cs#L12)定义 AKRS.ZX2200.Point，仅含 float X/Y 自动属性；[28行](../../trunk/AKRS.ZX2200/Common.cs#L28)定义 ChipTypeAndThickness，含 string Type 和 float Thickness。文件没有方法、事件、调度、校验或持久化逻辑，不能单独画成自动化步骤。坐标和厚度的物理单位也未在类型中编码。

对 trunk C# 排除bin/obj的 ChipTypeAndThickness 与完全限定 AKRS.ZX2200.Point 搜索只发现前者定义，没有发现显式业务调用。名称检索不是符号绑定、反射或序列化使用的完备证明；Point存在同名框架类型风险，因此不声明全工程无调用或可删除。

待完成：编译语义级引用检查、动态类型/序列化使用核查、最终编译项验证。当前只确认两个声明的结构，不新增虚构调用关系，也不代表芯片厚度业务已全部解析。
