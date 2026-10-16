# Akrs.ChangeJson：配置类型命名空间迁移工具

更新：2026-09-29。限定范围部分复核；原更新方法已作临时文件隔离检查，未运行产品界面或改写生产 JSON。

## 原更新方法的隔离验证

`node scripts/test-changejson-update.cjs`提取完整BtUpdateJson_Click原文，使用真实Task及临时文件执行9项检查。测试Task包装只捕获原方法丢弃的句柄以观察异常；Invoke使用同步替身，不代表WinForms消息循环。见[原文、文件哈希与场景回执](changejson-update-test.json)。

|场景|观察结果|
|---|---|
|常规带空格$type文本|按映射替换|
|冒号后无空格|未匹配，内容不变|
|映射缺失|提示缺失，内容保留|
|相同简单类名有两个映射|使用列表第一项|
|第二个文件不存在|第一个已改写，第三个未处理，任务异常结束|
|Invoke替身抛异常|尚未写回当前文件|
|Invoke期间受控增加JsonList项|当前文件先写入，随后枚举抛InvalidOperationException|
|文件允许读取但锁定写入|已经显示映射提示，写入抛IOException，内容保持原值|
|同一窗口两个任务交错，期间替换映射项|第二任务先写Other命名空间；第一任务恢复后用旧快照写New，覆盖第二任务结果；两任务均成功|

并发用两个ManualResetEventSlim明确控制：第一任务已经读取原文件并取得旧映射对象，在Invoke处等待；测试线程将映射列表项替换为新对象，再从同一窗口再次启动并等待第二任务写完；最后释放第一任务。文件前后内容均实读确认，无需靠Sleep猜测顺序。此场景证明原方法不检测读后文件变化或旧映射快照，不证明实际界面能以同样顺序操作，也未验证所有并发交错。

文件锁场景验证写入失败，不等同于磁盘满、断电或ACL权限测试。列表变化在明确检查点注入，不证明真实UI竞争频率。另已完成[反射辅助类7项检查](changejson-reflection-review.md)。

## 流程摘要

这是操作员点击触发的配置迁移工具，不是设备自动生产循环。Main 打开 FrmMain，Load 装入迁移控件；用户选程序目录、选行反射类名及命名空间，再选 JSON 根目录；点击更新后后台任务逐文件读取、匹配类型文本、查找映射、显示提示并覆盖原文件。按钮之间没有自动串联或强制前置顺序。

## 执行步骤与证据

|步骤|实际行为|源码|
|---|---|---|
|入口|Application.Run(new FrmMain())|[Program.cs:16](../../trunk/Akrs.ChangeJson/Program.cs#L16)|
|窗口加载|创建 UcChangeNameSpace 并添加到页签|[FrmMain.cs:19](../../trunk/Akrs.ChangeJson/FrmMain.cs#L19)、[事件绑定:71](../../trunk/Akrs.ChangeJson/FrmMain.Designer.cs#L71)|
|选程序目录|仅当前目录匹配 AKRS.ZX2200.exe，并非枚举所有 DLL|[BtOpenDllDir_Click:50](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L50)|
|反射|对选中行先加载相对路径 AKRS.Galaxy2.Infrastructure.dll，再加载选中程序；GetTypes 收集 IsClass 的简单名称和命名空间|[BtReflectObject_Click:76](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L76)|
|选 JSON|递归枚举 *.json，保存到 JsonList|[BtReadJson_Click:107](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L107)|
|更新入口|Task.Run 遍历整个 JsonList，ReadAllText 后执行正则匹配；不读取表格选中行|[BtUpdateJson_Click:132](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L132)|
|映射分支|按简单 ClassName 的 Find 第一项查找；缺失仅提示，找到则先提示、再字符串替换|[查找与替换:149](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L149)|
|逐文件结束|WriteAllText 写回原路径；没有匹配或找不到映射仍可走到写入，没有显式完成通知|[覆盖:175](../../trunk/Akrs.ChangeJson/UcChangeNameSpace.cs#L175)|

四个按钮绑定见 UcChangeNameSpace.Designer.cs 第 89、161、211、227 行。Data.cs 第32–35行定义路径字段，ClassNameSpace.cs 第32–42行保存简单类名和命名空间。

## 输入、输出与依赖

输入为目录、选中的程序、基础程序集、JSON文件和内存类型列表。输出为原路径文本与 memoEdit1 提示。替换是正则加字符串操作，不是 JSON 语义解析；格式空格和固定程序集文字影响匹配，程序集仍为 AKRS.ZX2200。所读执行路径涉及 WinForms/DevExpress、反射和文件系统，未见网络服务、数据库、持久队列或定时器；此结论不扩展到整个仓库。

[项目声明](../../trunk/Akrs.ChangeJson/Akrs.ChangeJson.csproj#L1)为 WinExe/.NET Framework 4.8，但 AssemblyName 和 RootNamespace 为 DXApplication1；Debug|AnyCPU 输出指向 ZX2200 Debug 目录。输出目录不证明生产程序会调用该工具。

## 失败与一致性边界

以下限定于上述函数：反射和更新没有局部异常处理或重试；Task 未保存或 await。异常可能中断剩余文件，已写入文件没有回滚。没有备份、临时提交或原子替换；UI 提示早于写入，不能作为写入成功凭证。简单类名重名未检测，改写后未做 JSON/反序列化验证。后台直接访问可由 UI 修改的列表，未见输入快照、互斥或按钮禁用；并发风险尚未动态复现。

## 文件辅助方法补充

已读取DirAndFileHelper全部34个公开方法/重载，并完成7项真实临时文件检查，确认短写尾部残留、目标目录误创建、清理部分删除和进程当前目录副作用。[方法范围与测试边界](changejson-files-review.md)。按钮路径直接使用File，不应将辅助类行为混入按钮执行链。

## 未完成项

资源与配置已完成[XML声明核对](changejson-assets-review.md)：三份resx无数据项，一个设计器元数据；项目引用的packages.config缺失。资源编译、许可生成与运行加载尚未验证。

- DirAndFileHelper全部方法已读，ReflectionHelper具名引用已搜索并有7项隔离检查；外部/动态调用、辅助方法全部输入与生成资源仍未完整验收。
- MSBuild 条件、程序集依赖版本、构建和加载兼容性未验收。
- 零匹配、缺失映射、同名类、文件锁写入失败、中途读取失败、列表变化及两个任务旧快照覆盖已作上述隔离检查；ACL权限、磁盘故障、真实UI并发及其余多任务交错仍未验收。
- 未证明生产程序动态调用此工具；暂列独立手动维护路径，不能据此宣布主自动生产完整。
