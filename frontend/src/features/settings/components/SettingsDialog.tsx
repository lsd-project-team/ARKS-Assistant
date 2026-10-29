import { useEffect, useState } from 'react';
import { BookOpen, Brain, Cable, Check, Cpu, HardDrive, LoaderCircle, Palette } from 'lucide-react';
import { useSettingsDraft } from '../hooks/useSettingsDraft';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { ModelSettingsPanel } from './ModelSettingsPanel';
import { McpSettingsPanel } from './McpSettingsPanel';
import { SettingsDataPanel } from './SettingsDataPanel';
import { UnsavedNotice } from '../../../shared/ui/UnsavedNotice';
import { ConfirmationNotice } from '../../../shared/ui/ConfirmationNotice';
import { AppearanceSettings } from './AppearanceSettings';
import { MemorySettingsPanel } from '../../memory/components/MemorySettingsPanel';
import { useMemoryDraft } from '../../memory/hooks/useMemoryDraft';
import { useSourcePreferences } from '../../chat/hooks/useSourcePreferences';
import { KnowledgeSourceSettings } from './KnowledgeSourceSettings';
import { useAuth } from '../../auth/AuthContext';
import { api } from '../../../app/api/client';

export function SettingsDialog({
  open,
  onClose,
  initialTab = 'model',
  embedded = false,
  allowedTabs,
  onDirtyChange,
}: {
  open: boolean;
  onClose: () => void;
  initialTab?: string;
  embedded?: boolean;
  allowedTabs?: string[];
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const canConfigure = useAuth().session?.user.role === 'admin';
  const startingTab = initialTab;
  const [tab, setTab] = useState(startingTab);
  const [advancedDirty, setAdvancedDirty] = useState(false);
  const [sourcePreview, setSourcePreview] = useState<{
    path: string;
    content?: string;
    error?: unknown;
  }>();
  const [mcpEditorVersion, setMcpEditorVersion] = useState(0);
  const controller = useSettingsDraft(open, onClose, advancedDirty);
  const memoryController = useMemoryDraft(open && tab === 'memory', closeSettings);
  const sourceController = useSourcePreferences(open && tab === 'sources');
  const configurationTab = tab === 'model' || tab === 'mcp' || tab === 'data';
  // 未应用的 JSON 也是草稿，切换标签页前要避免把它留在已卸载的编辑器里。
  const [pendingTab, setPendingTab] = useState<string>();
  useEffect(() => {
    if (open) setTab(startingTab);
    else {
      setAdvancedDirty(false);
      setPendingTab(undefined);
    }
  }, [open, startingTab]);
  const { draft, busy } = controller;
  useEffect(() => {
    onDirtyChange?.(
      controller.dirty || memoryController.dirty || sourceController.dirty || advancedDirty,
    );
  }, [
    controller.dirty,
    memoryController.dirty,
    sourceController.dirty,
    advancedDirty,
    onDirtyChange,
  ]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);
  function closeSettings() {
    if (advancedDirty) {
      setPendingTab('close');
      return;
    }
    sourceController.leave(controller.close);
  }
  const Container = embedded ? EmbeddedSettings : Modal;
  return (
    <Container
      open={open}
      onClose={memoryController.close}
      title="工作区设置"
      className="settings-dialog"
    >
      <div className="dialog-tabs">
        {[
          { id: 'appearance', title: '外观', icon: Palette },
          { id: 'model', title: '模型', icon: Cpu },
          { id: 'mcp', title: 'MCP', icon: Cable },
          { id: 'sources', title: '知识来源', icon: BookOpen },
          { id: 'memory', title: '长期记忆', icon: Brain },
          { id: 'data', title: '数据', icon: HardDrive },
        ]
          .filter((item) => !allowedTabs || allowedTabs.includes(item.id))
          .map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? 'selected' : ''}
              disabled={busy || memoryController.busy || sourceController.busy}
              onClick={() => {
                if (tab === item.id) return;
                memoryController.leave(() => {
                  sourceController.leave(() => {
                    if (advancedDirty) setPendingTab(item.id);
                    else setTab(item.id);
                  });
                });
              }}
            >
              <item.icon size={14} />
              {item.title}
            </button>
          ))}
      </div>
      <div className="dialog-body">
        {tab === 'appearance' && <AppearanceSettings />}
        {tab === 'sources' && <KnowledgeSourceSettings controller={sourceController} />}
        {tab === 'memory' && (
          <MemorySettingsPanel
            controller={memoryController}
            onNavigate={(action) => memoryController.leave(() => controller.navigate(action))}
            onOpenThread={
              embedded
                ? (id) => {
                    window.location.hash = `admin/questions/${id}`;
                  }
                : undefined
            }
            onOpenSource={
              embedded
                ? (path) => {
                    setSourcePreview({ path });
                    void api<{ content: string }>(`/file?path=${encodeURIComponent(path)}`)
                      .then((saved) =>
                        setSourcePreview((current) =>
                          current?.path === path ? { path, content: saved.content } : current,
                        ),
                      )
                      .catch((error) =>
                        setSourcePreview((current) =>
                          current?.path === path ? { path, error } : current,
                        ),
                      );
                  }
                : undefined
            }
          />
        )}
        {configurationTab && controller.saved.isPending && <p className="muted">正在读取设置…</p>}
        {configurationTab && draft && (
          <fieldset className="settings-content" disabled={busy || !canConfigure}>
            {tab === 'model' && (
              <ModelSettingsPanel
                settings={draft}
                onChange={controller.setDraft}
                clearKeys={controller.clearKeys}
                onClearKeys={controller.setClearKeys}
                probes={controller.probes}
                busy={busy}
                onProbe={(id) => void controller.perform(() => controller.probeModel(id))}
              />
            )}
            {tab === 'mcp' && (
              <McpSettingsPanel
                key={mcpEditorVersion}
                settings={draft}
                onChange={controller.setDraft}
                probes={controller.mcpProbes}
                busy={busy}
                onProbe={(server) => void controller.perform(() => controller.probeMcp(server))}
                onAdvancedDirty={(dirty) => {
                  setAdvancedDirty(dirty);
                  if (dirty) controller.setFeedback('');
                }}
              />
            )}
            {tab === 'data' && (
              <SettingsDataPanel
                settings={draft}
                onChange={controller.setDraft}
                busy={busy}
                perform={controller.perform}
              />
            )}
          </fieldset>
        )}
        {configurationTab && !!controller.errors.length && (
          <ul className="settings-validation" role="alert">
            {controller.errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        )}
        {tab !== 'memory' && tab !== 'sources' && (
          <ErrorText
            error={controller.error || controller.saved.error}
            reveal={!!controller.error}
          />
        )}
        {tab !== 'memory' && tab !== 'sources' && !!controller.error && (
          <Button disabled={busy} onClick={controller.reload}>
            读取最新设置
          </Button>
        )}
        {tab !== 'memory' && tab !== 'sources' && controller.feedback && (
          <p className="success-text">
            <Check size={14} />
            {controller.feedback}
          </p>
        )}
        <UnsavedNotice guard={controller.guard} />
        <UnsavedNotice guard={memoryController.guard} />
        <UnsavedNotice guard={sourceController.guard} />
        {pendingTab && (
          <ConfirmationNotice>
            <span>JSON 修改尚未应用到表单。</span>
            <Button onClick={() => setPendingTab(undefined)}>继续编辑 JSON</Button>
            <Button
              onClick={() => {
                const target = pendingTab;
                setPendingTab(undefined);
                setAdvancedDirty(false);
                setMcpEditorVersion((version) => version + 1);
                if (target === 'close') controller.close();
                else setTab(target);
              }}
            >
              放弃 JSON 修改
            </Button>
          </ConfirmationNotice>
        )}
      </div>
      <div className={tab === 'memory' ? 'modal-footer memory-footer' : 'modal-footer'}>
        <span>
          {!canConfigure && configurationTab
            ? '系统配置由管理员维护'
            : tab === 'appearance'
              ? ''
              : tab === 'sources'
                ? sourceController.dirty
                  ? '有未保存的知识来源修改'
                  : ''
                : tab === 'memory'
                  ? memoryController.dirty
                    ? '有未保存的记忆修改'
                    : ''
                  : controller.dirty || advancedDirty
                    ? '有未保存的修改'
                    : ''}
        </span>
        {tab === 'sources' && (
          <Button
            className="primary"
            disabled={sourceController.busy || !sourceController.draft}
            onClick={() => void sourceController.save()}
          >
            {sourceController.busy ? (
              <LoaderCircle size={14} className="spin" />
            ) : (
              <Check size={14} />
            )}
            保存知识来源
          </Button>
        )}
        {configurationTab && (
          <Button
            className="primary"
            disabled={
              !canConfigure || busy || !draft || !!controller.errors.length || advancedDirty
            }
            onClick={() => void controller.perform(controller.save)}
          >
            {busy ? <LoaderCircle size={14} className="spin" /> : <Check size={14} />}保存配置
          </Button>
        )}
      </div>
      {sourcePreview && (
        <Modal open title={sourcePreview.path} onClose={() => setSourcePreview(undefined)}>
          <div className="dialog-body">
            <ErrorText error={sourcePreview.error} />
            {sourcePreview.content === undefined && !sourcePreview.error ? (
              <p>正在读取当前源码…</p>
            ) : (
              <>
                <p className="muted">当前源码，仅供核对记忆依据。</p>
                <pre className="admin-reference-text">{sourcePreview.content}</pre>
              </>
            )}
          </div>
          <div className="modal-footer">
            <Button onClick={() => setSourcePreview(undefined)}>关闭</Button>
          </div>
        </Modal>
      )}
    </Container>
  );
}

function EmbeddedSettings({
  children,
}: {
  children?: import('react').ReactNode;
  [key: string]: unknown;
}) {
  return <section className="settings-dialog admin-settings-panel">{children}</section>;
}
