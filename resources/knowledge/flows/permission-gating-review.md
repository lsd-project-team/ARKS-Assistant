# 权限与编辑事件门控复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。机器可复核证据见 [permission-gating-audit.json](permission-gating-audit.json)。本轮只读取 `trunk` 源码，没有执行登录、数据库、VM、设备或生产 UI。

## 角色和 AOP 规则

`CommonEnum.cs:50–69` 将角色编码为 Admin=1、Engineer=2、Operator=3，数字越小权限越高。`Machine.cs:118–127` 在没有登录用户时返回 3，因此匿名状态按 Operator 处理。

`MethodAopAttribute.OnEntry`（`MethodAopAttribute.cs:28–59`）只对第二个参数为 `ItemClickEventArgs` 且其 Item 为 `BarButtonItem` 的调用读取 `Tag` 并比较角色。空 Tag 默认按 Engineer；当 `requiredRole.CompareTo(currentRole) < 0` 且 `IsPermissionOpen` 为 true 时弹窗并设置 `FlowBehavior.Return`。同一 AOP 对 `SimpleButton` 的分支只写操作日志，没有设置权限拒绝。

## 编辑程式入口

主界面 `BtEditProduct` 在设计器 `UcMainSystem.designer.cs:558–565` 没有显式 `Tag`，事件进入 `UcMainSystem.cs:368–401` 后只检查工作状态、DryCycle 和配方对象/名称；这里没有 `CurrentRole`、`CurrentRoleLevel` 或 `IsPermissionOpen` 检查。因此源码能确认编辑入口有运行状态门，但不能确认它对角色做了入口级限制。

编辑控件类在 `UcEditProductProgramming.cs:81` 标记了 `MethodAopAttribute`，但其四个操作按钮都是设计器中的 `SimpleButton.Click` 事件：Start `:869`、Close `:923`、Reset `:936`、Save `:1066`。这些处理器没有直接角色检查；按当前 AOP 分支，SimpleButton 事件只进入日志路径，不能从该属性推导出角色拒绝。参数控件另有独立门控：`UcProgramArgs.cs:1703–1724` 先检查 `IsWorking` 与 `AllowUserChange`，再按 `CurrentRoleLevel <= RoleLevel` 决定控件是否可编辑。

## 登录、自动登出和配置开关

`UcMainSystem.cs:1193–1200` 的登录按钮在登录对话框返回 OK 后写入 `RuntimeProvider.CurrentLoginUser`。用户管理入口 `:1208–1223` 另行要求当前用户存在且角色为 Admin；自动刮胶入口 `:1796–1812` 也有显式 Admin 检查。`Machine.Operate.cs:640–657` 的自动登出只清除 `RoleID < 3` 的已登录用户；Operator 不进入这条自动登出条件。`MachineSoftwareConfiguration.cs:114–115` 的 `IsPermissionOpen` 默认值为 true，但该配置会使 AOP 角色门整体失效，具体配置保存与运行时变更仍待验证。

## 结论和边界

- 当前源码证明了三种不同层次：主编辑入口的状态门、参数控件的角色/可编辑门、少数按钮的显式 Admin 门。
- 不能把 `MethodAopAttribute` 的类标注当作整个编辑窗口的角色锁；其权限分支只覆盖特定 BarButtonItem 事件，而编辑窗口的主要操作使用 SimpleButton。
- 本轮没有证明 Fody 是否已织入、运行时控件 `Enabled` 状态、登录数据源、权限配置持久化或真实操作员路径。

## 可点击源码证据

- [MethodAopAttribute.cs:28–59](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/MethodAopAttribute.cs#L28)
- [CommonEnum.cs:50–69](../../trunk/AKRS.ZX2200/Infrastructure/Models/Enums/CommonEnum.cs#L50)
- [Machine.cs:118–127](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L118)
- [UcMainSystem.designer.cs:558–565](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L558)
- [UcMainSystem.cs:368–401](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L368)
- [UcEditProductProgramming.cs:81](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs#L81)
- [UcEditProductProgramming.cs:869–874](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs#L869)
- [UcEditProductProgramming.cs:923–936](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs#L923)
- [UcEditProductProgramming.cs:1066–1078](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs#L1066)
- [UcProgramArgs.cs:1701–1724](../../trunk/AKRS.ZX2200/SupportFeature/Parameters/UcProgramArgs.cs#L1701)
- [Machine.Operate.cs:640–657](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L640)
