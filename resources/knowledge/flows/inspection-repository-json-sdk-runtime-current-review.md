# 检查仓储 JSON SDK 运行时当前复验

日期：2026-10-06。状态：current-inspection-repository-json-sdk-runtime-verified。

在两个隔离的 Windows .NET Framework 进程中，按当前 DLL 重新执行 52 个断言位置（26 个独立行为），覆盖 JSON 列表/对象保存读取、缺失文件、序列化错误、目录错误和 Singleton 缓存/加载/并发。

该项使用合成记录、隔离临时目录和两份 DLL，不代表产品配置、PR、原生应用、部署 UI 或设备验收。
