import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';

const dom = new JSDOM('<div id="root"></div>', { url: 'http://test/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.localStorage = dom.window.localStorage;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
const result = await build({
  stdin: {
    contents: `export {useCodeWorkPanel} from './src/app/layouts/hooks/useCodeWorkPanel';
      export {useWorkspace} from './src/app/state/store';`,
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'ts',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
});
const compiled = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  compiled,
  compiled.exports,
);
const { useCodeWorkPanel, useWorkspace } = compiled.exports;
let panel;
function Harness() {
  panel = useCodeWorkPanel();
  return createElement('button', { onClick: panel.show }, '查看变更');
}
async function mounted(verify, initial = {}) {
  useWorkspace.setState(
    {
      ...useWorkspace.getInitialState(),
      projectId: 'project-1',
      threadId: 'thread-1',
      codeOpen: false,
      explorerOpen: false,
      ...initial,
    },
    true,
  );
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () => root.render(createElement(Harness)));
    const trigger = document.querySelector('button');
    trigger.focus();
    await act(async () => trigger.click());
    assert.equal(panel.open, true);
    assert.equal(useWorkspace.getState().codeOpen, true);
    assert.equal(useWorkspace.getState().explorerOpen, false);
    await verify(trigger);
  } finally {
    await act(async () => root.unmount());
  }
}

test('打开变更保留草稿，重复打开不覆盖原布局，关闭恢复焦点和原工作区', async () => {
  const drafts = { 'thread-1': { content: '还未发送的问题', selections: [] } };
  await mounted(
    async (trigger) => {
      await act(async () => panel.show());
      await act(async () => useWorkspace.getState().setLayout({ chatRatio: 0.55 }));
      await act(async () => panel.close());
      const state = useWorkspace.getState();
      assert.equal(panel.open, false);
      assert.equal(state.codeOpen, false);
      assert.equal(state.explorerOpen, false);
      assert.equal(state.mobile, 'chat');
      assert.equal(state.chatRatio, 0.55);
      assert.deepEqual(state.drafts, drafts);
      assert.equal(document.activeElement, trigger);
    },
    { drafts },
  );
});

test('关闭右栏恢复原来的源码、文件树和专注状态', async () => {
  await mounted(
    async () => {
      assert.equal(useWorkspace.getState().readingFocused, false);
      await act(async () => panel.close());
      const state = useWorkspace.getState();
      assert.equal(state.codeOpen, true);
      assert.equal(state.explorerOpen, true);
      assert.equal(state.readingFocused, true);
      assert.equal(state.jump.line, 40);
    },
    {
      codeOpen: true,
      explorerOpen: true,
      readingFocused: true,
      activePath: 'Controllers/Previous.cs',
      positions: { 'Controllers/Previous.cs': 40 },
      jump: { line: 12, time: 1, align: 'start' },
    },
  );
});

test('点击源码引用退出变更并保留新路径和源码布局', async () => {
  await mounted(async () => {
    await act(async () => useWorkspace.getState().openFile('Controllers/Next.cs', 12));
    const state = useWorkspace.getState();
    assert.equal(panel.open, false);
    assert.equal(state.activePath, 'Controllers/Next.cs');
    assert.equal(state.jump.line, 12);
    assert.equal(state.codeOpen, true);
    assert.equal(state.mobile, 'code');
  });
});

test('切换对话关闭旧变更并恢复布局，切换项目不覆盖新项目的布局', async () => {
  await mounted(async () => {
    await act(async () => useWorkspace.setState({ threadId: 'thread-2' }));
    assert.equal(panel.open, false);
    assert.equal(useWorkspace.getState().codeOpen, false);
  });
  await mounted(async () => {
    await act(async () =>
      useWorkspace.setState({ projectId: 'project-2', threadId: 'thread-2', explorerOpen: true }),
    );
    assert.equal(panel.open, false);
    assert.equal(useWorkspace.getState().explorerOpen, true);
    assert.equal(useWorkspace.getState().codeOpen, true);
  });
});

test('通过分隔条收起工作区时不被旧布局重新打开', async () => {
  await mounted(async () => {
    await act(async () => useWorkspace.getState().collapsePane('chat'));
    assert.equal(panel.open, false);
    assert.equal(useWorkspace.getState().codeOpen, false);
    assert.equal(useWorkspace.getState().mobile, 'chat');
  });
});
