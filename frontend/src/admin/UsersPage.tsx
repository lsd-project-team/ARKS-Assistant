import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, UserRound } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { Button, ErrorText, Modal } from '../components/ui';
import { Select } from '../components/Select';
import { adminApi, dateTime } from './client';
import type { ManagedAccount } from './types';

export function UsersPage() {
  const cache = useQueryClient();
  const auth = useAuth();
  const [query, setQuery] = useState('');
  const [editor, setEditor] = useState<ManagedAccount | 'new'>();
  const [revoke, setRevoke] = useState<ManagedAccount>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const list = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: () => adminApi<ManagedAccount[]>('/admin/accounts'),
    refetchInterval: 15000,
  });
  const rows =
    list.data?.filter((row) =>
      `${row.username} ${row.display_name}`.toLowerCase().includes(query.toLowerCase()),
    ) || [];
  async function revokeSessions() {
    if (!revoke) return;
    setBusy(true);
    setError(undefined);
    try {
      await adminApi(`/admin/accounts/${revoke.id}/revoke`, { method: 'POST' });
      if (revoke.id === auth.session?.user.id) auth.endSession('登录会话已撤销，请重新登录。');
      setRevoke(undefined);
      await cache.invalidateQueries({ queryKey: ['admin-accounts'] });
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="admin-page">
      <header className="admin-heading">
        <div>
          <span className="admin-eyebrow">WORKSPACE / ACCOUNTS</span>
          <h1>用户管理</h1>
          <p>维护账号、角色与登录状态。</p>
        </div>
        <Button className="primary" onClick={() => setEditor('new')}>
          <Plus size={16} />
          新增账号
        </Button>
      </header>
      <section className="admin-panel">
        <div className="admin-panel-heading">
          <label className="admin-search">
            <Search size={16} />
            <input
              aria-label="搜索用户"
              placeholder="搜索姓名或账号"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <span className="muted">共 {list.data?.length || 0} 个账号</span>
        </div>
        <ErrorText error={list.error || error} />
        {list.isPending && <p role="status">正在读取账号…</p>}
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>角色</th>
                <th>状态</th>
                <th>有效登录会话</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="admin-user-cell">
                      <span className="admin-avatar">
                        <UserRound size={18} />
                      </span>
                      <div>
                        <strong>{row.display_name}</strong>
                        <small>
                          {row.username}
                          {row.id === auth.session?.user.id ? ' · 当前账号' : ''}
                        </small>
                      </div>
                    </div>
                  </td>
                  <td>{row.role === 'admin' ? '管理员' : '普通用户'}</td>
                  <td>
                    <span className={`admin-badge ${row.enabled ? 'success' : ''}`}>
                      {row.enabled ? '已启用' : '已禁用'}
                    </span>
                  </td>
                  <td>{row.sessions}</td>
                  <td>{dateTime(row.created_at)}</td>
                  <td>
                    <div className="admin-row-actions">
                      <Button onClick={() => setEditor(row)}>编辑</Button>
                      <Button onClick={() => setRevoke(row)}>撤销会话</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!list.isPending && !rows.length && <p className="admin-empty">没有匹配的账号。</p>}
      </section>
      {editor && (
        <AccountEditor
          key={typeof editor === 'string' ? editor : editor.id}
          account={editor === 'new' ? undefined : editor}
          onClose={() => setEditor(undefined)}
          onSaved={async (id) => {
            setEditor(undefined);
            if (id === auth.session?.user.id) auth.endSession('账号已更新，请重新登录。');
            await cache.invalidateQueries({ queryKey: ['admin-accounts'] });
          }}
        />
      )}
      <Modal open={!!revoke} title="撤销登录会话" onClose={() => !busy && setRevoke(undefined)}>
        <div className="dialog-body">
          <p>撤销 {revoke?.display_name} 的全部登录会话，用户需要重新登录。</p>
          <ErrorText error={error} />
        </div>
        <div className="modal-footer">
          <Button disabled={busy} onClick={() => setRevoke(undefined)}>
            取消
          </Button>
          <Button className="primary" disabled={busy} onClick={() => void revokeSessions()}>
            {busy ? '正在撤销…' : '确认撤销'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function AccountEditor({
  account,
  onClose,
  onSaved,
}: {
  account?: ManagedAccount;
  onClose: () => void;
  onSaved: (id: string) => void;
}) {
  const [username, setUsername] = useState(account?.username || '');
  const [name, setName] = useState(account?.display_name || '');
  const [role, setRole] = useState(account?.role || 'user');
  const [enabled, setEnabled] = useState(account?.enabled ?? true);
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  async function save(event: FormEvent) {
    event.preventDefault();
    if (password !== repeat) {
      setError(new Error('两次密码不一致'));
      return;
    }
    setBusy(true);
    setError(undefined);
    try {
      const saved = await adminApi<ManagedAccount>(
        `/admin/accounts${account ? `/${account.id}` : ''}`,
        {
          method: account ? 'PATCH' : 'POST',
          body: JSON.stringify({
            ...(account ? {} : { username }),
            display_name: name,
            role,
            enabled,
            ...(password ? { password } : {}),
          }),
        },
      );
      onSaved(saved.id);
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open title={account ? '编辑账号' : '新增账号'} onClose={() => !busy && onClose()}>
      <form onSubmit={save}>
        <div className="dialog-body admin-form">
          <label>
            账号
            <input
              aria-label="账号"
              autoComplete="off"
              required
              disabled={!!account || busy}
              pattern="[A-Za-z0-9_.-]+"
              maxLength={64}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            姓名
            <input
              aria-label="姓名"
              required
              maxLength={120}
              disabled={busy}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            角色
            <Select
              aria-label="角色"
              disabled={busy}
              value={role}
              onValueChange={(value) => setRole(value as typeof role)}
            >
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </Select>
          </label>
          <label className="admin-checkbox">
            <input
              type="checkbox"
              disabled={busy}
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            启用账号
          </label>
          <label>
            {account ? '重置密码（留空保留）' : '初始密码'}
            <input
              aria-label="新密码"
              type="password"
              autoComplete="new-password"
              required={!account}
              minLength={12}
              maxLength={256}
              disabled={busy}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label>
            确认密码
            <input
              aria-label="确认密码"
              type="password"
              autoComplete="new-password"
              required={!account || !!password}
              disabled={busy}
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
            />
          </label>
          <p className="muted">
            密码至少 12 个字符。修改账号后撤销该账号的全部登录会话；最后一个有效管理员受保护。
          </p>
          <ErrorText error={error} />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={busy} onClick={onClose}>
            取消
          </Button>
          <Button className="primary" type="submit" disabled={busy || !name.trim()}>
            {busy ? '正在保存…' : '保存账号'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
