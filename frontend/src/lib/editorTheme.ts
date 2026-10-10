import type { BeforeMount } from '@monaco-editor/react';

export const SOURCE_THEME = 'trunk-paper';

// 白色阅读面板配合低饱和语法色，保留代码辨识度，避免默认亮蓝色抢过正文。
export const registerSourceTheme: BeforeMount = (monaco) => {
  monaco.editor.defineTheme(SOURCE_THEME, {
    base: 'vs',
    inherit: true,
    rules: [
      { token: '', foreground: '343632' },
      { token: 'comment', foreground: '899182', fontStyle: '' },
      { token: 'keyword', foreground: '786A8A' },
      { token: 'string', foreground: '927557' },
      { token: 'number', foreground: '927557' },
      { token: 'type', foreground: '557D80' },
      { token: 'type.identifier', foreground: '557D80' },
      { token: 'delimiter', foreground: '77776E' },
      { token: 'delimiter.curly', foreground: '77776E' },
      { token: 'delimiter.square', foreground: '77776E' },
      { token: 'delimiter.parenthesis', foreground: '77776E' },
      { token: 'delimiter.angle', foreground: '77776E' },
      { token: 'tag', foreground: '557D80' },
      { token: 'attribute.name', foreground: '786A8A' },
      { token: 'attribute.value', foreground: '927557' },
    ],
    colors: {
      'editor.background': '#FFFFFF',
      'editor.foreground': '#343632',
      'editorLineNumber.foreground': '#B1B0AA',
      'editorLineNumber.activeForeground': '#74726B',
      'editorGutter.background': '#FFFFFF',
      'editor.selectionBackground': '#E4E8E2',
      'editor.inactiveSelectionBackground': '#EEEFEA',
      'editor.selectionHighlightBackground': '#F0F1EA',
      'editor.lineHighlightBackground': '#FAFAF7',
      'editorCursor.foreground': '#6F6D65',
      'editorIndentGuide.background1': '#EEEFEA',
      'editorIndentGuide.activeBackground1': '#D8DBD3',
      'editorBracketHighlight.foreground1': '#77776E',
      'editorBracketHighlight.foreground2': '#77776E',
      'editorBracketHighlight.foreground3': '#77776E',
      'editorBracketHighlight.foreground4': '#77776E',
      'editorBracketHighlight.foreground5': '#77776E',
      'editorBracketHighlight.foreground6': '#77776E',
      'editorWidget.background': '#FAF9F6',
      'editorWidget.border': '#E5E3DD',
      focusBorder: '#D2CFC6',
      'scrollbar.shadow': '#00000000',
      'scrollbarSlider.background': '#D2CFC650',
      'scrollbarSlider.hoverBackground': '#B5B1A780',
      'scrollbarSlider.activeBackground': '#96938B90',
    },
  });
};
