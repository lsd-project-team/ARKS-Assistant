# 文件图标来源

本目录使用 Pierre 的原版文件图标，与本机 Codex 文件树中的 53 个 SVG 图标逐个比对一致。

- 图标源项目：[@pierre/vscode-icons](https://github.com/pierrecomputer/vscode-icons)，版本 `0.0.9`，MIT 许可。
- 图标精灵、文件名与扩展名规则、浅色配色：[@pierre/trees](https://trees.software/docs)，版本 `1.0.0-beta.6`，Apache-2.0 许可。
- `pierre.svg` 保留上游图标路径、透明度和 symbol ID；仅补充独立 SVG 文件的根元素。
- `theme.json` 提取上游 complete 图标集的规则与浅色颜色，不依赖在线资源。
- 上游缺少专用图标的文件使用灰色默认图标，与 Codex 一致。

`dotnet.svg` 为本项目补充绘制的 C#、项目、解决方案、XML 与 PowerShell 图标；基础图标精灵保持原版。补充规则在 `FileIcon.tsx` 中，文件树和标签栏共用。
许可和上游声明保留在 `LICENSE.md`、`NOTICE.md` 与 `ICONS-LICENSE.md`。
