import { SourceGuidePanel } from '../SourceGuidePanel';
import { ArchifyFigure, ReadingFigure } from '../coordinates/ArchifyFigure';
import { functionalArtifacts } from '../data/functionalTopics';
import { CalibrationPersistence } from './CalibrationPersistence';
import { MotionOrdering } from './MotionOrdering';
import { ToolCalibrationPersistence } from './ToolCalibrationPersistence';
import '../coordinates/coordinates.css';

export function functionalVisual(flow: string, step: string) {
  if (`${flow}/${step}` === 'tc-entry/overview')
    return (
      <ReadingFigure
        diagram={{
          ...functionalArtifacts['tool-calibration-entry'],
          id: 'tool-calibration-entry',
          title: 'S2 校准页面的独立入口',
        }}
      />
    );
  if (`${flow}/${step}` === 'tc-results/persistence') return <ToolCalibrationPersistence />;
  if (`${flow}/${step}` === 'sm-order/table') return <MotionOrdering />;
  if (`${flow}/${step}` === 'sm-order/overview')
    return (
      <ReadingFigure
        diagram={{
          ...functionalArtifacts['safe-motion-branches'],
          narrow: functionalArtifacts['safe-motion-reading'],
          id: 'safe-motion-branches',
          title: 'XYZ 安全移动的高度分支',
        }}
      />
    );
  if (`${flow}/${step}` === 'cc-persistence/order') return <CalibrationPersistence />;
  if (`${flow}/${step}` === 'cc-dispatch/overview')
    return (
      <ReadingFigure
        diagram={{
          ...functionalArtifacts['camera-calibration'],
          id: 'camera-calibration',
          title: 'S2 自动标定执行顺序',
        }}
      />
    );
  if (`${flow}/${step}` === 'pv-acquisition/overview')
    return (
      <ReadingFigure
        diagram={{
          ...functionalArtifacts['vision-point'],
          id: 'vision-point',
          title: '单个物料定位点的公共链路',
        }}
      />
    );
  if (`${flow}/${step}` === 'product-hierarchy/chain') return <ArchifyFigure id="product-tree" />;
  if (`${flow}/${step}` === 'product-update/overview')
    return (
      <ReadingFigure
        diagram={{
          ...functionalArtifacts['product-update'],
          id: 'product-update',
          title: '定位结果怎样更新产品坐标',
        }}
      />
    );
  return null;
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
      </nav>
    </div>
  );
}
