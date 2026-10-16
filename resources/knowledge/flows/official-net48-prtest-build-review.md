# AKRS.Galaxy2.PR.Test 隔离构建失败记录

`AKRS.Galaxy2.PR.Test.csproj` 的隔离 MSBuild 试跑已保留为失败证据，退出码为 `1`。构建先进入 `AKRS.Galaxy2.PR` 项目，在 `CoreResGen` 阶段报告 18 组未解析引用，并在三个 `.resx` 文件中报告 `MSB3103`：`FrmPREditor.resx`、`UcVmResultShow.resx` 和 `Properties/Resources.resx` 都需要 `DevExpress.Utils.Svg.SvgImage`（来自 `DevExpress.Data.v21.2`）。

未解析引用包含 `AKRS.Galaxy2.HardwareEditor`、`MWArray`、`System.Threading.Tasks.Extensions` 及多个 DevExpress v21.2 程序集。日志中没有 `CS1617`。完整日志哈希见 [official-net48-prtest-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-prtest-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/prtest-build`。本轮没有修改生产工程，也没有补造缺失程序集。
