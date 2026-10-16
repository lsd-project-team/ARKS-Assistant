import { createContext, useContext, type ReactNode, type RefCallback } from 'react';
import { createPortal } from 'react-dom';
import { AccountMenu } from '../auth/AccountMenu';

export const WorkspaceHeadingTarget = createContext<HTMLDivElement | null>(null);

export function WorkspaceHeader({ headingRef }: { headingRef: RefCallback<HTMLDivElement> }) {
  return (
    <header className="workspace-topbar" aria-label="页面与账号">
      <div className="workspace-heading-slot" ref={headingRef} />
      <AccountMenu />
    </header>
  );
}

export function WorkspaceHeading({
  children,
  className,
  active = true,
}: {
  children: ReactNode;
  className: string;
  active?: boolean;
}) {
  const target = useContext(WorkspaceHeadingTarget);
  // 页面仍负责自己的标题和操作，共用顶栏让账号位置不受源码分栏影响。
  if (!active) return null;
  const heading = <div className={className}>{children}</div>;
  return target ? createPortal(heading, target) : heading;
}
