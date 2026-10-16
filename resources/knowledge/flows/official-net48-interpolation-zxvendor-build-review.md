# InterpolationMovementTest 真实厂商输入闭包复核

在隔离 `ReferencePath` 中加入原工程已有的 ZX2200 `bin/Debug` 和 `libs` 程序集后，`InterpolationMovementTest` 展开的 ZX2200、Calibration、SoftKey、AutoFocusing、AxisCompensate、MachineSupport、CoordinateSystems、Machine、Dispense 和 PR 闭包中的未解析引用全部消失。构建退出码为 `1`，13 个警告、2 个错误，两个错误均为对应 Dispense 和 PR 项目缺少真实 `LC.exe`（`MSB3086`）；日志没有 `CS1617`。

输入只复制到 `.archify-work/official-net48-build-toolchain/vendor-devexpress-from-zx2200-bin`，未修改生产工程，也未伪造许可证工具。日志和输入清单见 [official-net48-interpolation-zxvendor-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-interpolation-zxvendor-build-audit.json)。
