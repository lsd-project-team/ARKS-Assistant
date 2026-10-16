import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

const saved = new Map();
globalThis.localStorage = {
  getItem: (key) => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: (key) => saved.delete(key),
};
globalThis.window = { localStorage: globalThis.localStorage };
const { useWorkspace, draftFor, draftKey, activateWorkspaceAccount } =
  await import('../src/lib/store.ts');
activateWorkspaceAccount('store-test');
const store = useWorkspace;
beforeEach(() => {
  saved.clear();
  store.setState({
    threadId: '',
    chatPositions: {},
    closedFiles: [],
    drafts: {},
    paths: [],
    activePath: '',
    previewPath: '',
    history: [],
    historyIndex: -1,
    expandedDirectories: [],
    rootExpanded: true,
    explorerScroll: 0,
    readingFocused: false,
    workspaceRestore: null,
    sourceModes: {},
    positions: {},
    chatRatio: 0.36,
    explorerWidth: 0,
    codeOpen: true,
    explorerOpen: true,
    mobile: 'chat',
  });
});

test('统一工作区开关同时控制源码和文件树，保留标签与阅读位置', async () => {
  store.getState().openFile('A.cs', 10);
  store.getState().savePosition('A.cs', 80);
  store.getState().toggleReadingFocus();
  const navigationVersion = store.getState().navigationVersion;
  store.getState().setWorkspaceOpen(false);
  assert.equal(store.getState().codeOpen, false);
  assert.equal(store.getState().explorerOpen, false);
  assert.equal(store.getState().readingFocused, false);
  assert.equal(store.getState().mobile, 'chat');
  await store.persist.rehydrate();
  store.getState().setWorkspaceOpen(true);
  assert.equal(store.getState().codeOpen, true);
  assert.equal(store.getState().explorerOpen, true);
  assert.equal(store.getState().mobile, 'code');
  assert.deepEqual(store.getState().paths, ['A.cs']);
  assert.equal(store.getState().jump.line, 80);
  assert.equal(store.getState().navigationVersion, navigationVersion);
});

test('文件树拖动收起后恢复原宽度，聊天比例和草稿保持不变', async () => {
  store.getState().selectThread('A');
  store.getState().setDraft('未发送的问题');
  const restore = { chatRatio: 0.42, focusChatRatio: 0.24, explorerWidth: 260 };
  store.getState().setLayout(restore);
  store.getState().setLayout({ explorerWidth: 140 });
  store.getState().collapsePane('files', restore);
  assert.equal(store.getState().codeOpen, true);
  assert.equal(store.getState().explorerOpen, false);
  assert.equal(store.getState().chatRatio, 0.42);
  await store.persist.rehydrate();
  store.getState().setLayout({ explorerOpen: true });
  assert.equal(store.getState().explorerWidth, 260);
  assert.equal(draftFor(store.getState()).content, '未发送的问题');
});

test('整个工作区拖动收起并刷新后，恢复拖动前的专注比例和文件树状态', async () => {
  store.getState().openFile('A.cs', 10);
  store.getState().savePosition('A.cs', 80);
  const restore = { chatRatio: 0.42, focusChatRatio: 0.25, explorerWidth: 260 };
  store.getState().setLayout({ ...restore, explorerOpen: false });
  store.getState().toggleReadingFocus();
  store.getState().setLayout({ focusChatRatio: 0.8 });
  store.getState().collapsePane('chat', restore);
  assert.equal(store.getState().codeOpen, false);
  assert.equal(store.getState().explorerOpen, false);
  assert.equal(store.getState().readingFocused, false);
  assert.equal(store.getState().mobile, 'chat');
  // 关闭后的重复调用不覆盖可恢复的布局。
  store.getState().setWorkspaceOpen(false);
  await store.persist.rehydrate();
  store.getState().setWorkspaceOpen(true);
  assert.equal(store.getState().codeOpen, true);
  assert.equal(store.getState().explorerOpen, false);
  assert.equal(store.getState().readingFocused, true);
  assert.equal(store.getState().focusChatRatio, 0.25);
  assert.equal(store.getState().chatRatio, 0.42);
  assert.equal(store.getState().explorerWidth, 260);
  assert.equal(store.getState().jump.line, 80);
});

