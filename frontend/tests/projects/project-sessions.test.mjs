import test from 'node:test';
import assert from 'node:assert/strict';
const saved = new Map();
globalThis.localStorage = {
  getItem: (key) => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: (key) => saved.delete(key),
};
globalThis.window = { localStorage: globalThis.localStorage };
const { useWorkspace, draftFor } = await import('../../src/app/state/store.ts');
const { threadSelectedAt } = await import('../../src/features/chat/lib/sidebarNavigation.ts');
const { newConversationProject } =
  await import('../../src/features/chat/lib/conversationCreation.ts');

function reset() {
  saved.clear();
  useWorkspace.setState(useWorkspace.getInitialState(), true);
}

test('删除当前项目后独立继续原对话，保留对话草稿并清理旧源码状态', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('A');
  api().selectThread('chat-a');
  api().setDraft('原对话草稿');
  api().openFile('A.cs', 12);
  api().setProjectExpanded('A', true);
  useWorkspace.setState({ sourceBindings: { A: 'source-A' } });
  api().removeProject('A', 'independent');
  assert.equal(api().projectId, 'independent');
  assert.equal(api().threadId, 'chat-a');
  assert.equal(draftFor(api()).content, '原对话草稿');
  assert.equal(api().activePath, '');
  assert.equal(api().threadEntries['chat-a'], 'recent');
  for (const field of ['projectSessions', 'sourceBindings', 'expandedProjects'])
    assert.equal(api()[field].A, undefined);
});

test('删除其他项目合并新草稿时不覆盖当前项目及原独立草稿和选区', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('independent');
  api().setDraft('独立草稿');
  api().addSelection({ path: 'independent.cs' });
  api().switchProject('A');
  api().setDraft('项目草稿');
  api().addSelection({ path: 'A.cs' });
  api().switchProject('B');
  api().selectThread('chat-b');
  api().setDraft('B 的草稿');
  api().removeProject('A', 'trash');
  assert.equal(api().projectId, 'B');
  assert.equal(api().threadId, 'chat-b');
  assert.equal(draftFor(api()).content, 'B 的草稿');
  assert.equal(api().drafts['new:A'], undefined);
  assert.equal(api().drafts['new:independent'].content, '独立草稿\n\n项目草稿');
  assert.deepEqual(
    api().drafts['new:independent'].selections.map((row) => row.path),
    ['independent.cs', 'A.cs'],
  );
});

test('当前项目对话移入回收站后离开旧对话，新草稿和可恢复的对话草稿均保留', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('A');
  api().setDraft('新对话草稿');
  api().selectThread('chat-a');
  api().setDraft('原对话未发送内容');
  api().removeProject('A', 'trash');
  assert.equal(api().projectId, 'independent');
  assert.equal(api().threadId, '');
  assert.equal(api().sidebarView, 'deleted');
  assert.equal(draftFor(api()).content, '新对话草稿');
  assert.equal(api().drafts['chat-a'].content, '原对话未发送内容');
});

const creationProjects = {
  default_project_id: 'A',
  projects: [
    { id: 'A', state: 'active' },
    { id: 'B', state: 'active' },
    { id: 'deleted', state: 'deleted' },
  ],
};

test('公共新对话入口始终独立，只有明确指定有效项目时才归属项目', () => {
  assert.equal(newConversationProject(creationProjects), 'independent');
  assert.equal(newConversationProject(creationProjects, 'A'), 'A');
  assert.equal(newConversationProject(creationProjects, 'B'), 'B');
  assert.equal(newConversationProject(creationProjects, 'deleted'), undefined);
  assert.equal(newConversationProject(creationProjects, 'removed'), undefined);
});

test('创建独立对话不依赖默认项目、有效项目数量或项目列表是否加载', () => {
  assert.equal(newConversationProject(creationProjects, ''), 'independent');
  assert.equal(newConversationProject(creationProjects, 'independent'), 'independent');
  assert.equal(newConversationProject(undefined), 'independent');
  assert.equal(newConversationProject(undefined, 'A'), undefined);
  assert.equal(
    newConversationProject({ projects: [], default_project_id: null }, ''),
    'independent',
  );
  assert.equal(
    newConversationProject({ ...creationProjects, default_project_id: 'deleted' }),
    'independent',
  );
});

