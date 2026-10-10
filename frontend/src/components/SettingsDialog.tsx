import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Cable, Cpu, HardDrive, Download, LoaderCircle } from 'lucide-react';
import { api, jsonBody } from '../lib/api';
import type { Settings, ModelSettings } from '../types';
import { Button, Modal, ErrorText } from './ui';

export function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const cache = useQueryClient();
  const saved = useQuery({ queryKey: ['settings'], queryFn: () => api<Settings>('/settings') });
  const [settings, setSettings] = useState<Settings>();
  const [mcp, setMcp] = useState('[]');
  const [tab, setTab] = useState('model');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<unknown>();
  useEffect(() => {
    if (open && saved.data && !settings) {
      setSettings(structuredClone(saved.data));
      setMcp(JSON.stringify(saved.data.mcp_servers, null, 2));
      setFeedback('');
      setError(undefined);
    }
  }, [open, saved.data, settings]);
  function modelChange<K extends keyof ModelSettings>(name: K, value: ModelSettings[K]) {
    setSettings((current) =>
      current ? { ...current, model: { ...current.model, [name]: value } } : current,
    );
  }
  async function save() {
    if (!settings) return;
    const updated = { ...settings, mcp_servers: JSON.parse(mcp) };
    const response = await api<Settings>('/settings', {
      method: 'PUT',
      body: jsonBody({ settings: updated }),
    });
    cache.setQueryData(['settings'], response);
    setFeedback('配置已保存');
  }
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    setFeedback('');
    try {
      await action();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open={open}
      onClose={() => {
        setSettings(undefined);
        onClose();
      }}
      title="工作区设置"
      description="模型连接、知识来源与本地数据"
    >
      <div className="dialog-tabs">
        {[
          { id: 'model', title: '模型', icon: Cpu },
          { id: 'mcp', title: 'MCP', icon: Cable },
          { id: 'data', title: '数据', icon: HardDrive },
        ].map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? 'selected' : ''}
            onClick={() => setTab(item.id)}
          >
            <item.icon size={14} />
            {item.title}
          </button>
        ))}
      </div>
      <div className="dialog-body">
        {settings && tab === 'model' && (
          <div className="settings-fields">
            <label>
              接口协议
              <select
                value={settings.model.protocol}
                onChange={(e) =>
                  modelChange('protocol', e.target.value as ModelSettings['protocol'])
                }
              >
                <option value="openai">OpenAI Chat Completions</option>
                <option value="anthropic">Anthropic Messages</option>
              </select>
            </label>
            <label>
              接口地址
              <input
                value={settings.model.base_url}
                onChange={(e) => modelChange('base_url', e.target.value)}
                placeholder="https://example.com/v1"
              />
            </label>
            <label>
              模型名称
              <input
                value={settings.model.model}
                onChange={(e) => modelChange('model', e.target.value)}
              />
            </label>
            <label>
              API 密钥
              <input
                type="password"
                autoComplete="new-password"
                value={settings.model.api_key}
                onChange={(e) => modelChange('api_key', e.target.value)}
                placeholder={settings.model.has_api_key ? '已保存 · 留空保留当前密钥' : '输入密钥'}
              />
            </label>
            <div className="field-pair">
              <label>
                上下文容量
                <input
                  type="number"
                  min={2048}
                  value={settings.model.context_tokens}
                  onChange={(e) => modelChange('context_tokens', Number(e.target.value))}
                />
              </label>
              <label>
                最大回复 token
                <input
                  type="number"
                  min={256}
                  value={settings.model.output_tokens}
                  onChange={(e) => modelChange('output_tokens', Number(e.target.value))}
                />
              </label>
            </div>
            <label>
              压缩模型（可选）
              <input
                value={settings.model.summary_model}
                onChange={(e) => modelChange('summary_model', e.target.value)}
                placeholder="留空使用对话模型"
              />
            </label>
            <Button
              disabled={busy}
              onClick={() =>
                void perform(async () => {
                  await save();
                  const result = await api<{ reply: string }>('/settings/probe', {
                    method: 'POST',
                  });
                  setFeedback(`连接成功 · ${result.reply}`);
                })
              }
            >
              <Cable size={14} />
              保存并测试连接
            </Button>
          </div>
        )}
        {settings && tab === 'mcp' && (
          <div className="settings-fields">
            <label>
              DeepWiki 仓库
              <input
                value={settings.deepwiki_repo}
                onChange={(e) => setSettings({ ...settings, deepwiki_repo: e.target.value })}
                placeholder="owner/repository"
              />
            </label>
            <label>
              MCP 服务器配置
              <textarea
                className="json-editor"
                rows={12}
                value={mcp}
                onChange={(e) => setMcp(e.target.value)}
                spellCheck={false}
              />
            </label>
            <p className="muted">
              支持 Streamable HTTP、SSE 和本地 stdio。headers/env 中的掩码保留已保存值。
            </p>
            <div className="button-row">
              {settings.mcp_servers.map((server) => (
                <Button
                  key={server.id}
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      await save();
                      const result = await api<{ tools: { name: string }[] }>(
                        `/mcp/${server.id}/probe`,
                        { method: 'POST' },
                      );
                      setFeedback(`${server.name} 已连接 · ${result.tools.length} 个工具`);
                    })
                  }
                >
                  <Cable size={14} />
                  测试 {server.name}
                </Button>
              ))}
            </div>
          </div>
        )}
        {settings && tab === 'data' && (
          <div className="settings-fields">
            <div className="data-card">
              <HardDrive size={22} />
              <div>
                <strong>对话存储在本机</strong>
                <p>原始消息、代码选区和运行事件保存在 SQLite；上下文压缩后仍可找回原文。</p>
              </div>
            </div>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={settings.auto_memory}
                onChange={(e) => setSettings({ ...settings, auto_memory: e.target.checked })}
              />
              允许 Agent 主动保存稳定的项目事实
            </label>
            <Button
              disabled={busy}
              onClick={() =>
                void perform(async () => {
                  const response = await fetch('/api/backup', { method: 'POST' });
                  if (!response.ok) throw new Error('备份失败');
                  const blob = await response.blob();
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `trunk-agent-${new Date().toISOString().slice(0, 10)}.zip`;
                  link.click();
                  setTimeout(() => URL.revokeObjectURL(url), 1000);
                  setFeedback('备份已导出（不包含 API 密钥）');
                })
              }
            >
              <Download size={14} />
              导出本地备份
            </Button>
            <p className="muted">
              包含对话、检查点、长期记忆和压缩档案。恢复时停止服务，将内容解压至 data 目录。
            </p>
          </div>
        )}
        <ErrorText error={error || saved.error} />
        {feedback && (
          <p className="success-text">
            <Check size={14} />
            {feedback}
          </p>
        )}
      </div>
      <div className="modal-footer">
        <span>密钥仅保存在本机配置文件</span>
        <Button className="primary" disabled={busy || !settings} onClick={() => void perform(save)}>
          {busy ? <LoaderCircle size={14} className="spin" /> : <Check size={14} />}保存配置
        </Button>
      </div>
    </Modal>
  );
}
