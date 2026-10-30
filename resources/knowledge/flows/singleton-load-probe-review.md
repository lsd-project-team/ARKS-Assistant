# Singleton<T> 实际读盘与失败回退复核

在隔离目录编译了一个只引用原工程 `AKRS.Galaxy2.Infrastructure.dll` 的测试类型，调用真实 `Singleton<T>.GetInstance()` 和 `Load()`，输入文件全部位于 `.archify-work`。

- 合法 JSON：首次 `GetInstance()` 读出 `Name=from-json, Count=7`；再次获取返回同一引用；调用 `Load()` 后引用被替换并重新读出相同值。
- 文件不存在：返回默认构造对象，`Name` 为空、`Count=0`。
- JSON 损坏：同样返回默认构造对象，并在探针输出中记录 Newtonsoft 的两行解析错误。

这条证据补上了 Main 初始化清单中 `GetInstance/Load` 的实际行为边界。它只覆盖安全测试类型和隔离文件，未调用任何生产单例、设备配置、SDK、数据库或 UI。

- 机器审计：[singleton-load-probe-audit.json](singleton-load-probe-audit.json)
- 可重放脚本：[run-singleton-load-probe.ps1](../../.archify-work/run-singleton-load-probe.ps1)
