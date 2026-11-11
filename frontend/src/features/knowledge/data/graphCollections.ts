// 只归并目录入口，成员仍指向原图及说明；路由层也使用这份轻量清单。
export const graphCollections: Readonly<Record<string, readonly string[]>> = {
  'zx2200-architecture': ['manual-00'],
  'manual-39': ['manual-18'],
  'manual-40': ['manual-21'],
  'manual-32': ['manual-07'],
  'manual-34': ['manual-09'],
  'manual-31': ['manual-20'],
  'manual-41': ['manual-13'],
  'manual-42': ['manual-16', 'manual-17'],
  'startup-workflow': ['machine-start-readiness-workflow', 'manual-01'],
  'failure-recovery-workflow': [
    'stop-cleanup-workflow',
    'emergency-stop-close-workflow',
    'task-closure-gate-workflow',
    'manual-00-stop',
    'manual-91',
  ],
  'safe-motion-process': ['safe-motion', 'motion-arrival-sequence'],
  'tool-bank-process': ['nozzle-exchange'],
  'manual-maintenance-process': ['manual-epoxy-trial'],
  'camera-calibration-process': [
    'calibration-task-workflow',
    'calibration-execution-workflow',
    'bond-camera-calibration-workflow',
  ],
  'recipe-lifecycle-workflow': [
    'recipe-initialization-workflow',
    'recipe-live-reload-workflow',
    'recipe-switch-sequence',
  ],
  'background-lifecycle-workflow': ['background-task-sequence', 'exit-save-workflow'],
  'runtime-dataflow': ['async-persistence-dataflow', 'statistics-log-producer-workflow'],
  'dispense-workflow': [
    's1-step-commit-gate-workflow',
    's1-return-gates-workflow',
    's1-segment-interaction-workflow',
    's1-defect-outcome-workflow',
    's1-rework-context-workflow',
    's1-stop-rework-recovery-workflow',
    's1-task-loop-pause-workflow',
  ],
  'bonding-workflow': [
    's2-task-entry-boundary-workflow',
    's2-action-boundary-workflow',
    'relative-bond-order-workflow',
  ],
  'wafer-supply-workflow': [
    'wafer-search-gate-workflow',
    'wafer-change-retry-workflow',
    'wafer-pick-handshake-sequence',
    'wafer-vision-outcome-workflow',
  ],
};

export const primaryWorkflowIds = new Set([
  'startup-workflow',
  'transport-workflow',
  'dispense-workflow',
  'wafer-supply-workflow',
  'bonding-workflow',
  'pickup-workflow',
  'bond-action-workflow',
  'failure-recovery-workflow',
]);

const owners = new Map(
  Object.entries(graphCollections).flatMap(([id, members]) =>
    members.map((member) => [member, id] as const),
  ),
);

export const graphOwner = (id: string) => owners.get(id) ?? id;
export function graphMemberIds(id: string): readonly string[] {
  const owner = graphOwner(id);
  return [owner, ...(Object.hasOwn(graphCollections, owner) ? graphCollections[owner] : [])];
}

export function selectedGraphId(id: string, view?: string): string {
  const owner = graphOwner(id);
  // 拒绝跨组参数；旧成员链接没有 view 时仍打开原成员，不丢失阅读位置。
  return view ? (graphMemberIds(owner).includes(view) ? view : owner) : id;
}
