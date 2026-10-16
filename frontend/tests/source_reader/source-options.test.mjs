import assert from 'node:assert/strict';
import { test } from 'node:test';
import { useWorkspace, draftFor } from '../../src/app/state/store.ts';
import { resolvedSources } from '../../src/features/settings/lib/sourceOptions.ts';

test('旧草稿使用兼容来源默认值，关闭资料不影响源码选择', () => {
  assert.deepEqual(resolvedSources(), {
    use_deepwiki: true,
    use_knowledge: true,
    use_memory: true,
  });
  useWorkspace.setState({ threadId: 'source-control', drafts: {} });
  const options = { use_deepwiki: false, use_knowledge: false, use_memory: false };
  useWorkspace.getState().setSourceOptions(options);
  useWorkspace.getState().setDraft('解释入口');
  const draft = draftFor(useWorkspace.getState());
  assert.deepEqual(draft.source_options, options);
  useWorkspace.getState().consumeCommand('source-control', draft);
  assert.deepEqual(draftFor(useWorkspace.getState()).source_options, options);
  useWorkspace.getState().selectThread('another-thread');
  assert.equal(draftFor(useWorkspace.getState()).source_options, undefined);
});
