# 换片名称选择与网格状态一致性

23项受控检查，提取窗口8个原方法及AdapterEntity两个原方法，不修改方法体。真实List查找，控件为被动替身，持久化、料片构造依赖和槽位子实体初始化为替身。没有验证DevExpress事件触发顺序、反序列化或实际文件/设备。

## 名称与保存对象

[名称切换](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L353)对null直接返回；非空依次查晶圆配置和适配器配置。成功时新建tempTablet并绑定数组；两库同名且第一库匹配对象是晶圆类型时优先晶圆。两者均未匹配只提示，不清空此前tempTablet。

检查覆盖null、空字符串、缺失名称、两库同名、适配器成功及创建/映射刷新失败。适配器路径先赋新tempTablet再CreateAdapterEntity；创建失败时临时对象已替换、网格尚未更新，刷新失败时网格已经绑定新数组。

[Save](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L396)不重新校验选择名称，直接发布tempTablet。对空字符串/缺失名称依次调用原名称事件与Save，确认保存的是旧临时对象。这是方法组合风险，不证明真实UI可输入任意值或异常后必然继续保存；按钮门控和保存/运动失败见[前一专题](manual-wafer-change-review.md)。

[Load](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L286)列出晶圆和适配器名称，优先选择当前需料晶圆名；显式tabletName直接赋值。回退到非NullTablet时，代码只有在tempTablet.Name为null/空字符串时才给EditValue赋该名称，非空旧名称反而保留控件原值；回退的DataSource是单个对象，成功名称事件使用数组。测试记录这些实际条件，不按意图改写为非空判断。

控件替身赋EditValue不会自动派发事件。用手动调用名称事件检查后续创建，未据此声称实际Load期间存在或不存在重入。真实事件顺序需在目标控件版本验证。

## 网格状态与失败前缀

|原方法|先发生的状态变化|后续失败边界|
|---|---|---|
|[主行设Good](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L444)、[主行设None](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L464)|先改聚焦料片SlotState|晶圆InitTabletInfo或适配器子状态处理异常时已赋状态保留，后续刷新/绑定跳过|
|[槽位设Good](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L489)、[槽位设None](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L503)|通过AdapterEntity更新聚焦槽位|主聚焦行不是适配器时返回；槽位null由下层忽略，仍可走绑定|

[AdapterEntity.SetSlotState](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterEntity.cs#L57)对null直接返回；非null先设槽位状态再调用子项SetAllSlotState，异常转换成新的通用Exception，无InnerException。[SetAllSlotState](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterEntity.cs#L80)逐槽调用前者。子项具体算法为替身，不把这些检查算作整个适配器初始化验收。

[BindingAdapterData](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L407)依据当前聚焦行和AdapterState设置第二网格数据源，再刷新。上述四种按钮方法没有直接Save；这仅指本地方法，不排除真实控件或其他订阅的额外副作用。

## 局部事件绑定

已固化[名称切换](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L321)、[槽位焦点](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L407)、[槽位按钮](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L455)、[主网格数据源](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L509)、[主行按钮](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L571)、[Load](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L642)。焦点和数据源转发事件仅静态定位，运行期嵌套派发未测试。

## 验证与后续

`node scripts/test-wafer-selection.cjs`：13项选择/加载/保存组合，10项网格状态与失败处理，全部通过；输出原文和夹具哈希。[16段源码快照](wafer-selection-evidence.json)接入阅读器。

已补齐本地名称与临时对象、聚焦行及保存对象的关系。仍需真实配置/构造、绑定生命周期、映射控件刷新内部、设备SDK和现场恢复验收。下一步同步换片图和语义台账，再推进剩余模块缺口；整体29组仍部分复核。