test('统一新对话动作保留当前项目源码阅读位置及已有对话草稿', () => {
  reset();
  const state = () => useWorkspace.getState();
  state().initializeProject('B');
  state().setDraft('B 的新对话草稿');
  state().selectThread('chat-b');
  state().setDraft('B 的旧对话草稿');
  state().openFile('Program.cs', 40);
  state().savePosition('Program.cs', 40);
  state().setSidebarView('deleted');
  state().startConversation(newConversationProject(creationProjects, 'B'));
  assert.equal(state().projectId, 'B');
  assert.equal(state().threadId, '');
  assert.equal(state().sidebarView, 'active');
  assert.equal(state().positions['Program.cs'], 40);
  assert.equal(draftFor(state()).content, 'B 的新对话草稿');
  assert.equal(state().drafts['chat-b'].content, 'B 的旧对话草稿');
});

test('从项目新建独立对话时保留项目会话和草稿，独立草稿刷新后仍独立', () => {
  reset();
  const state = () => useWorkspace.getState();
  state().initializeProject('A');
  state().openFile('Default.cs', 12);
  state().selectThread('chat-a');
  state().setDraft('默认项目的草稿');
  state().setSidebarView('deleted');
  state().startConversation(newConversationProject(creationProjects));
  assert.equal(state().projectId, 'independent');
  assert.equal(state().threadId, '');
  assert.equal(state().sidebarView, 'active');
  assert.equal(state().activePath, '');
  state().setDraft('独立对话的草稿');
  const options = useWorkspace.persist.getOptions();
  useWorkspace.setState(
    options.merge(options.partialize(state()), useWorkspace.getInitialState()),
    true,
  );
  assert.equal(state().projectId, 'independent');
  assert.equal(draftFor(state()).content, '独立对话的草稿');
  state().switchProject('A');
  assert.equal(state().threadId, 'chat-a');
  assert.equal(state().activePath, 'Default.cs');
  assert.equal(draftFor(state()).content, '默认项目的草稿');
  state().switchProject('independent');
  assert.equal(state().threadId, '');
  assert.equal(draftFor(state()).content, '独立对话的草稿');
});

test('在已有独立对话上新建时保持独立，旧对话消息身份和草稿可恢复', () => {
  reset();
  const state = () => useWorkspace.getState();
  state().initializeProject('independent');
  state().selectThread('standalone');
  state().setDraft('独立对话的草稿');
  state().startConversation(newConversationProject(creationProjects));
  assert.equal(state().projectId, 'independent');
  assert.equal(state().threadId, '');
  assert.equal(draftFor(state()).content, '');
  assert.equal(state().drafts.standalone.content, '独立对话的草稿');
  state().selectThread('standalone');
  assert.equal(state().threadId, 'standalone');
  assert.equal(draftFor(state()).content, '独立对话的草稿');
});

test('同一对话的两个入口互斥高亮，切换入口不改变消息、草稿和阅读位置', () => {
  reset();
  const state = () => useWorkspace.getState();
  const row = { id: 'chat-a', project_id: 'A' };
  state().initializeProject('A');
  state().selectThread(row.id);
  state().setDraft('未发送的内容');
  state().savePosition('Program.cs', 21);
  const highlighted = () =>
    ['project', 'recent'].filter((entry) => threadSelectedAt(row, entry, state()));
  assert.deepEqual(highlighted(), ['project']);
  for (const entry of ['recent', 'project', 'recent']) {
    state().selectThread(row.id);
    state().setThreadEntry(row.id, entry);
    assert.deepEqual(highlighted(), [entry]);
    assert.equal(draftFor(state()).content, '未发送的内容');
    assert.equal(state().positions['Program.cs'], 21);
  }
  state().selectThread('');
  assert.deepEqual(highlighted(), []);
});

