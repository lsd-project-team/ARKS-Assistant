import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { groupReplies } from '../../src/features/chat/lib/replyHistory.ts';

const environment = { chosen: '' };
const compiled = await build({
  stdin: {
    contents:
      "export { ReplyVersions } from './src/features/chat/components/ReplyVersions';" +
      "export { ReansweredQuestion } from './src/features/chat/components/ReansweredQuestion';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'reply-boundaries',
      setup(builder) {
        builder.onResolve({ filter: /^(react|\.\/MessageBubble)$/ }, ({ path }) => ({
          path,
          namespace: 'reply-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'reply-boundary' }, ({ path }) => ({
          loader: 'js',
          contents:
            path === 'react'
              ? 'export const useState = () => [environment.chosen, value => { environment.chosen = value; }];'
              : 'export function MessageBubble() { return null; }',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'environment', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
  environment,
);
const { ReplyVersions, ReansweredQuestion } = module.exports;
const message = (id, content = id) => ({ id, role: 'assistant', content, selections: [] });
const run = (id, question, answer, extra = {}) => ({
  id,
  message_id: question,
  response_message_id: answer,
  status: 'completed',
  ...extra,
});
const versions = [
  { message: message('answer-1'), run: run('run-1', 'question-a', 'answer-1') },
  {
    message: message('answer-2'),
    run: run('run-2', 'question-a', 'answer-2', { regenerated_from: 'run-1' }),
  },
];
function find(element, predicate) {
  if (!element || typeof element !== 'object') return;
  if (predicate(element)) return element;
  for (const child of [element.props?.children].flat()) {
    const found = find(child, predicate);
    if (found) return found;
  }
}

test('历史重答独立追加，原回答与中间问答不并入末条版本组', () => {
  const messages = ['answer-a', 'answer-b', 'answer-a-new', 'answer-a-v2'].map((id) => message(id));
  const runs = [
    run('a', 'question-a', 'answer-a'),
    run('b', 'question-b', 'answer-b'),
    run('a-new', 'reanswered-a', 'answer-a-new', { regenerated_from: 'a' }),
    run('a-v2', 'reanswered-a', 'answer-a-v2', { regenerated_from: 'a-new' }),
  ];
  const { replyRuns, versionGroups } = groupReplies(messages, runs);
  assert.deepEqual([...versionGroups.keys()], ['question-a', 'question-b', 'reanswered-a']);
  assert.deepEqual(
    versionGroups.get('question-a').map((row) => row.message.id),
    ['answer-a'],
  );
  assert.deepEqual(
    versionGroups.get('reanswered-a').map((row) => row.message.id),
    ['answer-a-new', 'answer-a-v2'],
  );
  assert.equal(replyRuns.get('answer-b').id, 'b');
});

test('末条回答原位显示两个版本，左右按钮能切换到旧版并从所选版本再次生成', () => {
  environment.chosen = '';
  const requests = [];
  const props = {
    versions,
    selectedMessage: '',
    canRegenerate: true,
    onRegenerate: (id) => requests.push(id),
  };
  let tree = ReplyVersions(props);
  assert.equal(
    find(tree, (node) => node.type.name === 'MessageBubble').props.message.id,
    'answer-2',
  );
  find(tree, (node) => node.props['aria-label'] === '上一版回复').props.onClick();
  tree = ReplyVersions(props);
  const bubble = find(tree, (node) => node.type.name === 'MessageBubble');
  assert.equal(bubble.props.message.id, 'answer-1');
  assert.equal(bubble.props.canRegenerate, true);
  assert.equal(
    find(tree, (node) => node.props['aria-label'] === '上一版回复').props.disabled,
    true,
  );
  bubble.props.onRegenerate('run-1');
  assert.deepEqual(requests, ['run-1']);
  assert.equal(environment.chosen, '');
  const third = { message: message('answer-3'), run: run('run-3', 'question-a', 'answer-3') };
  tree = ReplyVersions({ ...props, versions: [...versions, third] });
  assert.equal(
    find(tree, (node) => node.type.name === 'MessageBubble').props.message.id,
    'answer-3',
  );
});

test('只读、运行中等上层禁用状态及未完成回复不能开放重新生成', () => {
  environment.chosen = '';
  for (const props of [
    { versions, canRegenerate: false },
    {
      versions: [{ ...versions[0], run: { ...versions[0].run, status: 'failed' } }],
      canRegenerate: true,
    },
  ]) {
    const tree = ReplyVersions({ ...props, selectedMessage: '', onRegenerate: () => {} });
    assert.equal(
      find(tree, (node) => node.type.name === 'MessageBubble').props.canRegenerate,
      false,
    );
  }
});

test('追加重答标明原问题且原文只作文本，保留换行与长标题', () => {
  const original = '原问题\n<script>test()</script>';
  const html = renderToStaticMarkup(
    createElement(ReansweredQuestion, { message: message('q', original) }),
  );
  assert.match(html, /重新回答：/);
  assert.match(html, /原问题\n&lt;script&gt;test\(\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});
