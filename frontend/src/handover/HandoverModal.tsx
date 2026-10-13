import type { FormEventHandler, ReactNode } from 'react';
import { Modal } from '../components/ui';

export function HandoverModal({
  title,
  description,
  onClose,
  onSubmit,
  footer,
  children,
  className = '',
}: {
  title: string;
  description: string;
  onClose: () => void;
  onSubmit?: FormEventHandler<HTMLFormElement>;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const content = (
    <>
      <div className="handover-modal-body">{children}</div>
      {footer && <div className="handover-form-footer">{footer}</div>}
    </>
  );
  return (
    <Modal
      open
      title={title}
      description={description}
      onClose={onClose}
      className={`handover-modal ${className}`}
    >
      {onSubmit ? (
        <form className="handover-modal-layout" onSubmit={onSubmit}>
          {content}
        </form>
      ) : (
        content
      )}
    </Modal>
  );
}
