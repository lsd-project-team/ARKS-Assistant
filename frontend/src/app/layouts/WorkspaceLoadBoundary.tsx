import { Component, type ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from '../../shared/ui/ui';

export class WorkspaceLoadBoundary extends Component<
  { children: ReactNode; kind: 'source' | 'knowledge' },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    // 更新后的旧页面可能引用已替换的动态模块；只隔离失败区域，保住导航和问答。
    const source = this.props.kind === 'source';
    return (
      <section
        className={`${source ? 'code-pane' : 'knowledge-workspace padded'} source-load-error`}
        role="alert"
      >
        <strong>{source ? '源码显示区' : '流程与功能资料'}暂时无法加载</strong>
        <p>页面可能已更新，或连接暂时中断。重新加载页面后再试，已保存的草稿会保留。</p>
        <Button onClick={() => window.location.reload()}>
          <RefreshCw size={14} />
          重新加载页面
        </Button>
      </section>
    );
  }
}
