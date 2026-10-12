import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap } from 'lucide-react';
import { Select } from './Select';
import type { Settings } from '../types';
import { api, jsonBody } from '../lib/api';
import { normalizeSettings, settingsPayload } from '../lib/settingsDraft';
import { toast } from '../lib/toasts';

export function ModelPicker({ settings, busy }: { settings: Settings; busy: boolean }) {
  const cache = useQueryClient();
  const current = normalizeSettings(settings);
  const change = useMutation({
    mutationFn: (id: string) =>
      api<Settings>('/settings', {
        method: 'PUT',
        body: jsonBody({
          settings: settingsPayload({ ...current, active_profile_id: id }),
          version: current.version,
        }),
      }),
    onSuccess: (result) => {
      cache.setQueryData(['settings'], result);
      toast(busy ? '模型已切换，下一轮使用新配置' : '模型已切换');
    },
    onError: (error) => {
      void cache.invalidateQueries({ queryKey: ['settings'] });
      toast(error instanceof Error ? error.message : '模型切换失败', undefined, 'error');
    },
  });
  return (
    <label
      className="model-picker"
      title={busy ? '切换后下一轮使用；当前回复保持原模型' : '选择对话模型'}
    >
      <Zap size={12} fill="currentColor" />
      <Select
        aria-label="当前模型配置"
        disabled={change.isPending}
        value={current.active_profile_id}
        onValueChange={(value) => change.mutate(value)}
      >
        {current.model_profiles.map((profile) => (
          <option value={profile.id} key={profile.id}>
            {profile.config.model || profile.name}
            {current.model_profiles.length > 1 ? ` · ${profile.name}` : ''}
          </option>
        ))}
      </Select>
    </label>
  );
}