test('只有文件树时拖动收起，再打开恢复文件树并保留源码关闭状态', async () => {
  store.getState().setLayout({ codeOpen: false, explorerWidth: 250 });
  store.getState().collapsePane('files');
  assert.equal(store.getState().codeOpen, false);
  assert.equal(store.getState().explorerOpen, false);
  await store.persist.rehydrate();
  store.getState().setWorkspaceOpen(true);
  assert.equal(store.getState().codeOpen, false);
  assert.equal(store.getState().explorerOpen, true);
  assert.equal(store.getState().explorerWidth, 250);
});

test('阅读位置按会话恢复，删除当前会话清理草稿和锚点', async () => {
  store.getState().selectThread('A');
  store.getState().setDraft('草稿 A');
  store.getState().saveChatPosition('A', { anchor: 'message-80', offset: 32, following: false });
  store.getState().selectThread('B');
  store.getState().setDraft('草稿 B');
  store.getState().selectThread('A');
  assert.equal(store.getState().messageJump.id, 'message-80');
  assert.equal(store.getState().messageJump.restore, true);
  await store.persist.rehydrate();
  assert.equal(store.getState().messageJump.id, 'message-80');
  store.getState().jumpToMessage('A', 'search-hit');
  assert.equal(store.getState().messageJump.restore, undefined);
  store.getState().forgetThread('A');
  assert.equal(store.getState().threadId, '');
  assert.equal(store.getState().chatPositions.A, undefined);
  assert.equal(store.getState().drafts.A, undefined);
  assert.equal(store.getState().drafts.B.content, '草稿 B');
});

test('关闭右侧、关闭全部和重新打开都保留对应文件阅读行', async () => {
  for (const path of ['A.cs', 'B.cs', 'C.cs']) store.getState().openFile(path);
  store.getState().savePosition('C.cs', 120);
  store.getState().openFile('B.cs');
  store.getState().closeRightFiles('B.cs');
  assert.deepEqual(store.getState().paths, ['A.cs', 'B.cs']);
  assert.equal(store.getState().activePath, 'B.cs');
  await store.persist.rehydrate();
  store.getState().reopenFile();
  assert.equal(store.getState().activePath, 'C.cs');
  assert.equal(store.getState().jump.line, 120);
  store.getState().closeAllFiles();
  assert.equal(store.getState().activePath, '');
  store.getState().reopenFile();
  assert.deepEqual(store.getState().paths, ['C.cs']);
  assert.equal(store.getState().jump.line, 120);
});

test('引用范围和字号改变保留定位，布局重置保留会话与标签', () => {
  store.getState().selectThread('A');
  store.getState().openFile('A.cs', 16, 'pinned', 21);
  assert.equal(store.getState().jump.endLine, 21);
  store.getState().savePosition('A.cs', 90);
  store.getState().setReader(16, 2);
  assert.equal(store.getState().jump.line, 90);
  store.getState().setLayout({ chatRatio: 0.2, explorerWidth: 330 });
  store.getState().resetLayout();
  assert.equal(store.getState().chatRatio, 0.36);
  assert.equal(store.getState().threadId, 'A');
  assert.deepEqual(store.getState().paths, ['A.cs']);
});

test('执行命令保留选区，异步压缩返回不会清空新草稿或其他会话', () => {
  store.getState().selectThread('A');
  store.getState().setDraft('/compact');
  store.getState().addSelection({
    path: 'A.cs',
    start_line: 1,
    end_line: 1,
    start_column: 1,
    end_column: 2,
    content: 'A',
    version: 'v1',
  });
  const submitted = draftFor(store.getState());
  store.getState().setDraft('压缩期间输入的新问题');
  store.getState().consumeCommand('A', submitted);
  assert.equal(draftFor(store.getState()).content, '压缩期间输入的新问题');
  store.getState().setDraft('/context');
  const command = draftFor(store.getState());
  store.getState().selectThread('B');
  store.getState().setDraft('B 的问题');
  store.getState().consumeCommand('A', command);
  assert.equal(draftFor(store.getState()).content, 'B 的问题');
  store.getState().selectThread('A');
  assert.equal(draftFor(store.getState()).content, '');
  assert.equal(draftFor(store.getState()).selections.length, 1);
});

