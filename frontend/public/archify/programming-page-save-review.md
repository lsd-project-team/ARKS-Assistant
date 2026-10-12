# ZX2200 编程页面保存路径复核

更新：2026-09-28。先读trunk，再登记结论；不执行生产程序或设备。

## 工作流摘要

编程树选节点 → 创建selectedControl → 页面内部可即时修改/保存 → 顶部Save调用可选IProgrammingControl.Confirm → 未抛异常则显示成功。顶部Start同样先Confirm，再进入示教分派。因此顶部按钮不是所有页面的唯一保存入口，也不能凭其成功提示证明所有页面刚刚执行了Save。

[页面盘点](programming-page-inventory.md)包含33处创建、32种页面主类型：20种主类直接声明IProgrammingControl，12种未直接声明。盘点是限定范围的声明与调用候选检查，不是继承解析、全部方法复核或运行覆盖率。

## 未直接声明接口的12种主页面

|分类|页面|已读主文件实际行为|边界|
|---|---|---|---|
|7种说明页|UcConfigurationDescription、UcPPToolsDescription、UcESToolsDescription、UcFlipToolsDescreption、UcDispenserDescription、UcTransportUnitDescription、UcComponentsDescription|主文件仅InitializeComponent；Flip另有实际语句为空的RefreshControl|未因接口缺失认定数据丢失；Designer/外部基类行为未作完整运行验收|
|配置展示|UcConfiguration2|绑定吸嘴架、顶针槽、分配树和名称标签；焦点事件记录节点索引|主文件未见Save调用；不据此断言所有绑定控件绝无其他修改途径|
|异形对象编辑|FrmTransportUnitEdit|新增对话框OK、删除确认、复制OK和清空按钮各有ProductConfiguration.Save调用|子对话框、深拷贝、其他子控件与异常后的状态仍需展开|
|焊点列表|UcAddBondPosition|新增、删除确认、复制后调用产品Save；双击改名另有配置/制程/PR调用|删除确认取消后，若有TU仍可进入InitializeTS询问；并非取消即结束整个事件。改名见上一专题|
|点胶列表|UcAddEpoxyApplication|新增、删除、库选择各有保存；构造调用的RefreshControl本身也Save|根据S2点胶配置且当前S2选择决定BondProgram，否则System1Program；刷新并非纯只读|
|焊后检测列表|UcAddPostBond|新增委托对话框；删除确认后移除当前程式名称并保存Repository及BondProgram；库管理后补入当前配方项目并Save|新增对话框内部持久化本轮未展开；列表移除不等于删除底层视觉库|

## 点胶列表的保存顺序

- 构造：InitializeComponent → 设置父刷新回调 → RefreshControl。后者先绑定当前工位数据，再调用对应Program.Save，最后刷新控件。
- 新增OK：追加名称 → 对应Program.Save → RefreshControl（再Save）→ 父节点刷新。取消新增不追加名称，但仍RefreshControl并调用Save。
- 删除无选中项：提示并立即返回。选中项确认Yes则Remove并Save；选择No不Remove，但之后同样RefreshControl并Save。
- 库选择：对话框返回的DsSetting为null则返回；否则按工位去重添加名称，依次Repository.Save → System1Program.Save → BondProgram.Save → RefreshControl → 父刷新。代码没有以DialogResult.OK作为这一分支的门控。
- 所读方法没有局部catch；保存抛异常会跳过其后的刷新或回调。这里只确认调用顺序，不保证外部Save一定落盘或具有事务性。

## 验证与生产边界

`node scripts/test-epoxy-list-save.cjs`：9项原方法隔离断言通过，覆盖S1/S2分派、新增/删除确认及取消、无选中项、刷新Save抛错。见[结果](epoxy-list-save-test.json)。两条插值消息降级为C#5表达式；其余方法语句不改。对话框、程序属性、枚举场景及Save计数为替身，没有执行真实序列化、第三方控件或硬件。

取消后调用Save不等于取消的新增/删除仍发生，也不证明现场文件被错误修改。这里取消阻止名称列表的对应增删，但不阻止后续刷新中的保存调用。

## 下一步与缺失项

- 继续20种直接声明接口页面的Confirm方法体及其委托保存，不能以接口名称替代语义。
- 补齐新增对话框、Repository与外部Singleton的具体加载/保存契约，以及配置变化与自动生产对象的连接。
- 用认证配方和隔离UI验证取消、保存失败、旧控件生命周期；所有模块仍部分复核，不修改生产源码。

## 精确源码入口

- [page-epoxy-refresh：UcAddEpoxyApplication.cs:26–71](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=page-epoxy-refresh)
- [page-epoxy-add：UcAddEpoxyApplication.cs:78–103](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=page-epoxy-add)
- [page-epoxy-delete：UcAddEpoxyApplication.cs:110–145](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=page-epoxy-delete)
- [page-epoxy-library：UcAddEpoxyApplication.cs:152–195](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=page-epoxy-library)
- [page-epoxy-events：UcAddEpoxyApplication.Designer.cs:154–188](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=page-epoxy-events)
- [page-post-add-delete：UcAddPostBond.cs:93–133](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-post-add-delete)
- [page-post-library：UcAddPostBond.cs:140–164](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-post-library)
- [page-post-events：UcAddPostBond.Designer.cs:173–207](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-post-events)
- [page-bond-add-delete：UcAddBondPosition.cs:163–215](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-bond-add-delete)
- [page-bond-copy：UcAddBondPosition.cs:222–270](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-bond-copy)
- [page-bond-events：UcAddBondPosition.Designer.cs:157–177](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=page-bond-events)
- [page-shape-add-delete：FrmTransportUnitEdit.cs:114–172](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=page-shape-add-delete)
- [page-shape-copy：FrmTransportUnitEdit.cs:179–212](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=page-shape-copy)
- [page-shape-clear：FrmTransportUnitEdit.cs:286–293](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=page-shape-clear)
- [page-shape-events：FrmTransportUnitEdit.Designer.cs:121–154](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=page-shape-events)
- [page-config-overview：UcConfiguration2.cs:20–166](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-config-overview)
- [page-description-UcConfigurationDescription：UcConfigurationDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcConfigurationDescription)
- [page-description-UcPPToolsDescription：UcPPToolsDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcPPToolsDescription)
- [page-description-UcESToolsDescription：UcESToolsDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcESToolsDescription)
- [page-description-UcFlipToolsDescreption：UcFlipToolsDescreption.cs:1–41](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcFlipToolsDescreption)
- [page-description-UcDispenserDescription：UcDispenserDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcDispenserDescription)
- [page-description-UcTransportUnitDescription：UcTransportUnitDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcTransportUnitDescription)
- [page-description-UcComponentsDescription：UcComponentsDescription.cs:1–16](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=page-description-UcComponentsDescription)
