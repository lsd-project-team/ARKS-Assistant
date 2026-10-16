# 编程页外部命名对话框 IL 边界

`FrmRepository<T>` 在源代码中构造并显示 `FrmCreateName`，但仓库没有该窗体的 `.cs` 源文件。本记录固定核对随附的 `AKRS.Galaxy2.Infrastructure.dll`，为这条间接保存入口补上可复核的二进制边界证据。

| 项目 | 结果 |
| --- | --- |
| 程序集 | `trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.Infrastructure.dll` |
| SHA-256 | `f75452133ba809255061210eafc861b576c0fe8b553a983575934fe3d19892eb` |
| 类型 | `AKRS.Galaxy2.Infrastructure.CustomControls.Controls.FrmCreateName` |
| 基类 | `DevExpress.XtraEditors.XtraForm` |
| 方法 | 10 个；其中 8 个为本审计选择的方法 |

从 IL 可确认：构造函数接收初始名称、窗体标题和标签文本，并初始化控件；`ValidatePredicate` 和 `CreateName` 都是可读写属性；确认处理器读取 `TxtName.Text` 写入 `CreateName`，再设置 `DialogResult` 为 `OK`；取消处理器设置 `DialogResult` 为 `Cancel`；名称编辑事件在谓词为空时启用确认按钮，否则用当前文本调用谓词并把返回值写入确认按钮的 `Enabled` 状态。

这项证据闭合了 `FrmRepository<T>` 对外部命名窗体的构造、校验、返回值和模态结果边界，但仍不能替代真实 UI 运行、程序集部署一致性或运行时异常恢复验收。机器结果见 [programming-external-dialog-il.json](programming-external-dialog-il.json)，校验入口为 `scripts/verify-programming-external-dialog-il.cjs`。
