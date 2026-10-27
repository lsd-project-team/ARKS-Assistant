import { SourceGuidePanel } from '../SourceGuidePanel';
import type { ComponentType } from 'react';
import { ArchifyFigure, ReadingFigure } from '../coordinates/ArchifyFigure';
import { functionalArtifacts } from '../data/functionalTopics';
import { CalibrationPersistence } from './CalibrationPersistence';
import { MotionOrdering } from './MotionOrdering';
import { ToolCalibrationPersistence } from './ToolCalibrationPersistence';
import { GlobalCalibrationPersistence } from './GlobalCalibrationPersistence';
import { LightHardwareTable } from './LightHardwareTable';
import { HeightReadingTable, HeightPersistenceTable } from './HeightMeasurementTables';
import { ForceReadingTable, ForcePersistenceTable } from './ForceControlTables';
import { ToolBankStatusTable, ToolBankPersistenceTable } from './ToolBankTables';
import { MaintenanceEntryTable, MaintenanceSaveTable } from './MaintenanceTables';
import '../coordinates/coordinates.css';

const tablesByStep: Record<string, ComponentType> = {
  'mn-manual/overview': MaintenanceEntryTable,
  'mn-results/persistence': MaintenanceSaveTable,
  'nb-identity/overview': ToolBankStatusTable,
  'nb-results/persistence': ToolBankPersistenceTable,
  'fc-entry/overview': ForceReadingTable,
  'fc-results/persistence': ForcePersistenceTable,
  'mh-entry/overview': HeightReadingTable,
  'mh-results/persistence': HeightPersistenceTable,
  'lc-hardware/overview': LightHardwareTable,
  'gc-completion/persistence': GlobalCalibrationPersistence,
  'tc-results/persistence': ToolCalibrationPersistence,
  'sm-order/table': MotionOrdering,
  'cc-persistence/order': CalibrationPersistence,
};

const diagramsByStep: Record<
  string,
  { id: string; title: string; narrow?: string; readingMinWidth?: number }
> = {
  'mn-trigger/overview': {
    id: 'nozzle-clean-overview',
    title: '非离线取晶的清嘴触发',
    narrow: 'nozzle-clean-reading',
    readingMinWidth: 860,
  },
  'nb-change/overview': {
    id: 'tool-change-overview',
    title: '按工具名称判断与换嘴主链',
    narrow: 'tool-change-reading',
    readingMinWidth: 860,
  },
  'fc-start/overview': {
    id: 'force-calibration-overview',
    title: '闭环标定的驱动分派与保存',
    narrow: 'force-calibration-dispatch',
    readingMinWidth: 780,
  },
  'fc-conversion/overview': {
    id: 'force-input-overview',
    title: '目标力到驱动输入的正常多点路径',
    narrow: 'force-input-conversion',
    readingMinWidth: 780,
  },
  'mh-product/overview': { id: 'height-s1-writeback', title: 'S1 多点有效返回的高度回写路径' },
  'mh-flatness/overview': { id: 'height-flat-batch', title: '平面度单批次的结果链' },
  'lc-acquisition/overview': { id: 'lightness-calibration', title: '亮度采集到保存的正常主链' },
  'lc-application/overview': { id: 'lightness-alarm-edit', title: '点胶相机保持不变的报警编辑' },
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
        readingMinWidth: diagram.readingMinWidth,
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
        {page === 'tool-bank' && (
          <>
            <a className="text-button" href="#topic/tool-calibration">
              工具高度与中心校准 →
            </a>
            <a className="text-button" href="#topic/motion-safety">
              安全运动与等待边界 →
            </a>
          </>
        )}
        {page === 'manual-maintenance' && (
          <>
            <a className="text-button" href="#topic/tool-bank">
              工具更换与人工入口 →
            </a>
            <a className="text-button" href="#topic/height-measurement">
              测高与工具准备 →
            </a>
            <a className="text-button" href="#topic/force-control">
              清洁力控的设定与复位 →
            </a>
            <a className="text-button" href="#topic/motion-safety">
              安全运动与等待边界 →
            </a>
          </>
        )}
        {page === 'height-measurement' && (
          <>
            <a className="text-button" href="#topic/motion-safety">
              安全运动与等待边界 →
            </a>
            <a className="text-button" href="#topic/global-calibration">
              全局标定与旧偏移插值 →
            </a>
          </>
        )}
        {page === 'global-calibration' && (
          <a className="text-button" href="#topic/motion-safety">
            安全运动与等待边界 →
          </a>
        )}
        {page === 'force-control' && (
          <>
            <a className="text-button" href="#topic/height-measurement">
              TouchDown 准备与焊头测高 →
            </a>
            <a className="text-button" href="#topic/motion-safety">
              安全运动与等待边界 →
            </a>
          </>
        )}
      </nav>
    </div>
  );
}
