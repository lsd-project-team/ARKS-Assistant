import { registerCustomTheme, type ThemeRegistration } from '@pierre/diffs';
import codexLight from '../../../shared/assets/code-theme/codex-light.json';
import codexDark from '../../../shared/assets/code-theme/codex-dark.json';

export const SOURCE_THEME = 'workspace-codex-light';
export const SOURCE_DARK_THEME = 'workspace-codex-dark';

// 使用本机 Codex Light 的声明式主题配置，避免手工近似配色丢失语言细节。
export const sourceTheme: ThemeRegistration = { ...codexLight, name: SOURCE_THEME, type: 'light' };
registerCustomTheme(SOURCE_THEME, async () => sourceTheme);
// 深色使用 Codex 的完整语法规则，避免浅色高亮在暗底上失去对比。
export const sourceDarkTheme: ThemeRegistration = {
  ...codexDark,
  name: SOURCE_DARK_THEME,
  type: 'dark',
};
registerCustomTheme(SOURCE_DARK_THEME, async () => sourceDarkTheme);
