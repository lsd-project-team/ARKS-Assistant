# 加载配方：路径重置与失败状态

范围：加载既有配方的BarBtLoad_ItemClick，以及它调用ReLoadRecipe的顺序与边界。新建、复制、快捷键入口不因本次七项测试而视为已验收。

## 执行摘要

加载按钮 → 先取得旧CurrentRecipe → 显示选择窗口 → OK且所选非空 → 修改RecipeID → SaveMachineConfig → 旧配方为空或ID改变才ReLoadRecipe → 窗口Dispose → 请求后台刷新。同ID也保存机器配置，但跳过六类程序的重新初始化。取消对话框跳过整个OK分支，包括本方法中的显式Dispose和刷新。

入口证据：[Designer:670](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L670) → [完整加载方法:804–839](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)。[配置字段:25–37](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L25)中RecipeID为Guid，CurrentRecipe通过当前ID查仓库。oldRecipe是对话框显示前取得的对象引用，不是独立保存的ID快照；本轮替身场景未模拟对话框期间并发修改旧对象。

## 原入口的七项受控检查

| 场景 | 方法可观察次序 | 内存RecipeID与退出边界 |
| --- | --- | --- |
| Cancel | dialog | 保留旧ID；不进入显式Dispose/刷新语句 |
| OK、所选null | dialog→错误提示→Dispose→刷新 | 保留旧ID，没有Save/重载 |
| OK、同ID | dialog→Save→Dispose→刷新 | 不重载；不能据此认为外部修改的配方文件已重新读取 |
| OK、不同ID | dialog→Save→重载→Dispose→刷新 | 新ID；Save在重载之前 |
| 旧配方null | dialog→Save→重载→Dispose→刷新 | 新ID |
| Save抛异常 | dialog→Save→异常外抛 | 已赋新ID；跳过重载和后续清理，没有本地回滚 |
| 重载抛异常 | dialog→Save→重载→异常外抛 | 已赋新ID；跳过Dispose/刷新，没有本地回滚 |

复现：[test-recipe-load-entry.cjs](../../scripts/test-recipe-load-entry.cjs)。原事件方法完整提取，窗口、保存、重载、提示与后台服务为替身。测试验证入口执行顺序、内存ID和异常传播；不证明Save成功落盘，不把未执行Dispose等同于已测得资源泄漏，也不验证真实UI/SDK。

## 六类程序的路径与实例重置

[InitProgramNodes:124–132](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)按以下顺序分别GetInstance并调用初始化：