test('源码和文件面板独立关闭，重新打开源码恢复阅读位置和标签', () => {
  store.getState().openFile('A.cs', 10);
  store.getState().savePosition('A.cs', 80);
  store.getState().toggleReadingFocus();
  store.getState().setLayout({ codeOpen: false });
  assert.equal(store.getState().explorerOpen, true);
  assert.equal(store.getState().readingFocused, false);
  assert.deepEqual(store.getState().paths, ['A.cs']);
  store.getState().setLayout({ explorerOpen: false });
  assert.equal(store.getState().mobile, 'chat');
  store.getState().setLayout({ codeOpen: true });
  assert.equal(store.getState().explorerOpen, false);
  assert.equal(store.getState().jump.line, 80);
  assert.equal(store.getState().jump.align, 'start');
  store.getState().setLayout({ explorerOpen: true });
  assert.equal(store.getState().codeOpen, true);
});

test('面板关闭状态持久化，打开文件或导航引用会恢复源码区', async () => {
  store.getState().openFile('A.cs');
  store.getState().openFile('B.cs');
  store.getState().setLayout({ codeOpen: false, explorerOpen: false });
  await store.persist.rehydrate();
  assert.equal(store.getState().codeOpen, false);
  assert.equal(store.getState().explorerOpen, false);
  store.getState().navigateHistory(-1);
  assert.equal(store.getState().codeOpen, true);
  assert.equal(store.getState().explorerOpen, false);
  store.getState().setLayout({ codeOpen: false });
  store.getState().openFile('Referenced.cs', 12);
  assert.equal(store.getState().codeOpen, true);
  assert.equal(store.getState().jump.line, 12);
  assert.equal(store.getState().explorerOpen, false);
});

test('连续单击只替换临时标签，双击保留及源码引用不被替换', () => {
  store.getState().openFile('A.cs', undefined, 'preview');
  store.getState().openFile('B.cs', undefined, 'preview');
  assert.deepEqual(store.getState().paths, ['B.cs']);
  store.getState().keepFile('B.cs');
  store.getState().openFile('C.cs', undefined, 'preview');
  store.getState().openFile('Referenced.cs', 9);
  store.getState().openFile('D.cs', undefined, 'preview');
  assert.deepEqual(store.getState().paths, ['B.cs', 'D.cs', 'Referenced.cs']);
  store.getState().closeOtherFiles('D.cs');
  assert.deepEqual(store.getState().paths, ['D.cs']);
  assert.equal(store.getState().previewPath, '');
});

test('导航保留离开时的行号，后退后新跳转清除前进分支', () => {
  store.getState().openFile('A.cs');
  store.getState().savePosition('A.cs', 80);
  store.getState().openFile('B.cs', 12);
  store.getState().savePosition('B.cs', 30);
  store.getState().navigateHistory(-1);
  assert.equal(store.getState().activePath, 'A.cs');
  assert.equal(store.getState().jump.line, 80);
  store.getState().navigateHistory(1);
  assert.equal(store.getState().jump.line, 30);
  store.getState().navigateHistory(-1);
  store.getState().openFile('C.cs');
  assert.deepEqual(
    store.getState().history.map((item) => item.path),
    ['A.cs', 'C.cs'],
  );
  store.getState().navigateHistory(1);
  assert.equal(store.getState().activePath, 'C.cs');
});

test('关闭当前文件的导航记录仍然准确，并可返回已关闭文件', () => {
  store.getState().openFile('A.cs');
  store.getState().savePosition('A.cs', 20);
  store.getState().openFile('B.cs');
  store.getState().savePosition('B.cs', 50);
  store.getState().closeFile('B.cs');
  store.getState().navigateHistory(-1);
  assert.equal(store.getState().activePath, 'B.cs');
  assert.equal(store.getState().jump.line, 50);
});

test('目录展开与滚动持久化，主动折叠不会被选中文件立即展开', async () => {
  store.getState().openFile('src/Views/Main.cs');
  assert.deepEqual(store.getState().expandedDirectories, ['src', 'src/Views']);
  store.getState().saveExplorerScroll(480);
  await store.persist.rehydrate();
  assert.equal(store.getState().explorerScroll, 480);
  store.getState().collapseDirectories();
  assert.deepEqual(store.getState().expandedDirectories, []);
  store.getState().revealFile();
  assert.deepEqual(store.getState().expandedDirectories, ['src', 'src/Views']);
});

test('专注阅读退出后保留普通布局，Markdown 引用行号自动切换源码', () => {
  store.getState().setLayout({ chatRatio: 0.42, collapsed: false });
  store.getState().toggleReadingFocus();
  store.getState().setLayout({ focusChatRatio: 0.28 });
  store.getState().toggleReadingFocus();
  assert.equal(store.getState().chatRatio, 0.42);
  assert.equal(store.getState().collapsed, false);
  store.getState().openFile('README.md', 12);
  assert.equal(store.getState().sourceModes['README.md'], true);
  assert.equal(store.getState().jump.line, 12);
});

