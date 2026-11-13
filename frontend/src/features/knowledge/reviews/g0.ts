import type { SourceGuide } from '../sourceGuides';
import { g0Relations, g0General, g0Camera } from './g0Basics.ts';
import { g0Registry, g0Calibration } from './g0Lifecycle.ts';
import { g0Production, g0Limits } from './g0Production.ts';

export const g0Guide: SourceGuide = {
  id: 'g0-coordinate-review',
  topic: 'g0',
  diagrams: ['g0-coordinate-system'],
  title: '建议阅读顺序',
  flows: [g0Relations, g0General, g0Camera, g0Registry, g0Calibration, g0Production, g0Limits],
  boundaries: [
    {
      text: '本图谱依据 ZX2200 中坐标功能的示教、标定和生产用法整理，说明当前版本的做法。设备的实际原点与轴方向由现场标定和参数决定；这里没有给出可直接用于设备的偏移值。',
      refs: ['g0-math', 'g0-transport-teach', 'g0-cam-ds', 'g0-wafer-move'],
    },
  ],
};
