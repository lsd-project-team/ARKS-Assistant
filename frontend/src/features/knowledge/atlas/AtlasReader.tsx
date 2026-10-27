import { SourceGuidePanel } from '../SourceGuidePanel';
import { ArchifyFigure, ReadingFigure } from '../coordinates/ArchifyFigure';
import { functionalArtifacts } from '../data/functionalTopics';
import '../coordinates/coordinates.css';

export function functionalVisual(flow: string, step: string) {
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
      </nav>
    </div>
  );
}
