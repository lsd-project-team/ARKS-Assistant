import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { useEffect, useRef } from 'react';

export const cn = (...values: ClassValue[]) => twMerge(clsx(values));
export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cn('button', className)} {...props} />;
}
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(value) => !value && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className={cn('modal-content', className)}>
          <div className="modal-heading">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>{description || title}</Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button className="icon-button" aria-label="关闭">
                <X size={18} />
              </Button>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function ErrorText({ error, reveal = false }: { error: unknown; reveal?: boolean }) {
  const alert = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!error || !reveal) return;
    // 长表单提交失败时，错误不能留在看不见的位置，让按钮看起来没有响应。
    alert.current?.scrollIntoView({ block: 'nearest' });
    alert.current?.focus({ preventScroll: true });
  }, [error, reveal]);
  return error ? (
    <div ref={alert} tabIndex={reveal ? -1 : undefined} className="error-text" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
