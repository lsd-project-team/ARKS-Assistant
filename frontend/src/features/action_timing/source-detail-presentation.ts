import { milliseconds } from './format.ts';
import type { SourceAction, SourceComponent, SourceStage } from './source-types.ts';

export const missingLabels: Record<string, string> = {
  motion: '轴起点、有效运动参数及到位条件',
  input: '当前配方、输入值或循环次数',
  feedback: '实际信号或任务完成时刻',
  sdk: 'SDK重载、通信及设备完成时间',
  runtime: '运行门禁、锁或队列条件',
  analysis: '源码分析尚未完成的调用或数值路径',
  external: '外部调用的内部耗时或完成约定',
};

export function motionFixedNote(model: SourceStage['motion_model']) {
  const value = model?.source_fixed_wait_ms;
  return value != null && value > 0
    ? `初始化等门禁通过时，包内固定等待 ${milliseconds(value)} ms；与已启动的运动重叠，不另加到完整运动时间`
    : '';
}

export function componentTime(component: SourceComponent, compact = false) {
  const factors = component.factors || [];
  return `${milliseconds(component.milliseconds)} ms${factors.length ? ` × ${compact ? '待定次数' : factors.join(' × ')}` : ''}`;
}

export function componentPreview(row: SourceAction) {
  const source = row.source_components?.find((part) => part.milliseconds > 0);
  if (source && (row.analysis_unit === 'wizard_step' || row.analysis_unit === 'callback')) {
    return `条件组成 ${componentTime(source, true)}`;
  }
  const actual = row.known_components?.find((part) => part.milliseconds > 0);
  if (actual)
    return `${actual.scope === 'background' ? '后台' : '条件'}停留 ${componentTime(actual, true)}`;
  return source ? `条件组成 ${componentTime(source, true)}` : '';
}

export function motionCompletion(model: SourceStage['motion_model']) {
  return model?.completion?.startsWith('send at t;')
    ? '发令后先执行包内固定等待，再按到位规则等待；已开始的运动与固定等待重叠'
    : model?.completion || '';
}