test('刷新和项目切换仍恢复最后点击的入口，独立对话仅在最近列表高亮', () => {
  reset();
  const state = () => useWorkspace.getState();
  const row = { id: 'chat-a', project_id: 'A' };
  state().initializeProject('A');
  state().selectThread(row.id);
  state().setThreadEntry(row.id, 'recent');
  state().switchProject('B');
  assert.equal(threadSelectedAt(row, 'recent', state()), false);
  state().switchProject('A');
  const options = useWorkspace.persist.getOptions();
  useWorkspace.setState(
    options.merge(options.partialize(state()), useWorkspace.getInitialState()),
    true,
  );
  assert.equal(threadSelectedAt(row, 'recent', state()), true);
  assert.equal(threadSelectedAt(row, 'project', state()), false);
  state().switchProject('independent');
  state().selectThread('standalone');
  const standalone = { id: 'standalone', project_id: null };
  assert.equal(threadSelectedAt(standalone, 'recent', state()), true);
  assert.equal(threadSelectedAt(standalone, 'project', state()), false);
  state().forgetThread(row.id);
  assert.equal(state().threadEntries[row.id], undefined);
});

test('项目切换与刷新保留列表类型和各项目的展开状态', () => {
  reset();
  const state = () => useWorkspace.getState();
  state().initializeProject('A');
  state().setSidebarView('deleted');
  state().setProjectExpanded('A', false);
  state().setProjectExpanded('B', true);
  state().switchProject('B');
  assert.equal(state().sidebarView, 'deleted');
  assert.deepEqual(state().expandedProjects, { A: false, B: true });
  const options = useWorkspace.persist.getOptions();
  useWorkspace.setState(
    options.merge(options.partialize(state()), useWorkspace.getInitialState()),
    true,
  );
  assert.equal(state().sidebarView, 'deleted');
  assert.deepEqual(state().expandedProjects, { A: false, B: true });
});

test('旧归档视图恢复到最近时保留原草稿、选择和展开状态', () => {
  reset();
  const state = useWorkspace.getState();
  state.initializeProject('A');
  state.selectThread('chat-a');
  state.setDraft('不能丢失的草稿');
  state.setProjectExpanded('A', true);
  const options = useWorkspace.persist.getOptions();
  const persisted = { ...options.partialize(useWorkspace.getState()), sidebarView: 'archived' };
  const restored = options.merge(persisted, useWorkspace.getInitialState());
  assert.equal(restored.sidebarView, 'active');
  assert.equal(restored.threadId, 'chat-a');
  assert.equal(draftFor(restored).content, '不能丢失的草稿');
  assert.deepEqual(restored.expandedProjects, { A: true });
});

test('从最近列表删除其他项目的对话会清理保存的选择，同时保留当前会话', () => {
  reset();
  const state = () => useWorkspace.getState();
  state().initializeProject('A');
  state().selectThread('chat-a');
  state().setDraft('A 的草稿');
  state().switchProject('B');
  state().selectThread('chat-b');
  state().setDraft('B 的草稿');
  state().forgetThread('chat-a');
  assert.equal(state().threadId, 'chat-b');
  assert.equal(draftFor(state()).content, 'B 的草稿');
  state().switchProject('A');
  assert.equal(state().threadId, '');
  assert.equal(state().drafts['chat-a'], undefined);
});

test('迁移旧阅读状态和新对话草稿，项目身份初始化不清空历史', () => {
  reset();
  useWorkspace.getState().openFile('Program.cs', 23);
  useWorkspace.getState().selectThread('old-thread');
  useWorkspace.setState({ drafts: { new: { content: '迁移草稿', selections: [] } } });
  useWorkspace.getState().initializeProject('project-a');
  const state = useWorkspace.getState();
  assert.equal(state.activePath, 'Program.cs');
  assert.equal(state.threadId, 'old-thread');
  assert.equal(state.drafts['new:project-a'].content, '迁移草稿');
  assert.equal(state.drafts.new, undefined);
});

