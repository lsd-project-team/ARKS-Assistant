# ZX2200 设置提交、实例重载与示教入口

更新：2026-09-28。范围：trunk指定方法的静态复核；不执行设备、真实JSON保存或第三方UI。

## 工作流摘要

- 常规TransportUnitGeneral节点创建UcTransportUnitFrame，内部创建TU、基板、基岛三个控件；异形分支创建FrmTransportUnitEdit，不走相同控件链。
- 基板/基岛控件构造时缓存当前子配置引用。部分CheckedChanged/EditValueChanged事件即时写状态或调用各自Save；这些子控件Save主要把界面值写入内存，并非每次都执行产品配置落盘。
- 显式Confirm按TU.Save → Substrate.Save → Module.Save → 当前ProductConfiguration.GetInstance().Save顺序调用。过程中没有局部回滚；不能将任一步返回视为所有操作已原子完成。
- 编程界面“Start”先调用可选IProgrammingControl.Confirm，再Start(true)；这不是Machine.Start自动生产入口。“Save”按钮也执行可选Confirm，随后弹“保存成功”；Confirm抛异常时只提示异常信息。
- 配方重载的InitProductConfiguration只是更新FilePath并清instance，不是该方法自身完成读取。外部Singleton实现尚未取得；不能据此推断缺文件、反序列化、迁移、线程安全或事务行为。

## 核验边界

树节点切换、位置示教分派及代表状态事件已在下文核对；其余页面、控件缓存生命周期和完整启动准备仍未全部验收。本专题不把控件缓存等同于已发生跨配方错写；需要证明旧控件存活、实例实际变更和保存可达后才能确认该运行问题。

## 进一步确认的分支

- 树节点切换先Controls.Clear，再按Tag创建页面；已读入口没有先调用旧selectedControl.Confirm。这里不推断第三方Controls.Clear是否Dispose控件。
- TU子控件在Load事件取得配置引用；基板/基岛在构造时取得。必须区分这些生命周期，不能统称都在构造时绑定。
- 普通基岛多实例复选框：首次加载返回；选中置ModulePosition.UnAble及IsMultiple=true，取消置ForBidden及false，然后刷新步骤列表并调用子控件Save。它改变后续示教门控，不等于完成新阵列示教。
- 框架/基板/基岛位置示教先检查IsNormalOrderAssistant；框架在线时还检查ChangeTouchDownAssistance返回。窗口返回OK后可递归调用Start()，是示教界面内继续分派，不是Machine.Start生产任务启动。位置示教内部Save的数量/坐标同步见配置编辑专题。
- Start()有自己的try/catch并提示异常，但按钮调用Confirm发生在进入Start之前，因此不能用Start的catch保护Confirm失败。
- 常规GetAssistantResult只检查状态列表是否有UnAble；IsNormalOrderAssistant在未全部完成时查名称，再检查目标前的UnAble。名字不存在时IndexOf得到-1，循环不会执行并返回true。这是该方法的静态语义，不代表正常界面的固定名称必然触发此情况。异形完成判断转调AssistantSuccess，未在本轮扩展。

## 原方法隔离验证

运行 `node scripts/test-config-submit.cjs`，8项通过。覆盖三个子提交→产品Save顺序、子提交/最终保存失败的部分副作用、Confirm失败阻止Start且向外传播、Save按钮捕获异常，以及非IProgrammingControl或null的可选调用。见[测试报告](config-submit-test.json)。

特别注意：非IProgrammingControl对象可在未调用Confirm的情况下显示“保存成功”。是否对应实际可选页面及其是否另有保存路径，应逐页核实，不能将此条件测试直接声称为所有页面保存失败。

测试提取原方法；C#5只将空条件接口调用展开为等价显式null检查。子控件Save、单例、Start和消息框均为受控替身，无实际UI、硬件或JSON保存。

## 源码阅读器直达

- [submit-frame-confirm：UcTransportUnitFrame.cs:33–56](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-frame-confirm)
- [submit-module-binding：UcModule.cs:26–55](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-module-binding)
- [submit-module-change：UcModule.cs:93–140](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-module-change)
- [submit-sub-binding：UcSubstrate.cs:40–62](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-sub-binding)
- [submit-sub-save：UcSubstrate.cs:112–133](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-sub-save)
- [submit-tu-save：UcTransportUnit.cs:103–140](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-tu-save)
- [submit-tu-binding：UcTransportUnit.cs:308–331](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-tu-binding)
- [submit-editor-switch：UcEditProductProgramming.cs:453–475](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-editor-switch)
- [submit-editor-create：UcEditProductProgramming.cs:718–734](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-editor-create)
- [submit-editor-start：UcEditProductProgramming.cs:869–874](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-editor-start)
- [submit-editor-save：UcEditProductProgramming.cs:1066–1078](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-editor-save)
- [submit-teach-tu-sub：UcEditProductProgramming.cs:1573–1643](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-teach-tu-sub)
- [submit-teach-module：UcEditProductProgramming.cs:1679–1697](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-teach-module)
- [submit-teach-catch：UcEditProductProgramming.cs:2093–2100](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=submit-teach-catch)
- [submit-assistant-result：TransportUnitConfig.cs:249–274](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-assistant-result)
- [submit-assistant-order：TransportUnitConfig.cs:280–331](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-assistant-order)
- [submit-reset-instance：ProductConfiguration.cs:71–83](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=submit-reset-instance)
