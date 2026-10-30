# 登录会话与权限配置边界复核

复核日期：2026-10-06。状态：`source-and-binary-metadata-confirmed`。机器可复核证据见 [permission-session-audit.json](permission-session-audit.json)。本轮只读取宿主源码、权限配置源码和仓库中的 UserManager DLL 元数据/IL，没有连接 SQL、打开登录窗口或执行用户管理方法。

宿主 `UcMainSystem.cs:1195–1199` 创建外部 `FrmLogin`，仅当 `ShowDialog()` 返回 `OK` 时把 `frmLogin.CurrentUser` 写入 `RuntimeProvider.CurrentLoginUser`。`RuntimeProvider.cs:38` 的当前用户是进程级静态属性；源码没有声明启动恢复、线程同步或持久化逻辑。用户管理按钮在宿主源码中另有 Admin 角色门。

对哈希固定的 `AKRS.Galaxy2.UserManager.dll` 做只读 Mono.Cecil 检查得到以下边界：登录处理器先校验账号/密码非空，再调用 `UserService.UserVerify`；验证结果还会检查 `User.Disabled`，然后写入 UserManagerContext.UserCache、设置 CurrentUser、保存 `lastUserAccount` 配置并返回 OK。`UserVerify` 通过 `UserDal.QueryByAccount` 查询用户和 Role，并用字符串相等比较存储的 Password 与输入值。`BaseDAL<T>` 构造函数携带 `Server=localhost;Database=UserManager;Trusted_Connection=True;`，创建 SqlSugar 客户端，调用 `CreateDatabase`，空表时执行 CodeFirst 初始化。上述是二进制元数据观察，没有实际触发连接或建库。

权限配置 `MachineSoftwareConfiguration.cs:115` 将 `IsPermissionOpen` 默认设为 true，静态构造函数在第 168 行把继承的 `FilePath` 设为 `Path.Combine(PathConfig.DeviceDirPath, "MachineSoftwareConfiguration.json")`。宿主在 `UcMainSystem.cs:680` 和 `Machine.cs:400` 调用 `Save()`。已有的 [Singleton 隔离探针](singleton-load-probe-review.md)用安全测试类型确认了合法 JSON 的反序列化、`Load()` 的引用替换，以及缺失/损坏 JSON 的默认对象回退；它没有执行 `MachineSoftwareConfiguration` 本身或设备路径。`Machine.Operate.cs:648` 的自动登出只在超时且 `RoleID < 3` 时清空当前用户。

结论是：登录用户来自外部 UserManager 的 SQL 查询，成功后只进入进程内静态缓存；权限总开关默认打开并通过继承的配置单例保存。通用单例的失败回退已有隔离证据，但真实设备配置路径、数据库账号、密码安全和操作员路径仍未验收。

## 可点击证据

- [UcMainSystem.cs:1195](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1195)
- [RuntimeProvider.cs:38](../../trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs#L38)
- [MachineSoftwareConfiguration.cs:115](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs#L115)
- [MachineSoftwareConfiguration.cs:168](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs#L168)
- [ZX2200PathConfig.cs:308](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L308)
- [UserManager DLL](../../trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.UserManager.dll)
- [UserManager IL 检查脚本](../../.archify-work/inspect-user-manager-il.ps1)
- [permission-session-audit.json](permission-session-audit.json)
