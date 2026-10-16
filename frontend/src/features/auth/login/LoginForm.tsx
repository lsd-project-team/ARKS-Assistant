import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { readRememberedAccount, rememberAccount, requestLogin } from './loginRequest';
import { useAuth } from '../AuthContext';

export function LoginForm() {
  const auth = useAuth();
  const [remembered] = useState(readRememberedAccount);
  const [username, setUsername] = useState(remembered);
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(!!remembered);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const usernameInput = useRef<HTMLInputElement>(null);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const account = username.trim();
    if (!account) {
      setError('请输入账号。');
      usernameInput.current?.focus();
      return;
    }
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setError('');
    setHelpOpen(false);
    rememberAccount(account, remember);
    try {
      const session = await requestLogin({ username: account, password }, controller.signal);
      // 只有服务端真正接受登录后才进入工作台，不在前端模拟认证成功。
      if (!controller.signal.aborted) {
        auth.acceptSession(session);
        window.location.hash = auth.returnAfterLogin();
      }
    } catch (failure) {
      if (!controller.signal.aborted)
        setError(failure instanceof Error ? failure.message : '登录暂时不可用，请稍后重试。');
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return (
    <div className="login-form-panel">
      <form className="login-form" onSubmit={(event) => void submit(event)} aria-busy={busy}>
        <div className="login-form-heading">
          <h1>欢迎回来</h1>
          <p>登录 ARKS，进入你的工作空间</p>
        </div>
        {auth.notice && (
          <p className="login-help-message" role="status">
            {auth.notice}
          </p>
        )}
        <div className="login-fields">
          <div className="login-field">
            <label htmlFor="login-username">账号</label>
            <input
              ref={usernameInput}
              id="login-username"
              name="username"
              type="text"
              value={username}
              placeholder="请输入账号"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={64}
              required
              disabled={busy}
              onChange={(event) => {
                setUsername(event.target.value);
                setError('');
              }}
            />
          </div>
          <div className="login-field">
            <label htmlFor="login-password">密码</label>
            <div className="login-password-field">
              <input
                id="login-password"
                name="password"
                type={passwordVisible ? 'text' : 'password'}
                value={password}
                placeholder="请输入密码"
                autoComplete="current-password"
                maxLength={256}
                required
                disabled={busy}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setError('');
                }}
              />
              <button
                className="login-password-toggle"
                type="button"
                disabled={busy}
                aria-label={passwordVisible ? '隐藏密码' : '显示密码'}
                aria-pressed={passwordVisible}
                onClick={() => setPasswordVisible(!passwordVisible)}
              >
                {passwordVisible ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
        </div>
        <div className="login-form-options">
          <label className="login-remember">
            <input
              type="checkbox"
              checked={remember}
              disabled={busy}
              onChange={(event) => {
                setRemember(event.target.checked);
                if (!event.target.checked) rememberAccount('', false);
              }}
            />
            <span>记住账号</span>
          </label>
          <button
            className="login-help-link"
            type="button"
            disabled={busy}
            aria-expanded={helpOpen}
            aria-controls="login-password-help"
            onClick={() => setHelpOpen(!helpOpen)}
          >
            忘记密码？
          </button>
        </div>
        {helpOpen && (
          <p id="login-password-help" className="login-help-message" role="status">
            请联系管理员重置密码，或开通你的账号。
          </p>
        )}
        {error && (
          <p className="login-error" role="alert">
            {error}
          </p>
        )}
        <button className="login-submit" type="submit" disabled={busy}>
          <span>{busy ? '正在登录…' : '登录'}</span>
          {busy ? <LoaderCircle className="login-spinner" size={19} /> : <ArrowRight size={19} />}
        </button>
        <p className="login-account-note">账号由管理员统一开通</p>
        <div className="login-intranet-note">
          <LockKeyhole size={14} />
          企业内网工作空间
        </div>
      </form>
    </div>
  );
}
