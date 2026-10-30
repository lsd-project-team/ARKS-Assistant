import test from 'node:test';
import assert from 'node:assert/strict';
import { scopedApiUrl } from '../../src/shared/api/apiRoutes.ts';
import { queryGroups } from '../../src/shared/api/querySync.ts';
import {
  instructionBytes,
  validateAgentInstructions,
  MAX_AGENT_INSTRUCTION_BYTES,
} from '../../src/features/settings/lib/agentInstructionsDraft.ts';

test('个人全局指令始终使用账号接口，切换项目不改变路径', () => {
  for (const project of ['first', 'second', 'independent', '']) {
    assert.equal(scopedApiUrl('/agent-instructions', project), '/api/agent-instructions');
  }
  assert.equal(
    scopedApiUrl('/agent-instructions-extra', 'first'),
    '/api/p/first/agent-instructions-extra',
  );
  assert.deepEqual(queryGroups('/agent-instructions'), ['agent-instructions', 'context']);
});

test('指令允许留空，按UTF-8字节限制中文与表情，保留原始换行', () => {
  assert.equal(validateAgentInstructions(''), '');
  assert.equal(validateAgentInstructions(' \r\n'), '');
  assert.equal(validateAgentInstructions('a'.repeat(MAX_AGENT_INSTRUCTION_BYTES)), '');
  assert.match(validateAgentInstructions('a'.repeat(MAX_AGENT_INSTRUCTION_BYTES + 1)), /32 KiB/);
  const content = '中文🙂\r\n';
  assert.equal(instructionBytes(content), 12);
  assert.equal(
    validateAgentInstructions('中'.repeat(Math.floor(MAX_AGENT_INSTRUCTION_BYTES / 3))),
    '',
  );
  assert.match(
    validateAgentInstructions('中'.repeat(Math.floor(MAX_AGENT_INSTRUCTION_BYTES / 3) + 1)),
    /32 KiB/,
  );
  assert.equal(content, '中文🙂\r\n');
});
