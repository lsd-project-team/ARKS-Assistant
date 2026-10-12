# 原始 S2 自检 IL 边界

本轮对 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe` 做只读 Mono.Cecil 检查，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。没有启动生产程序，也没有触发 UI、SDK、数据库、VM 或设备。

| 原始类型/方法 | IL 指令数 | 关键边界 |
| --- | ---: | --- |
| `System2Domain.CheckIsReady` | 336 | 先 `OpenBondHeadVaccum`，再按开关调用 `BondProgram.SelfCheck`、`S2ActionNodeController.SelfCheck`、参数门、吸嘴架传感器、可选吸嘴检测、焊头余料处理和预点胶报警；含 `AKRSXtraMessageBox.Show` |
| `S2ActionNodeController.SelfCheck` | 109 | 失败路径调用 `AKRSXtraMessageBox.Show` |
| `BondProgram.SelfCheck` | 439 | 先调用 `NozzleShelfProgram.SelfCheck`，并包含配置失败提示 |
| `NozzleShelfProgram.SelfCheck` | 81 | 调用吸嘴仓库并包含配置失败提示 |
| `NozzleShelfController.CheckToolBankConfiguration` | 304 | 读取 `PickerHolderSensor1` 至 `PickerHolderSensor7` 的 `GetInputValue`，错误路径调用 `AKRSMessageBoxExt.Show` |

这份 IL 证据把源码自检顺序锚定到当前原始程序，并明确了 UI/设备边界；它仍不能证明自检在真实启动路径成功，也不能替代生产 UI、硬件和部署验收。机器结果见 [original-s2-selfcheck-il.json](original-s2-selfcheck-il.json)，校验入口为 `scripts/verify-original-s2-selfcheck-il.cjs`。
