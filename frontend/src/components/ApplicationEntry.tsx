import { lazy, Suspense, useEffect, useSyncExternalStore } from 'react';
import { useAuth } from '../auth/AuthContext';
import { UsageCollector } from '../auth/UsageCollector';

const AdminShell = lazy(() => import('../admin/AdminShell'));

const ProjectShell = lazy(() =>
  import('./ProjectShell').then((module) => ({ default: module.ProjectShell })),
);
const LoginPage = lazy(() => import('../login/LoginPage'));

function subscribeToLocation(listener: () => void) {
  window.addEventListener('hashchange', listener);
  return () => window.removeEventListener('hashchange', listener);
}

export function ApplicationEntry() {
  const role = useAuth().session?.user.role;
  const hash = useSyncExternalStore(subscribeToLocation, () => window.location.hash);
  // 登录页独立加载；展示表单时不读取工作台的项目、源码和对话数据。
  const loginOpen = /^#\/?login(?:\?|$)/.test(hash);
  useEffect(() => {
    if (!loginOpen && role === 'user' && /^#admin(?:\/|$)/.test(hash))
      window.location.hash = 'handover/overview';
  }, [hash, role, loginOpen]);
  return (
    <Suspense
      fallback={
        <div className="project-loading" role="status">
          正在加载…
        </div>
      }
    >
      {loginOpen ? (
        <LoginPage />
      ) : role === 'admin' ? (
        <AdminShell />
      ) : (
        <>
          <UsageCollector />
          <ProjectShell />
        </>
      )}
    </Suspense>
  );
}
