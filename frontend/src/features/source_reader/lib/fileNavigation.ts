export type FileOpenMode = 'preview' | 'pinned';
export interface FileLocation {
  path: string;
  line: number;
}
export interface FileNavigation {
  paths: string[];
  activePath: string;
  previewPath: string;
  positions: Record<string, number>;
  history: FileLocation[];
  historyIndex: number;
}

export function closeTabs(
  state: FileNavigation & { closedFiles: FileLocation[] },
  closing: string[],
) {
  const paths = state.paths.filter((path) => !closing.includes(path));
  const activePath = closing.includes(state.activePath) ? paths.at(-1) || '' : state.activePath;
  return {
    ...(activePath !== state.activePath && activePath
      ? visitFile({ ...state, paths }, activePath)
      : {}),
    paths,
    activePath,
    previewPath: closing.includes(state.previewPath) ? '' : state.previewPath,
    closedFiles: [
      ...state.closedFiles,
      ...closing.map((path) => ({ path, line: state.positions[path] || 1 })),
    ].slice(-20),
    ...(activePath !== state.activePath ? { jump: fileJump(state, activePath) } : {}),
  };
}

export function fileJump(state: Pick<FileNavigation, 'positions'>, path: string, line?: number) {
  return {
    line: line ?? state.positions[path] ?? 1,
    time: Date.now(),
    align: line === undefined ? ('start' as const) : ('center' as const),
  };
}

export function visitFile(
  state: FileNavigation,
  path: string,
  line?: number,
  mode: FileOpenMode = 'pinned',
) {
  let paths = state.paths;
  let previewPath = state.previewPath;
  if (!paths.includes(path)) {
    // 临时标签只占一个位置；引用定位和双击保留的文件不会被替换。
    paths =
      mode === 'preview' && previewPath
        ? paths.map((item) => (item === previewPath ? path : item))
        : [...paths, path];
    if (mode === 'preview') previewPath = path;
  }
  if (mode === 'pinned' && previewPath === path) previewPath = '';
  const jump = fileJump(state, path, line);
  let history = state.history.slice(0, state.historyIndex + 1);
  if (history.at(-1)?.path === state.activePath) {
    const current = history[history.length - 1];
    history[history.length - 1] = {
      ...current,
      line: state.positions[state.activePath] ?? current.line,
    };
  }
  const current = history.at(-1);
  if (!current || current.path !== path || (line !== undefined && line !== current.line)) {
    history = [...history, { path, line: jump.line }].slice(-100);
  }
  return { paths, activePath: path, previewPath, jump, history, historyIndex: history.length - 1 };
}

export function navigateFiles(state: FileNavigation, direction: number) {
  const historyIndex = state.historyIndex + direction;
  const target = state.history[historyIndex];
  if (!target) return {};
  const history = [...state.history];
  const current = history[state.historyIndex];
  if (current && state.activePath)
    history[state.historyIndex] = {
      ...current,
      line: state.positions[state.activePath] ?? current.line,
    };
  return {
    history,
    historyIndex,
    activePath: target.path,
    positions: { ...state.positions, [target.path]: target.line },
    paths: state.paths.includes(target.path) ? state.paths : [...state.paths, target.path],
    // 导航恢复浏览当时的位置，不覆盖记录或生成额外的历史条目。
    jump: fileJump(state, target.path, target.line),
  };
}

export function parentDirectories(path: string) {
  const parts = path.split('/');
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join('/'));
}

export function tabLabel(path: string, paths: string[]) {
  const name = path.split('/').at(-1) || path;
  const duplicates = paths.filter((item) => item.split('/').at(-1) === name);
  if (duplicates.length < 2) return name;
  const parts = path.split('/');
  for (let count = 2; count <= parts.length; count++) {
    const suffix = parts.slice(-count).join('/');
    if (
      duplicates.every(
        (item) => item === path || item.split('/').slice(-count).join('/') !== suffix,
      )
    )
      return suffix;
  }
  return path;
}
