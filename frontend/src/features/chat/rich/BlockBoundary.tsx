import { Component, type ReactNode } from 'react';
import { CodeBlock } from '../../../shared/ui/markdown/CodeBlock';
import type { ContentBlock } from './types';

export class BlockBoundary extends Component<
  { block: ContentBlock; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidUpdate(previous: Readonly<{ block: ContentBlock; children: ReactNode }>) {
    if (this.state.failed && previous.block !== this.props.block) this.setState({ failed: false });
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <section className="rich-fallback">
        <p role="status">此内容块暂时无法显示，原始数据已保留。</p>
        <CodeBlock>
          <code>{JSON.stringify(this.props.block, null, 2)}</code>
        </CodeBlock>
      </section>
    );
  }
}
