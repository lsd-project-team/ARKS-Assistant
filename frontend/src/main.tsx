import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApplicationEntry } from './app/ApplicationEntry';
import { AuthBoundary } from './features/auth/AuthBoundary';
import { useAppearance } from './features/settings/lib/appearance';
import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import '@fontsource-variable/noto-sans-sc';
import './shared/styles/base.css';
import './shared/styles/legacy-visual.css';
import './shared/styles/refined-interface.css';
import './shared/styles/overlays.css';
import './features/chat/styles/conversation-search.css';
import './features/chat/styles/chat-layout.css';
import './features/chat/styles/chat-welcome.css';
import './app/layouts/styles/navigation-layout.css';
import './app/layouts/styles/layout-motion.css';
import './features/source_reader/styles/file-tabs.css';
import './features/projects/styles/projects.css';
import './app/layouts/styles/sidebar-navigation.css';
import './shared/styles/theme-interface.css';
import './shared/styles/control-surfaces.css';
import './features/chat/styles/answer-content.css';
import './features/chat/styles/rich-content.css';

// 项目数据加载前先恢复外观，避免刷新时短暂显示另一套主题的加载页。
document.documentElement.dataset.appearance = useAppearance.getState().mode;

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15000, retry: 1 } },
});
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthBoundary>
        <ApplicationEntry />
      </AuthBoundary>
    </QueryClientProvider>
  </React.StrictMode>,
);
