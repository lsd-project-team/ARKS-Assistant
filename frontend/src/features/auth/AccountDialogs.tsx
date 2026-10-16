import { useEffect, useRef, useState, type FormEvent } from 'react';
import { LoaderCircle, LockKeyhole } from 'lucide-react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { useAuth } from './AuthContext';
import { passwordError, requestPasswordChange, type PasswordChange } from './accountRequests';

export const roleNames = { admin: '管理员', user: '普通用户' } as const;

export function ProfileDialog({ onClose }: { onClose: () => void }) {
  const { session } = useAuth();
  if (!session) return null;
  const { user } = session;
  return (
    <Modal
      open
      onClose={onClose}
      title="个人信息"
      description="查看当前登录账号的信息"
      className="account-dialog"
    >
      <div className="dialog-body account-profile">
        <dl>
          <div>
            <dt>账号</dt>
            <dd>{user.username}</dd>
          </div>
          <div>
            <dt>显示名称</dt>
            <dd>{user.display_name}</dd>
          </div>
          <div>
            <dt>用户身份</dt>
            <dd>{roleNames[user.role]}</dd>
          </div>
        </dl>
      </div>
      <div className="modal-footer">
        <Button onClick={onClose}>关闭</Button>
      </div>
    </Modal>
  );
}

export function PasswordDialog({ onClose }: { onClose: () => void }) {
  const { session, endSession } = useAuth();
  const [values, setValues] = useState<PasswordChange>({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const validation = passwordError(values);
    if (validation) {
      setError(new Error(validation));
      return;
    }
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    setError(undefined);
    try {
      await requestPasswordChange(values, controller.signal);
      if (!controller.signal.aborted) endSession('密码已修改，请使用新密码登录。');
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure);
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <Modal
      open
      onClose={() => !busy && onClose()}
      title="修改密码"
      description="修改后需要在各窗口重新登录"
      className="account-dialog"
    >
      <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
        <div className="dialog-body account-password-form">
          <p className="account-password-account">
            <LockKeyhole size={16} />
            当前账号 <strong>{session?.user.username}</strong>
          </p>
          <input
            type="text"
            autoComplete="username"
            value={session?.user.username || ''}
            readOnly
            hidden
          />
          {(
            [
              ['current_password', '当前密码', 'current-password'],
              ['new_password', '新密码', 'new-password'],
              ['confirm_password', '确认新密码', 'new-password'],
            ] as const
          ).map(([name, label, complete]) => (
            <label key={name}>
              <span>{label}</span>
              <input
                name={name}
                type="password"
                autoComplete={complete}
                value={values[name]}
                required
                minLength={name === 'current_password' ? 1 : 6}
                maxLength={256}
                disabled={busy}
                placeholder={
                  name === 'current_password'
                    ? '请输入当前密码'
                    : name === 'new_password'
                      ? '请输入 6–256 位新密码'
                      : '请再次输入新密码'
                }
                onChange={(event) => {
                  setValues({ ...values, [name]: event.target.value });
                  setError(undefined);
                }}
              />
            </label>
          ))}
          <ErrorText error={error} reveal />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={busy} onClick={onClose}>
            取消
          </Button>
          <Button
            className="primary"
            type="submit"
            disabled={
              busy || !values.current_password || !values.new_password || !values.confirm_password
            }
          >
            {busy && <LoaderCircle size={15} className="account-spinner" />}
            {busy ? '正在修改…' : '确认修改'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