| 次序 | 目标 | 源码行为 |
| --- | --- | --- |
| 1 | ProductConfiguration | [71–75](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L71)：新RecipeDirPath/ProductConfiguration.json，再instance=null |
| 2 | TransportProgram | [71–75](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L71)：TransportSystemProgramFilePath，再instance=null |
| 3 | BondProgram | [216–220](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L216)：BondProgramFilePath，再instance=null |
| 4 | System1Program | [56–60](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Program.cs#L56)：DispenseProgramPath，再instance=null |
| 5 | WaferSystemProgram | [70–90](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L70)：按配置先清供片记忆，再更新路径/清实例；catch重新抛Exception |
| 6 | ProcessDomain | [37–41](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L37)：ProcessProgramFilePath，再instance=null |

GetInstance发生在各Init前；已有[随附Singleton读取实现](persistence-save-contract-review.md)表明实例为空时可先按当时静态FilePath触发Load。因此不能把这六行看成不含读取/构造副作用的纯赋值批处理。路径更新是逐项进行的，不是事务；第五步清供片记忆若抛异常，前四类可能已更新，而第五类路径重置及第六步尚未执行。这里是源码可达的部分完成状态，不是已观测到现场损坏。

## 重载方法的两种异常边界

[ReLoadRecipe:137–203](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L137)先设PrInitSuccess=false、禁用界面并显示提示，设置任务名、清dock、执行InitProgramNodes；这些都在try之前。若该阶段异常，后面的catch/finally不覆盖它，加载入口也没有回滚或finally。

try内：离线直接置PrInitSuccess=true后return并执行finally；在线关闭旧视觉方案、创建新方案、获取PR列表、按名称初始化。找不到某个PR仅记日志，仍可能执行最后的PrInitSuccess=true；不要把该标志解释为列表中每个模板均成功存在。try内异常提示并日志后重抛，finally恢复界面。完整视觉和供片子链复用[既有重载源码审计](recipe-initialization-source-review.md)。入口七项检查之外，下节继续验证重载方法本身；下层SDK和设备仍使用替身。

## 重载内部的十项原方法检查

[test-recipe-reload.cjs](../../scripts/test-recipe-reload.cjs)提取完整ReLoadRecipe（137–212行），包括return之后当前不可达的重启语句。为了兼容C#5编译器，五处日志插值改为等价常量/拼接，保留GetName求值；控制分支与catch/finally不改。界面、视觉SDK、日志、PR仓库及InitProgramNodes为替身，不读真实配方、不运行真实视觉。

| 场景 | PrInitSuccess | Enabled / 提示Visible | 受控结果 |
| --- | --- | --- | --- |
| 在线正常 | true | true / false | close→create→names→find→algorithm→dispense |
| 离线正常 | true | true / false | 仍先init，跳过视觉并执行finally |
| PR仓库返回null | true | true / false | 跳过algorithm，仍到dispense及置就绪 |
| dock清理异常 | false | false / true | try前外抛，不到init和视觉 |
| 程序初始化异常 | false | false / true | try前外抛，不到视觉 |
| 关闭旧方案异常 | false | true / false | catch提示、重抛，finally恢复UI |
| 创建新方案异常 | false | true / false | 同上，未到names |
| 获取名称列表异常 | false | true / false | 同上，未到find |
| 算法初始化异常 | false | true / false | 同上，未到dispense |
| 离线但程序初始化异常 | false | false / true | 离线判断在init之后，不能绕过该失败 |

十项均通过；假定测试中的提示、日志和界面属性本身不抛异常。没有据此验证六个Init内部、SDK释放、实际文件或恢复后的生产动作。缺模板仍置就绪属于源码控制流结论，不据此断言现场一定允许生产；后续还有独立启动门控。

## 当前结论与剩余项

已补齐加载入口七种结果、同ID跳过重载、保存先于重载和六类路径可能部分更新的证据。仍待取得真实配方样本，验证菜单状态、并发编辑、实际JSON读取与保存、缺失PR、初始化中途失败后的人工恢复。生产源码未改；不把静态复核或替身通过计作整机验收。

## 配方切换时序图与逐条溯源

[交互时序图](recipe-switch-sequence.html) · [图规范](recipe-switch-sequence.archify.json) · [交付记录](recipe-switch-sequence-status.json)

图展示确认非空选择后的主要调用与条件分支，不表示所有分支同次执行。同ID保存后跳过重载。初始化后才检查离线，离线跳过视觉。初始化异常经重载传播回入口，非程序模块直接调用界面。try内异常恢复UI并重抛，不继续成功尾部。取消、空选择及保存异常见前文入口矩阵。

视觉参与者合并SDK、仓库与算法。LoadDispensePr当前为空实现，未单独画节点。非事务结论结合前文六类初始化源码；返回箭头不是新增调用。

| 消息 | 含义 | 源码 |
| --- | --- | --- |
| save | OK 且非空：赋 ID → 保存 | [809–814](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L809) |
| same | 同 ID：保存后跳过重载 | [816–825](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L816) |
| invoke | 旧配方为空 / ID 不同 → 重载 | [816–825](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L816) |
| init | 未就绪 → 禁用 UI → 清 dock → 初始化 | [139–149](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L139) |
| reset | 顺序重置路径/实例；非事务 | [124–132](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124) |
| preerror | 初始化异常：try 前外抛，未恢复 UI | [139–151](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L139) |
| close | 在线：关闭 → 创建；离线跳过视觉 | [153–167](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L153) |
| pr | 逐项查找 PR；存在则初始化算法 | [171–178](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L171) |
| missing | 缺 PR 仅日志；异常则提示、重抛 | [175–195](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L175) |
| return | 正常置就绪返回；try 内退出均恢复 UI | [189–203](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L189) |
| finish | 成功尾部：Dispose → 激活后台刷新 | [834–837](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L834) |

Archify九项检查、0错误0警告；四种桌面尺寸通过；最小浅色与最大深色截图已审查。不计为设备验收。
