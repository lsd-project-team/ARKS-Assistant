import { lazy, Suspense, useEffect, useState, useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  CheckCheck,
  ClipboardList,
  Database,
  Menu,
  MessageSquareText,
  Settings2,
  Users,
} from 'lucide-react';
import { AccountMenu } from '../auth/AccountMenu';
import { useAppearance } from '../lib/appearance';
import { useWorkspace } from '../lib/store';
import { useHandoverNavigation } from '../handover/navigation';
import { Toasts } from '../components/Toasts';
import { AppearanceSwitch } from '../components/AppearanceSwitch';
import { Button, ErrorText, Modal } from '../components/ui';
import type { ProjectList } from '../types';
import { adminApi } from './client';
import { adminRoute } from './navigation';
import './admin.css';
import '../styles/settings.css';

const OverviewPage = lazy(() =>
  import('./OverviewPage').then((module) => ({ default: module.OverviewPage })),
);
const UsersPage = lazy(() =>
  import('./UsersPage').then((module) => ({ default: module.UsersPage })),
);
const QuestionsPage = lazy(() =>
  import('./QuestionsPage').then((module) => ({ default: module.QuestionsPage })),
);
const ConfigurationPage = lazy(() =>
  import('./ConfigurationPage').then((module) => ({ default: module.ConfigurationPage })),
);
const HandoverWorkspace = lazy(() => import('../handover/HandoverWorkspace'));

const navigation = [
  { id: 'overview', title: '管理概览', href: '#admin/overview', icon: BarChart3 },
  { id: 'users', title: '用户管理', href: '#admin/users', icon: Users },
  { id: 'questions', title: 'AI 问答记录', href: '#admin/questions', icon: MessageSquareText },
  { id: 'handover', title: '交接管理', href: '#handover/materials', icon: ClipboardList },
  { id: 'reviews', title: '复核与追溯', href: '#handover/updates', icon: CheckCheck },
  { id: 'settings', title: '系统配置', href: '#admin/settings', icon: Settings2 },
  { id: 'data', title: '数据维护', href: '#admin/data', icon: Database },
];

function subscribe(listener: () => void) {
  window.addEventListener('hashchange', listener);
  return () => window.removeEventListener('hashchange', listener);
}

export default function AdminShell() {
  const hash = useSyncExternalStore(subscribe, () => location.hash);
  const handoverNavigation = useHandoverNavigation();
  const route = adminRoute(hash);
  const handover = { ...route.handover, navigate: handoverNavigation.navigate };
  const [mobile, setMobile] = useState(false);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [pendingHref, setPendingHref] = useState('');
  const appearance = useAppearance((state) => state.mode);
  const list = useQuery({
    queryKey: ['admin-bootstrap'],
    queryFn: () => adminApi<ProjectList>('/projects'),
  });
  const page = route.page;
  useEffect(() => {
    document.documentElement.dataset.appearance = appearance;
  }, [appearance]);
  useEffect(() => {
    if (!route.valid) location.hash = 'admin/overview';
    setMobile(false);
  }, [hash]);
  useEffect(() => {
    if (!list.data) return;
    const current = useWorkspace.getState().projectId;
    if (!list.data.projects.some((project) => project.id === current))
      useWorkspace
        .getState()
        .switchProject(list.data.default_project_id || list.data.projects[0]?.id || 'independent');
  }, [list.data]);
  return (
    <div
      className="admin-shell"
      data-mobile-open={mobile}
      onClickCapture={(event) => {
        const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#"]');
        if (settingsDirty && link && link.hash !== hash) {
          event.preventDefault();
          event.stopPropagation();
          setPendingHref(link.hash);
        }
      }}
    >
      <aside className="admin-navigation" aria-label="管理员导航">
        <a href="#admin/overview" className="admin-brand">
          <img src="/brand/arks-assistant-icon.png" alt="" />
          <div>
            <strong>ARKS</strong>
            <span>管理工作区</span>
          </div>
        </a>
        <span className="admin-nav-caption">工作区管理</span>
        <nav>
          {navigation.map((item) => (
            <a
              href={item.href}
              key={item.id}
              className={page === item.id ? 'active' : ''}
              aria-current={page === item.id ? 'page' : undefined}
            >
              <item.icon size={19} />
              {item.title}
            </a>
          ))}
        </nav>
        <div className="admin-navigation-tools">
          <AppearanceSwitch />
        </div>
      </aside>
      {mobile && (
        <button
          className="admin-mobile-shade"
          aria-label="关闭管理导航"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="admin-content">
        <div className="admin-topbar">
          <button
            className="admin-mobile-menu"
            aria-label="展开管理导航"
            onClick={() => setMobile(!mobile)}
          >
            <Menu size={20} />
          </button>
          <span>
            管理工作区{' '}
            <span className="admin-breadcrumb">
              / {navigation.find((item) => item.id === page)?.title}
            </span>
          </span>
          <AccountMenu />
        </div>
        <ErrorText error={list.error} />
        {list.isError && <Button onClick={() => void list.refetch()}>重新连接</Button>}
        <main className="admin-main" key={page}>
          <Suspense
            fallback={
              <p className="admin-page" role="status">
                正在加载管理页面…
              </p>
            }
          >
            {page === 'overview' && <OverviewPage />}
            {page === 'users' && <UsersPage />}
            {page === 'questions' && <QuestionsPage identifier={route.questionId} />}
            {(page === 'handover' || page === 'reviews') && (
              <HandoverWorkspace
                management
                tab={handover.tab}
                recordId={handover.recordId}
                version={handover.version}
                navigate={handover.navigate}
              />
            )}
            {(page === 'settings' || page === 'data') && list.data && (
              <ConfigurationPage dataOnly={page === 'data'} onDirtyChange={setSettingsDirty} />
            )}
          </Suspense>
        </main>
      </div>
      <Toasts />
      <Modal open={!!pendingHref} title="配置尚未保存" onClose={() => setPendingHref('')}>
        <div className="dialog-body">
          <p>当前页面有未保存的配置，请保存后切换，或放弃本次修改。</p>
        </div>
        <div className="modal-footer">
          <Button onClick={() => setPendingHref('')}>继续编辑</Button>
          <Button
            onClick={() => {
              setSettingsDirty(false);
              location.hash = pendingHref;
              setPendingHref('');
            }}
          >
            放弃修改并切换
          </Button>
        </div>
      </Modal>
    </div>
  );
}
