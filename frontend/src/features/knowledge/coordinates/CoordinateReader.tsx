import { SourceGuidePanel } from '../SourceGuidePanel';
import { CameraMap, CoordinateMap, ProductChain, StorageMap } from './CoordinateMaps';
import { NumericalExample, ProductionPath, TransformFormula } from './CoordinateExamples';
import './coordinates.css';

// 图只交代空间关系或计算结构，分支、保存语义和限制由对应节点的文字说明承担。
export function coordinateVisual(flow: string, step: string) {
  switch (`${flow}/${step}`) {
    case 'g0-relations/reference':
      return <CoordinateMap />;
    case 'g0-relations/product':
      return <ProductChain />;
    case 'g0-general/forward':
      return <TransformFormula />;
    case 'g0-general/inverse':
      return <TransformFormula inverse />;
    case 'g0-general/example':
      return <NumericalExample />;
    case 'g0-camera/inputs':
      return <CameraMap />;
    case 'g0-registry/storage':
      return <StorageMap />;
    case 'g0-production/s1':
      return <ProductionPath />;
    case 'g0-production/s2':
      return <ProductionPath bond />;
    default:
      return null;
  }
}

export function CoordinateReader() {
  return (
    <div className="g0-reader">
      <SourceGuidePanel page="g0" renderVisual={coordinateVisual} />
    </div>
  );
}
