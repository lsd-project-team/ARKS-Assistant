import { knownDelay, milliseconds } from './format.ts';
import type { SourceAction } from './source-types.ts';

const actionNames: Record<string, string> = {
  InteractiveAction: '流道交互',
  BondPositionVisionTest: '焊点定位精度测试',
  CheckInkDotActionNode: '墨点检测',
};

const pendingNotes: Record<string, string> = {
  S1DispenseCorrectionActionNode: '定位耗时无法由现有源码确定',
  S1DispenseActionNode: '轨迹与等待耗时未定',
  PickActionNode: '运动与取料等待耗时未定',
};

function perItemTiming(row: SourceAction) {
  return (row.per_item_timing || [])
    .filter((item) => Number.isFinite(item.min_ms) && item.min_ms > 0)
    .map((item) => {
      const unit = item.element_type.split('.').at(-1) === 'Light' ? '每路光源' : '每项';
      const time =
        item.max_ms == null
          ? `≥${milliseconds(item.min_ms)} ms`
          : item.min_ms === item.max_ms
            ? `${milliseconds(item.min_ms)} ms`
            : `${milliseconds(item.min_ms)}–${milliseconds(item.max_ms)} ms`;
      return `${unit} ${time}`;
    })
    .join('；');
}

export function actionPresentation(row: SourceAction) {
  const station = row.group.match(/^S[12]\b/)?.[0] || row.group;
  const node = row.kind === 'node';
  const name = (node && actionNames[row.class_name]) || row.name.replace(/^S[12]\s+/, '');
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
  const itemTiming = perItemTiming(row);
  const duration = hasTotal
    ? `${milliseconds(row.total_ms)} ms`
    : hasDelay
      ? knownDelay(row)
      : itemTiming || (row.total_ms === 0 ? '无固定停留' : '耗时未定');

  // 停留可能与已启动的运动重叠，不能用加号暗示可直接相加为总时长。
  const pending = [row.motion_count > 0 && '运动', row.wait_count > 0 && '等待'].filter(Boolean);
  const remainder =
    row.total_ms == null && hasDelay
      ? pending.length
        ? `已知停留，${pending.join('与')}耗时未定`
        : '已知停留，完整耗时未定'
      : itemTiming && !hasTotal
        ? '数量未知，完整耗时未定'
        : '';
  let note = '源码参数或调用耗时尚未确定';
  if (row.total_ms === 0) note = '源码未设置固定停留，不表示实际耗时为零';
  else if (hasTotal) note = '按源码模拟逻辑计算';
  else if (hasDelay) {
    note = `可算停留 ${knownDelay(row)}，其余耗时待定`;
    if (node && row.class_name === 'UpLookCorrectionActionNode' && high != null) {
      note = `单点停留 ${milliseconds(low)} ms，双点停留 ${milliseconds(high)} ms`;
    } else if (node && row.class_name === 'BondActionNode' && low === high) {
      note = `固定停留 ${milliseconds(low)} ms，另含运动与抬起`;
    }
  } else if (node && pendingNotes[row.class_name]) note = pendingNotes[row.class_name];
  else if (pending.length) note = `${pending.join('与')}耗时无法由现有源码确定`;
  if (itemTiming && row.total_ms == null) {
    note = hasDelay ? `${note}；${itemTiming}，数量未知` : '按每项顺序计算，数量及其余耗时未定';
  }
  if (row.kind === 'placeholder') note = '源码中尚无动作实现';
  return {
    station,
    name,
    duration,
    remainder,
    note,
    hasDuration: hasDelay || hasTotal || !!itemTiming,
  };
}

export function filterActions(
  rows: SourceAction[],
  { auxiliary, group, search }: { auxiliary: boolean; group: string; search: string },
) {
  const query = search.trim().toLocaleLowerCase();
  return rows.filter((row) => {
    if (!(row.primary ?? row.kind === 'node') !== auxiliary || (group && row.group !== group))
      return false;
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
