import { createContext, useContext } from 'react';
import type { AuthSession } from './session';

export interface AuthContextValue {
  session: AuthSession | null;
  acceptSession: (session: AuthSession) => void;
  endSession: (notice?: string) => void;
  notice: string;
  returnAfterLogin: () => string;
}
export const AuthContext = createContext<AuthContextValue | null>(null);
export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('当前页面缺少登录上下文');
  return auth;
}
