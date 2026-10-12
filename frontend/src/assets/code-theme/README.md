# Source code appearance

The source viewer uses `@pierre/diffs@1.4.3`, matching the version listed in the locally installed Codex desktop application's third-party notices (Codex 26.928.1915.0).

`codex-light.json` contains the declarative Codex Light theme configuration from that installation: colors, TextMate scope rules and semantic colors. It contains no application implementation code. The registration name is changed to `workspace-codex-light` at runtime to avoid a theme-name collision.

The font stack, 12px size, 1.8 line-height ratio and four-character line-number gutter follow the installed app's source-view settings. These are scoped to the source viewer in `styles.css`.

Pierre Diffs is Apache-2.0 licensed: https://github.com/pierrecomputer/pierre/tree/main/packages/diffs
