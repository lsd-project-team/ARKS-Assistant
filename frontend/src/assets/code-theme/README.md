# Source code appearance

The source viewer uses `@pierre/diffs@1.4.3`, matching the version listed in the locally installed Codex desktop application's third-party notices (Codex 26.928.1915.0).

`codex-light.json` contains the declarative Codex Light theme configuration from that installation: colors, TextMate scope rules and semantic colors. It contains no application implementation code. The registration name is changed to `workspace-codex-light` at runtime to avoid a theme-name collision.

`codex-dark.json` contains the corresponding Codex Dark configuration from the current local installation (Codex 26.1007.2314.0), registered as `workspace-codex-dark`. The source viewer switches both highlighting and its surface with the application's appearance setting. Only declarative colors and syntax scopes are included.

The font stack, 12px size, 1.8 line-height ratio and four-character line-number gutter follow the installed app's source-view settings. These are scoped to the source viewer in `styles.css`.

The soft gray-green appearance retains Codex Light syntax highlighting and uses a tinted `#f8faf6` source surface with `#d6e6cf` selection. These surface colors come from shared appearance variables, so changing appearance updates the viewer without replacing its source or navigation state.

Pierre Diffs is Apache-2.0 licensed: https://github.com/pierrecomputer/pierre/tree/main/packages/diffs
