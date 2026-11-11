import { useRef, useEffect } from 'react';
import { NavigationIcon } from '../../shared/ui/NavigationIcon';
import { useAppearance } from '../settings/lib/appearance';
import { routeNames, type Route } from './routes';
import { WorkspaceHeading } from '../../app/layouts/WorkspaceHeader';
import { GraphAtlas, DiagramDetail } from './KnowledgePages';
import './legacy-styles.css';

export default function KnowledgeWorkspace({
  route,
  navigate,
}: {
  route: Route;
  navigate: (route: Route) => void;
}) {
  const mode = useAppearance((state) => state.mode);
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [route]);
  const theme = mode === 'dark' ? 'dark' : 'light';
  let page;
  switch (route.kind) {
    case 'graphs':
      page = <GraphAtlas navigate={navigate} />;
      break;
    case 'graph':
      page = (
        <DiagramDetail
          key={route.slug}
          id={route.slug}
          view={route.view}
          section={route.section}
          focusedSignal={route.signal}
          navigate={navigate}
          theme={theme}
        />
      );
      break;
    case 'catalog':
      page = (
        <DiagramDetail
          key={route.id}
          id={route.id}
          view={route.view}
          focusedSignal={route.signal}
          section={route.section}
          navigate={navigate}
          theme={theme}
        />
      );
      break;
    default:
      page = <GraphAtlas navigate={navigate} />;
  }
  return (
    <section className="knowledge-workspace" aria-label="功能与流程" ref={scroller}>
      <WorkspaceHeading className="knowledge-page-heading">
        <div className="breadcrumb knowledge-heading-title">
          <NavigationIcon kind="modules" size={23} />
          <strong>{routeNames[route.kind]}</strong>
        </div>
      </WorkspaceHeading>
      <div className="knowledge-content">{page}</div>
    </section>
  );
}
