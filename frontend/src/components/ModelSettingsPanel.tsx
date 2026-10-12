import { useState } from 'react';
import { Check, Plus, Trash2, Cable } from 'lucide-react';
import type { ModelCapabilities, ModelSettings, Settings } from '../types';
import { emptyModel } from '../lib/settingsDraft';
import { Button } from './ui';
import { Select } from './Select';
import { AnalysisSettingsPanel } from './AnalysisSettingsPanel';

export function ModelSettingsPanel({
  settings,
  onChange,
  clearKeys,
  onClearKeys,
  probes,
  busy,
  onProbe,
}: {
  settings: Settings;
  onChange: (settings: Settings) => void;
  clearKeys: string[];
  onClearKeys: (keys: string[]) => void;
  probes: Record<string, { signature: string; result: ModelCapabilities }>;
  busy: boolean;
  onProbe: (id: string) => void;
}) {
  const [chosen, setChosen] = useState(settings.active_profile_id);
  const profile =
    settings.model_profiles.find((row) => row.id === chosen) || settings.model_profiles[0];
  const model = profile.config;
  const clearing = clearKeys.includes(profile.id);
  const tested = probes[profile.id];
  const result =
    tested?.signature === JSON.stringify(model) + String(clearing)
      ? tested.result
      : !clearing
        ? profile.capabilities
        : undefined;
  function change<K extends keyof ModelSettings>(key: K, value: ModelSettings[K]) {
    onChange({
      ...settings,
      model_profiles: settings.model_profiles.map((row) =>
        row.id === profile.id
          ? { ...row, config: { ...row.config, [key]: value }, capabilities: undefined }
          : row,
      ),
    });
  }
  function remove() {
    const profiles = settings.model_profiles.filter((row) => row.id !== profile.id);
    onChange({
      ...settings,
      model_profiles: profiles,
      active_profile_id:
        settings.active_profile_id === profile.id ? profiles[0].id : settings.active_profile_id,
    });
    onClearKeys(clearKeys.filter((id) => id !== profile.id));
    setChosen(profiles[0].id);
  }
  return (
    <div className="model-settings-panel">
      <div className="profile-toolbar">
        <label>
          模型配置
          <Select
            aria-label="编辑模型配置"
            value={profile.id}
            disabled={busy}
            onValueChange={setChosen}
          >
            {settings.model_profiles.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
                {settings.active_profile_id === row.id ? ' · 当前' : ''}
              </option>
            ))}
          </Select>
        </label>
        <Button
          disabled={busy || settings.model_profiles.length >= 20}
          onClick={() => {
            const id = `model_${crypto.randomUUID().slice(0, 8)}`;
            onChange({
              ...settings,
              model_profiles: [
                ...settings.model_profiles,
                { id, name: '新模型配置', config: emptyModel() },
              ],
            });
            setChosen(id);
          }}
        >
          <Plus size={14} />
          新增
        </Button>
        <Button
          aria-label="删除模型配置"
          disabled={busy || settings.model_profiles.length === 1}
          onClick={remove}
        >
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="profile-current">
        <span>
          {settings.active_profile_id === profile.id
            ? '当前对话模型配置'
            : '此配置尚未设为当前模型'}
        </span>
        {settings.active_profile_id !== profile.id && (
          <Button
            disabled={busy}
            onClick={() => onChange({ ...settings, active_profile_id: profile.id })}
          >
            <Check size={13} />
            设为当前模型
          </Button>
        )}
      </div>
      <div className="settings-fields">
        <label>
          配置名称
          <input
            maxLength={80}
            value={profile.name}
            onChange={(event) =>
              onChange({
                ...settings,
                model_profiles: settings.model_profiles.map((row) =>
                  row.id === profile.id ? { ...row, name: event.target.value } : row,
                ),
              })
            }
          />
        </label>
        <label>
          接口协议
          <Select
            aria-label="接口协议"
            disabled={busy}
            value={model.protocol}
            onValueChange={(value) => change('protocol', value as ModelSettings['protocol'])}
          >
            <option value="openai">OpenAI Chat Completions</option>
            <option value="anthropic">Anthropic Messages</option>
          </Select>
        </label>
        <label>
          接口地址
          <input
            value={model.base_url}
            onChange={(event) => change('base_url', event.target.value)}
            placeholder="https://example.com/v1"
          />
        </label>
        <label>
          模型名称
          <input value={model.model} onChange={(event) => change('model', event.target.value)} />
        </label>
        <label>
          API 密钥
          <input
            type="password"
            autoComplete="new-password"
            value={model.api_key}
            disabled={clearing}
            onChange={(event) => change('api_key', event.target.value)}
            placeholder={model.has_api_key ? '已保存 · 留空保留此配置的密钥' : '输入密钥'}
          />
        </label>
        {model.has_api_key && (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={clearing}
              onChange={(event) =>
                onClearKeys(
                  event.target.checked
                    ? [...clearKeys, profile.id]
                    : clearKeys.filter((id) => id !== profile.id),
                )
              }
            />
            清空此配置已保存的密钥
          </label>
        )}
        <div className="field-pair">
          {(
            [
              { key: 'context_tokens', label: '上下文容量', min: 2048, max: 2000000 },
              { key: 'output_tokens', label: '最大回复 token', min: 256, max: 65536 },
            ] as const
          ).map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                type="number"
                min={field.min}
                max={field.max}
                value={model[field.key]}
                onChange={(event) => change(field.key, Number(event.target.value))}
              />
            </label>
          ))}
        </div>
        <div className="field-pair">
          <label>
            温度
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={model.temperature}
              onChange={(event) => change('temperature', Number(event.target.value))}
            />
          </label>
          <label>
            超时（秒）
            <input
              type="number"
              min={10}
              max={600}
              value={model.timeout_seconds}
              onChange={(event) => change('timeout_seconds', Number(event.target.value))}
            />
          </label>
        </div>
        <label>
          压缩模型（可选）
          <input
            value={model.summary_model}
            onChange={(event) => change('summary_model', event.target.value)}
            placeholder="留空使用对话模型"
          />
        </label>
        <Button disabled={busy} onClick={() => onProbe(profile.id)}>
          <Cable size={14} />
          {busy ? '正在检测…' : '检测当前配置'}
        </Button>
        <p className="muted">
          检测普通回复、流式、工具往返和压缩模型，最多发送 5
          次短请求。上下文容量是配置值，不是实测窗口上限。
        </p>
        {result && (
          <div className="capability-results">
            <small>检测于 {new Date(result.checked_at).toLocaleString('zh-CN')}</small>
            {result.checks.map((check) => (
              <div key={check.id} className={check.status}>
                <span>
                  {check.label}
                  <small>
                    {check.status === 'passed'
                      ? '通过'
                      : check.status === 'failed'
                        ? '未通过'
                        : '未检测'}
                  </small>
                </span>
                <p>{check.detail}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <AnalysisSettingsPanel settings={settings} onChange={onChange} />
    </div>
  );
}
