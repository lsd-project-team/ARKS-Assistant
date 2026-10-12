import { registerCustomTheme, type ThemeRegistration } from '@pierre/diffs';
import codexLight from '../assets/code-theme/codex-light.json';

export const SOURCE_THEME = 'workspace-codex-light';
export const SOURCE_LINE_HEIGHT = 21.6;

// 使用本机 Codex Light 的声明式主题配置，避免手工近似配色丢失语言细节。
export const sourceTheme: ThemeRegistration = { ...codexLight, name: SOURCE_THEME, type: 'light' };
registerCustomTheme(SOURCE_THEME, async () => sourceTheme);