test('不同项目的同名文件、阅读行、当前对话和草稿分别恢复', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('project-a');
  api().selectThread('chat-a');
  api().setDraft('A 的问题');
  api().openFile('Program.cs', 12);
  api().savePosition('Program.cs', 40);
  api().switchProject('project-b');
  assert.equal(api().activePath, '');
  assert.equal(draftFor(api()).content, '');
  api().selectThread('chat-b');
  api().setDraft('B 的问题');
  api().openFile('Program.cs', 3);
  api().savePosition('Program.cs', 9);
  api().switchProject('project-a');
  assert.equal(api().threadId, 'chat-a');
  assert.equal(api().positions['Program.cs'], 40);
  assert.equal(draftFor(api()).content, 'A 的问题');
  api().switchProject('project-b');
  assert.equal(api().threadId, 'chat-b');
  assert.equal(api().positions['Program.cs'], 9);
  assert.equal(draftFor(api()).content, 'B 的问题');
});

test('空白新对话草稿也按项目隔离，发送旧草稿不覆盖新项目输入', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('project-a');
  api().setDraft('A 的草稿');
  const submitted = draftFor(api());
  api().switchProject('project-b');
  api().setDraft('B 的草稿');
  api().consumeDraft('new:project-a', submitted);
  assert.equal(draftFor(api()).content, 'B 的草稿');
  api().switchProject('project-a');
  assert.equal(draftFor(api()).content, '');
  api().setDraft('A 的新问题');
  api().attachNewDraft('created-a');
  assert.equal(api().threadId, 'created-a');
  assert.equal(draftFor(api()).content, 'A 的新问题');
  assert.equal(api().drafts['new:project-a'], undefined);
});

test('刷新时丢弃旧项目首页开关，恢复对话、草稿和各项目的阅读记录', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('project-a');
  api().selectThread('chat-a');
  api().setDraft('A 的草稿');
  api().openFile('A.cs', 2);
  api().savePosition('A.cs', 2);
  api().switchProject('project-b');
  api().selectThread('chat-b');
  api().setDraft('B 的草稿');
  api().openFile('B.cs', 5);
  const options = useWorkspace.persist.getOptions();
  const persisted = { ...options.partialize(api()), projectPage: true };
  const restored = options.merge(persisted, useWorkspace.getInitialState());
  useWorkspace.setState(restored, true);
  assert.equal(api().projectId, 'project-b');
  assert.equal(api().threadId, 'chat-b');
  assert.equal(draftFor(api()).content, 'B 的草稿');
  assert.equal('projectPage' in api(), false);
  assert.equal('setProjectPage' in api(), false);
  assert.equal('projectPage' in options.partialize(api()), false);
  assert.equal(api().activePath, 'B.cs');
  api().switchProject('project-a');
  assert.equal(api().threadId, 'chat-a');
  assert.equal(draftFor(api()).content, 'A 的草稿');
  assert.equal(api().activePath, 'A.cs');
  assert.equal(api().jump.line, 2);
});

test('更换源码目录清空所有旧阅读状态，保留对话和未发送问题', () => {
  reset();
  const api = () => useWorkspace.getState();
  api().initializeProject('project-a');
  api().selectThread('chat-a');
  api().setDraft('继续分析');
  api().openFile('Program.cs', 20);
  api().savePosition('Program.cs', 20);
  api().setDirectoryExpanded('folder', true);
  api().setSourceMode('Program.cs', true);
  api().closeFile('Program.cs');
  api().resetProjectSource('project-a');
  assert.equal(api().threadId, 'chat-a');
  assert.equal(draftFor(api()).content, '继续分析');
  assert.deepEqual(api().positions, {});
  assert.deepEqual(api().closedFiles, []);
  assert.deepEqual(api().expandedDirectories, []);
  assert.deepEqual(api().sourceModes, {});
  api().switchProject('project-b');
  api().switchProject('project-a');
  assert.equal(api().threadId, 'chat-a');
  assert.deepEqual(api().paths, []);
});
