import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApplicationEntry } from './components/ApplicationEntry';
import { AuthBoundary } from './auth/AuthBoundary';
import { useAppearance } from './lib/appearance';
import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import '@fontsource-variable/noto-sans-sc';
import './styles.css';
import './styles/legacy-visual.css';
import './styles/refined-interface.css';
import './styles/overlays.css';
import './styles/conversation-search.css';
import './styles/chat-layout.css';
import './styles/chat-welcome.css';
import './styles/navigation-layout.css';
import './styles/layout-motion.css';
import './styles/file-tabs.css';
import './styles/projects.css';
import './styles/sidebar-navigation.css';
import './styles/theme-interface.css';
import './styles/control-surfaces.css';

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
