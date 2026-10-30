import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { normalizeSettings, settingsPayload, validateSettings } from '../lib/settingsDraft';
import type {
  McpProbeResult,
  McpServer,
  ModelCapabilities,
  Settings,
} from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';
import { useUnsavedGuard } from '../../../shared/hooks/useUnsavedGuard';

export function useSettingsDraft(open: boolean, onClose: () => void, advancedDirty = false) {
  const cache = useQueryClient();
  const saved = useQuery({
    queryKey: ['settings'],
    queryFn: () => api<Settings>('/settings'),
    enabled: open,
  });
  const [draft, setDraft] = useState<Settings>();
  const [baseline, setBaseline] = useState('');
  const [clearKeys, setClearKeys] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<unknown>();
  const [probes, setProbes] = useState<
    Record<string, { signature: string; result: ModelCapabilities }>
  >({});
  const [mcpProbes, setMcpProbes] = useState<
    Record<string, { signature: string; result: McpProbeResult }>
  >({});
  const dirty = !!draft && (JSON.stringify(draft) !== baseline || clearKeys.length > 0);
  const guard = useUnsavedGuard(dirty, busy, advancedDirty);
  function reset(settings: Settings) {
    const fresh = normalizeSettings(settings);
    setDraft(fresh);
    setBaseline(JSON.stringify(fresh));
    setClearKeys([]);
    setError(undefined);
    setProbes({});
    setMcpProbes({});
  }
  useEffect(() => {
    if (
      open &&
      saved.data &&
      (!draft || !dirty) &&
      JSON.stringify(normalizeSettings(saved.data)) !== baseline
    )
      reset(saved.data);
  }, [open, saved.data, draft, dirty, baseline]);
  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    setFeedback('');
    try {
      await action();
    } catch (reason) {
      setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  async function save() {
    if (!draft) return;
    const invalid = validateSettings(draft);
    if (invalid.length) throw new Error(invalid.join('；'));
    const response = await api<Settings>('/settings', {
      method: 'PUT',
      body: jsonBody({
        settings: settingsPayload(draft),
        version: draft.version,
        clear_profile_keys: clearKeys,
      }),
    });
    cache.setQueryData(['settings'], response);
    const verifiedMcp: typeof mcpProbes = {};
    for (const server of response.mcp_servers) {
      const source = draft.mcp_servers.find((row) => row.id === server.id);
      const tested = mcpProbes[server.id];
      if (tested && tested.signature === JSON.stringify(source))
        verifiedMcp[server.id] = { signature: JSON.stringify(server), result: tested.result };
    }
    reset(response);
    // 保存后凭据变为掩码，已检测且未再编辑的服务仍保留本次工具列表。
    setMcpProbes(verifiedMcp);
    guard.cancel();
    setFeedback('配置已保存');
    toast('配置已保存');
  }
  async function probeModel(profileId: string) {
    if (!draft) return;
    const profile = draft.model_profiles.find((row) => row.id === profileId)!;
    const result = await api<ModelCapabilities>('/settings/probe', {
      method: 'POST',
      body: jsonBody({
        settings: settingsPayload(draft),
        profile_id: profileId,
        version: draft.version,
        clear_profile_keys: clearKeys,
      }),
    });
    const signature = JSON.stringify(profile.config) + String(clearKeys.includes(profileId));
    setProbes((rows) => ({ ...rows, [profileId]: { signature, result } }));
    setFeedback(
      result.ok ? '四项能力检测通过，配置仍需点击保存。' : '检测已完成，请查看未通过的项目。',
    );
  }
  async function probeMcp(server: McpServer) {
    const result = await api<McpProbeResult>(`/mcp/${server.id}/probe`, {
      method: 'POST',
      body: jsonBody({ server }),
    });
    setMcpProbes((rows) => ({
      ...rows,
      [server.id]: { signature: JSON.stringify(server), result },
    }));
    setFeedback(`${server.name} 已连接 · ${result.tools.length} 个工具`);
  }
  function close() {
    setDraft(undefined);
    setBaseline('');
    setClearKeys([]);
    setFeedback('');
    setError(undefined);
    guard.cancel();
    onClose();
  }
  return {
    saved,
    draft,
    setDraft: (settings: Settings) => {
      setDraft(settings);
      setFeedback('');
    },
    dirty,
    busy,
    feedback,
    setFeedback,
    error,
    clearKeys,
    setClearKeys,
    probes,
    mcpProbes,
    guard,
    errors: draft ? validateSettings(draft) : [],
    perform,
    save,
    probeModel,
    probeMcp,
    close: () => guard.request(close),
    navigate: (action: () => void) =>
      guard.request(() => {
        close();
        action();
      }),
    reload: () =>
      guard.request(() => {
        void perform(async () => {
          const result = await saved.refetch();
          if (result.error) throw result.error;
          if (result.data) reset(result.data);
        });
      }),
  };
}
