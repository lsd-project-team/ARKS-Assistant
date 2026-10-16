import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, LoaderCircle, LockKeyhole, LogOut, UserRound } from 'lucide-react';
import { usePopupPosition } from '../hooks/usePopupPosition';
import { useAuth } from './AuthContext';
import { PasswordDialog, ProfileDialog, roleNames } from './AccountDialogs';
import { requestLogout } from './accountRequests';
import '../styles/account.css';

export function AccountMenu() {
  const { session, endSession } = useAuth();
  const [open, setOpen] = useState(false);
  const [dialog, setDialog] = useState<'profile' | 'password'>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const position = usePopupPosition(open, popup, trigger);
  const user = session?.user;

  function close(restore = true) {
    setOpen(false);
    if (restore) trigger.current?.focus();
  }
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (
        !popup.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        close(false);
    };
    const scrolled = () => close(false);
    document.addEventListener('pointerdown', outside);
    // 菜单使用 Portal；页面滚动后关闭，避免它停留在旧的锚点位置。
    window.addEventListener('scroll', scrolled, true);
    return () => {
      document.removeEventListener('pointerdown', outside);
      window.removeEventListener('scroll', scrolled, true);
    };
  }, [open]);
  useEffect(() => {
    if (open && position.visibility === 'visible')
      popup.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
  }, [open, position.visibility]);
  function navigate(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' || event.key === 'Tab') {
      if (event.key === 'Escape') event.preventDefault();
      close();
      return;
    }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)'),
    );
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? items.length - 1
          : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items[next]?.focus();
  }
  async function logout() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await requestLogout();
      endSession();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : '退出登录失败，请重试。');
      setBusy(false);
    }
  }
  if (!user) return null;
  const displayName = user.display_name.trim() || user.username;
  return (
    <div className="account-control">
      <button
        ref={trigger}
        type="button"
        className="account-trigger"
        aria-label={`账号菜单：${displayName}，${roleNames[user.role]}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => {
          setOpen(!open);
          setError('');
        }}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <span className="account-name" title={displayName}>
          {displayName}
        </span>
        <span className="account-role">{roleNames[user.role]}</span>
        <ChevronDown size={14} className="account-chevron" aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={popup}
            id={menuId}
            className="account-menu"
            style={position}
            role="menu"
            aria-label="账号菜单"
            onKeyDown={navigate}
          >
            <button
              type="button"
              role="menuitem"
              disabled={busy}
              onClick={() => {
                close(false);
                setDialog('profile');
              }}
            >
              <UserRound size={18} />
              个人信息
            </button>
            <button
              type="button"
              role="menuitem"
              disabled={busy}
              onClick={() => {
                close(false);
                setDialog('password');
              }}
            >
              <LockKeyhole size={18} />
              修改密码
            </button>
            <div className="account-menu-divider" role="separator" />
            <button type="button" role="menuitem" disabled={busy} onClick={() => void logout()}>
              {busy ? <LoaderCircle size={18} className="account-spinner" /> : <LogOut size={18} />}
              {busy ? '正在退出…' : '退出登录'}
            </button>
            {error && (
              <p className="account-menu-error" role="alert">
                {error}
              </p>
            )}
          </div>,
          document.body,
        )}
      {dialog === 'profile' && (
        <ProfileDialog
          onClose={() => {
            setDialog(undefined);
            trigger.current?.focus();
          }}
        />
      )}
      {dialog === 'password' && (
        <PasswordDialog
          onClose={() => {
            setDialog(undefined);
            trigger.current?.focus();
          }}
        />
      )}
    </div>
  );
}
