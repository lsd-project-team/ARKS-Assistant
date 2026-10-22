import { knownDelay, milliseconds } from './format.ts';
import type { SourceAction } from './source-types.ts';

const actionNames: Record<string, string> = {
  InteractiveAction: '流道交互',
  BondPositionVisionTest: '焊点定位精度测试',
  CheckInkDotActionNode: '墨点检测',
};

const pendingNotes: Record<string, string> = {
  S1DispenseCorrectionActionNode: '需补全运动与视觉等待参数',
  S1DispenseActionNode: '需补全轨迹与等待参数',
  PickActionNode: '需补全运动与取料等待参数',
};

export function actionPresentation(row: SourceAction) {
  const station = row.group.match(/^S[12]\b/)?.[0] || row.group;
  const name = actionNames[row.class_name] || row.name.replace(/^S[12]\s+/, '');
  if (row.execution_status === 'unavailable' || row.execution_status === 'skipped') {
    const unavailable = row.execution_status === 'unavailable';
    return {
      station,
      name,
      duration: unavailable ? '空跑不可执行' : '空跑不动作',
      remainder: '',
      note: unavailable ? '源码模拟分支无法正常完成' : '源码空跑分支直接跳过',
      hasDuration: false,
    };
  }
  const low = row.known_delay_min_ms;
  const high = row.known_delay_max_ms;
  const hasDelay = low != null && (low > 0 || (high != null && high > 0));
  const hasTotal = row.total_ms != null && row.total_ms > 0;
  const duration = hasTotal
    ? `${milliseconds(row.total_ms)} ms`
    : hasDelay
      ? knownDelay(row)
      : row.total_ms === 0
        ? '无固定停留'
        : '待补参数';

  // 已知停留只是动作的一部分，主表也要保留尚未算出的耗时，不能冒充总时长。
  const pending = [row.motion_count > 0 && '运动', row.wait_count > 0 && '等待'].filter(Boolean);
  const remainder =
    row.total_ms == null && hasDelay
      ? pending.length
        ? `+ ${pending.join('与')}时间`
        : '+ 其他待定耗时'
      : '';
  let note = '源码参数或调用耗时尚未确定';
  if (row.total_ms === 0) note = '源码未设置固定停留，不表示实际耗时为零';
  else if (hasTotal) note = '按源码模拟逻辑计算';
  else if (hasDelay) {
    note = `可算停留 ${knownDelay(row)}，其余耗时待定`;
    if (row.class_name === 'UpLookCorrectionActionNode' && high != null) {
      note = `单点停留 ${milliseconds(low)} ms，双点停留 ${milliseconds(high)} ms`;
    } else if (row.class_name === 'BondActionNode' && low === high) {
      note = `固定停留 ${milliseconds(low)} ms，另含运动与抬起`;
    }
  } else if (pendingNotes[row.class_name]) note = pendingNotes[row.class_name];
  else if (pending.length) note = `需补全${pending.join('与')}参数`;
  if (row.kind === 'placeholder') note = '源码中尚无动作实现';
  return { station, name, duration, remainder, note, hasDuration: hasDelay || hasTotal };
}

export function filterActions(
  rows: SourceAction[],
  { auxiliary, group, search }: { auxiliary: boolean; group: string; search: string },
) {
  const query = search.trim().toLocaleLowerCase();
  return rows.filter((row) => {
    if ((row.kind !== 'node') !== auxiliary || (group && row.group !== group)) return false;
    const { name, station } = actionPresentation(row);
    return `${station} ${name}`.toLocaleLowerCase().includes(query);
  });
}

function csvCell(value: string) {
  const safe = /^[=+\-@]/.test(value.trimStart()) ? `'${value}` : value;
  return `"${safe.replaceAll('"', '""')}"`;
}

export function actionTableCsv(rows: SourceAction[]) {
  const cells = [
    ['工位', '动作名称', '动作耗时（源码模拟）', '说明'],
    ...rows.map((row) => {
      const { station, name, duration, remainder, note } = actionPresentation(row);
      return [station, name, [duration, remainder].filter(Boolean).join(' '), note];
    }),
  ];
  return '\ufeff' + cells.map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
}