test('草稿和选区按会话隔离，并在重新加载后恢复', async () => {
  store.getState().selectThread('A');
  store.getState().setDraft('A 的未发送问题');
  store.getState().addSelection({ path: 'A.cs', start_line: 1, end_line: 2 });
  store.getState().selectThread('B');
  assert.equal(draftFor(store.getState()).content, '');
  assert.equal(draftFor(store.getState()).selections.length, 0);
  store.getState().setDraft('B 的草稿');
  const persisted = saved.get('trunk-workspace:account:store-test');
  store.setState({ drafts: {} });
  saved.set('trunk-workspace:account:store-test', persisted);
  await store.persist.rehydrate();
  store.getState().selectThread('A');
  assert.equal(draftFor(store.getState()).content, 'A 的未发送问题');
  assert.equal(draftFor(store.getState()).selections[0].path, 'A.cs');
});

test('异步提交只清理对应快照，不覆盖后续输入或其他会话', () => {
  store.getState().selectThread('A');
  store.getState().setDraft('已提交');
  const submitted = draftFor(store.getState());
  store.getState().setDraft('继续输入');
  store.getState().consumeDraft('A', submitted);
  assert.equal(draftFor(store.getState()).content, '继续输入');
  const updated = draftFor(store.getState());
  store.getState().selectThread('B');
  store.getState().setDraft('B 内容');
  store.getState().consumeDraft('A', updated);
  assert.equal(draftFor(store.getState()).content, 'B 内容');
  assert.equal(store.getState().drafts.A, undefined);
  assert.equal(draftKey(''), 'new');
});

test('布局和文件阅读位置恢复，显式引用行号优先于旧位置', async () => {
  store.getState().setLayout({ chatRatio: 0.41, explorerWidth: 210, explorerOpen: false });
  store.getState().savePosition('Long.cs', 120);
  await store.persist.rehydrate();
  store.getState().openFile('Long.cs');
  assert.equal(store.getState().jump.line, 120);
  assert.equal(store.getState().jump.align, 'start');
  assert.equal(store.getState().chatRatio, 0.41);
  assert.equal(store.getState().explorerOpen, false);
  store.getState().openFile('Long.cs', 8);
  assert.equal(store.getState().jump.line, 8);
  assert.equal(store.getState().jump.align, 'center');
});

test('新会话提交成功才迁移草稿，并保留请求期间追加的选区', () => {
  store.getState().setDraft('首次问题');
  const submitted = draftFor(store.getState());
  store.getState().addSelection({ path: 'Later.cs', start_line: 8, end_line: 9 });
  store.getState().attachNewDraft('created');
  store.getState().consumeDraft('new', submitted);
  store.getState().consumeDraft('created', submitted);
  assert.equal(store.getState().threadId, 'created');
  assert.equal(draftFor(store.getState()).content, '首次问题');
  assert.equal(draftFor(store.getState()).selections[0].path, 'Later.cs');
  assert.equal(store.getState().drafts.new, undefined);
  store.getState().attachNewDraft('another');
  assert.equal(store.getState().threadId, 'created');
});

test('刷新及关闭当前标签恢复对应文件位置', async () => {
  store.getState().openFile('A.cs');
  store.getState().savePosition('A.cs', 75);
  store.getState().openFile('B.cs');
  store.getState().savePosition('B.cs', 180);
  await store.persist.rehydrate();
  assert.equal(store.getState().jump.line, 180);
  store.getState().closeFile('B.cs');
  assert.equal(store.getState().activePath, 'A.cs');
  assert.equal(store.getState().jump.line, 75);
});

test('刷新文件使用当前阅读位置，不改动导航历史或 Markdown 模式', () => {
  store.getState().openFile('Guide.md');
  store.getState().setSourceMode('Guide.md', false);
  store.getState().savePosition('Guide.md', 42);
  const history = store.getState().history;
  store.getState().restoreReadingPosition();
  assert.equal(store.getState().jump.line, 42);
  assert.equal(store.getState().jump.align, 'start');
  assert.equal(store.getState().history, history);
  assert.equal(store.getState().sourceModes['Guide.md'], false);
});
