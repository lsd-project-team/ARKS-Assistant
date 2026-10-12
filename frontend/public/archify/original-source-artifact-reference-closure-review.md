# 16 项原始源码产物依赖/API 闭包核验

本轮对 16 个独立原始源码发射产物和各自 Compile 引用做只读反射元数据核验：共 254 个 AssemblyRef、15 条产物间引用边，所有引用均能由产物或 Compile 引用解析。唯一不一致是 `WindowsFormsApp1` 仍引用 `AKRS.ZX2200, Version=1.2.0.0`，而当前主程序发射物是 `Version=1.5.0.0`。因此依赖闭包可解析，但 16 项 API/程序集身份闭合尚未通过；不能把这次结果称为联合 MSBuild 或运行时验收。

证据：[assembly-reference-closure.json](../.archify-work/assembly-reference-closure.json)。本轮未修改生产源码/工程，未执行设备、SQL、VM、Fody 或部署。
