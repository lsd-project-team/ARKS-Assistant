import { Network } from 'lucide-react';
import { useEffect } from 'react';
import { useAppearance } from '../../settings/lib/appearance';
import { AppearanceSwitch } from '../../settings/components/AppearanceSwitch';
import { LoginBrand } from './LoginBrand';
import { LoginForm } from './LoginForm';
import './login.css';

export default function LoginPage() {
  const mode = useAppearance((state) => state.mode);
  useEffect(() => {
    document.documentElement.dataset.appearance = mode;
  }, [mode]);
  useEffect(() => {
    const previous = document.title;
    document.title = '登录 · ARKS 智能助手';
    return () => {
      document.title = previous;
    };
  }, []);
  return (
    <div className="login-page">
      <header className="login-header">
        <a className="login-header-brand" href="#login" aria-label="ARKS 智能助手登录">
          <img src="/brand/arks-assistant-icon.png" alt="" width="38" height="38" />
          <span>
            ARKS <span className="login-header-name">智能助手</span>
          </span>
        </a>
        <div className="login-header-tools">
          <span className="login-network-badge">
            <Network size={16} />
            公司内网
          </span>
          <AppearanceSwitch />
        </div>
      </header>
      <main className="login-main">
        <div className="login-card">
          <LoginBrand />
          <LoginForm />
        </div>
      </main>
    </div>
  );
}
