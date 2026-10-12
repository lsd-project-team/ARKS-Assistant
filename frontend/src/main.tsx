import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectShell } from './components/ProjectShell';
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

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15000, retry: 1 } },
});
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ProjectShell />
    </QueryClientProvider>
  </React.StrictMode>,
);
