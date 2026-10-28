import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap } from 'lucide-react';
import { Select } from '../../../shared/ui/Select';
import type { ModelPreference } from '../../../shared/types/api';
import { api, jsonBody } from '../../../app/api/client';
import { toast } from '../../../shared/utils/toasts';

export function ModelPicker({ preference, busy }: { preference: ModelPreference; busy: boolean }) {
  const cache = useQueryClient();
  const current = preference;
  const change = useMutation({
    mutationFn: (id: string) =>
      api<ModelPreference>('/model-preference', {
        method: 'PUT',
        body: jsonBody({ profile_id: id }),
      }),
    onSuccess: (result) => {
      cache.setQueryData(['model-preference'], result);
      void cache.invalidateQueries({ queryKey: ['context'] });
      toast(busy ? '模型已切换，下一轮使用新配置' : '模型已切换');
    },
    onError: (error) => {
      void cache.invalidateQueries({ queryKey: ['model-preference'] });
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
            {profile.model || profile.name}
            {current.model_profiles.length > 1 ? ` · ${profile.name}` : ''}
          </option>
        ))}
      </Select>
    </label>
  );
}
