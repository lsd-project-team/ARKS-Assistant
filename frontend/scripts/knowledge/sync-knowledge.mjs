import { knowledgePath, projectRoot } from './resources.mjs';
import { cp } from 'node:fs/promises';
import { resolve } from 'node:path';

const legacy = resolve(process.argv[2] || resolve(projectRoot, '其他模块/archify-ui'));
// 只同步流程资料，不再恢复已移除的历史源码索引与快照。
await cp(resolve(legacy, 'public/archify'), knowledgePath('archify/'), { recursive: true });
console.log('流程资料已同步');
