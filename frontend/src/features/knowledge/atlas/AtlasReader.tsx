import { SourceGuidePanel } from '../SourceGuidePanel';
import type { ComponentType } from 'react';
import { ArchifyFigure, ReadingFigure } from '../coordinates/ArchifyFigure';
import { functionalArtifacts } from '../data/functionalTopics';
import { CalibrationPersistence } from './CalibrationPersistence';
import { MotionOrdering } from './MotionOrdering';
import { ToolCalibrationPersistence } from './ToolCalibrationPersistence';
import { GlobalCalibrationPersistence } from './GlobalCalibrationPersistence';
import '../coordinates/coordinates.css';

const tablesByStep: Record<string, ComponentType> = {
  'gc-completion/persistence': GlobalCalibrationPersistence,
  'tc-results/persistence': ToolCalibrationPersistence,
  'sm-order/table': MotionOrdering,
  'cc-persistence/order': CalibrationPersistence,
};

const diagramsByStep: Record<string, { id: string; title: string; narrow?: string }> = {
  'gc-points/overview': { id: 'global-region-chain', title: '新版扫描数据与区域补偿主链' },
  'gc-driver/overview': { id: 'global-driver-mapping', title: '旧版二维映射的驱动分支' },
  'tc-entry/overview': { id: 'tool-calibration-entry', title: 'S2 校准页面的独立入口' },
  'sm-order/overview': {
    id: 'safe-motion-branches',
    title: 'XYZ 安全移动的高度分支',
    narrow: 'safe-motion-reading',
  },
  'cc-dispatch/overview': { id: 'camera-calibration', title: 'S2 自动标定执行顺序' },
  'pv-acquisition/overview': { id: 'vision-point', title: '单个物料定位点的公共链路' },
  'product-update/overview': { id: 'product-update', title: '定位结果怎样更新产品坐标' },
};

export function functionalVisual(flow: string, step: string) {
  const key = `${flow}/${step}`;
  const Table = tablesByStep[key];
  if (Table) return <Table />;
  if (key === 'product-hierarchy/chain') return <ArchifyFigure id="product-tree" />;
  const diagram = diagramsByStep[key];
  if (!diagram) return null;
  return (
    <ReadingFigure
      diagram={{
        ...functionalArtifacts[diagram.id],
        id: diagram.id,
        title: diagram.title,
        narrow: diagram.narrow ? functionalArtifacts[diagram.narrow] : undefined,
      }}
    />
  );
}

export function AtlasReader({ page }: { page: string }) {
  return (
    <div className="atlas-reader">
      <SourceGuidePanel key={page} page={page} renderVisual={functionalVisual} />
      <nav className="section card panel" aria-label="公共流程">
        <a className="text-button" href="#topic/g0">
          G0 坐标转换与生产应用 →
        </a>
        {page === 'public-vision' ? (
          <a className="text-button" href="#topic/product-coordinates">
            产品坐标写回与定位限值 →
          </a>
        ) : (
          <a className="text-button" href="#topic/public-vision">
            公共视觉与失败处理 →
          </a>
        )}
        {page === 'motion-safety' && (
          <a className="text-button" href="#topic/recovery">
            暂停停止与物料恢复 →
          </a>
        )}
        {page === 'tool-calibration' && (
          <a className="text-button" href="#topic/camera-calibration">
            相机与机械坐标标定 →
          </a>
        )}
        {page === 'global-calibration' && (
          <a className="text-button" href="#topic/motion-safety">
            安全运动与等待边界 →
          </a>
        )}
      </nav>
    </div>
  );
}
