import { Fragment, lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button, ErrorText } from '../../shared/ui/ui';
import { clearProjectCaches } from '../projects/lib/projectCache';
import { AuthContext } from './AuthContext';
import {
  readSession,
  sessionFetch,
  setSessionAccount,
  setSessionToken,
  type AuthSession,
} from './session';
import { activateWorkspaceAccount } from '../../app/state/store';
import { prepareLegacyWorkspace } from '../../app/state/accountWorkspace';

const LoginPage = lazy(() => import('./login/LoginPage'));

export function AuthBoundary({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState('');
  const current = useRef<AuthSession | null>(null);
  const pending = useRef<AbortController | null>(null);
  const returnTo = useRef(window.location.hash);
  const channel = useRef<BroadcastChannel | null>(null);
  const applying = useRef(0);

  async function applySession(next: AuthSession | null) {
    const revision = ++applying.current;
    const previous = current.current?.user;
    setSessionToken(next?.csrf_token || '');
    setSessionAccount(next?.user.id || '');
    if (previous?.id !== next?.user.id || previous?.role !== next?.user.role) {
      // 先清除管理员缓存，再挂载普通用户页面，避免切换账号时闪现旧复核资料。
      queryClient.clear();
      clearProjectCaches();
      setChecking(true);
      if (next) {
        try {
          await prepareLegacyWorkspace(next.user.id, async <T,>(path: string): Promise<T> => {
            const response = await sessionFetch(path);
            if (!response.ok) throw new Error('无法读取旧工作区归属');
            return response.json() as Promise<T>;
          });
        } catch {
          // 迁移失败仍保留旧原件；先进入当前账号的空工作区，不能沿用上一人的内容。
        }
      }
      if (revision !== applying.current) return;
      activateWorkspaceAccount(next?.user.id || '');
    }
    current.current = next;
    setSession(next);
    setChecking(false);
    setError(undefined);
    if (next) setNotice('');
    if (!next && !/^#\/?login(?:\?|$)/.test(window.location.hash)) {
      returnTo.current = window.location.hash;
      window.location.hash = 'login';
    }
  }

  async function refresh(block = false) {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    if (block) setChecking(true);
    try {
      const next = await readSession(controller.signal);
      if (!controller.signal.aborted) await applySession(next);
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(failure);
        setChecking(false);
      }
    }
  }

  useEffect(() => {
    void refresh(true);
    const expired = () => {
      pending.current?.abort();
      void applySession(null);
      channel.current?.postMessage('changed');
    };
    window.addEventListener('arks-auth-required', expired);
    const timer = window.setInterval(() => void refresh(), 60000);
    channel.current = new BroadcastChannel('arks-auth');
    channel.current.onmessage = () => void refresh(true);
    return () => {
      pending.current?.abort();
      window.removeEventListener('arks-auth-required', expired);
      window.clearInterval(timer);
      channel.current?.close();
    };
  }, []);

  const value = {
    session,
    notice,
    endSession: (message = '') => {
      pending.current?.abort();
      setNotice(message);
      void applySession(null);
      channel.current?.postMessage('changed');
    },
    acceptSession: (next: AuthSession) => {
      pending.current?.abort();
      void applySession(next);
      channel.current?.postMessage('changed');
    },
    returnAfterLogin: () => {
      const target = returnTo.current;
      return target && !/^#\/?login(?:\?|$)/.test(target) ? target.slice(1) : 'handover/overview';
    },
  };
  return (
    <AuthContext.Provider value={value}>
      {checking || error ? (
        <div className="project-loading" role="status">
          {error ? (
            <>
              <ErrorText error={error} />
              <Button onClick={() => void refresh(true)}>重新连接</Button>
            </>
          ) : (
            '正在核对登录状态…'
          )}
        </div>
      ) : session ? (
        <Fragment key={`${session.user.id}:${session.user.role}`}>{children}</Fragment>
      ) : (
        <Suspense fallback={<div className="project-loading">正在加载登录页…</div>}>
          <LoginPage />
        </Suspense>
      )}
    </AuthContext.Provider>
  );
}
