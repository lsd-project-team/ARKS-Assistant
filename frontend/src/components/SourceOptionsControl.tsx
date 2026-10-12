import { ChevronDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { SourceOptions } from '../types';
import { resolvedSources } from '../lib/sourceOptions';
import { usePopupPosition } from '../hooks/usePopupPosition';
import '../styles/source-options.css';

const choices = [
  ['use_deepwiki', 'DeepWiki', '查阅远端架构说明'],
  ['use_knowledge', '流程与功能资料', '检索项目文档、共享结论、流程和功能说明'],
  ['use_memory', '长期记忆', '带入相关记忆，并允许按设置保存记忆'],
] as const;

export function SourceOptionsControl({
  value,
  onChange,
  disabled = false,
  compact = true,
  legend = '本轮知识来源',
  description = '本地源码始终可读，选择要额外使用的资料。',
}: {
  value?: Partial<SourceOptions>;
  onChange: (value: SourceOptions) => void;
  disabled?: boolean;
  compact?: boolean;
  legend?: string;
  description?: string;
}) {
  const selected = resolvedSources(value);
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const position = usePopupPosition(open, popup, trigger);
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (
        !popup.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      trigger.current?.focus();
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);
  const count = Object.values(selected).filter(Boolean).length;
  const fields = (
    <fieldset className="source-options" disabled={disabled}>
      <legend>{legend}</legend>
      <p className="muted">{description}</p>
      {choices.map(([key, label, description]) => (
        <label key={key}>
          <input
            type="checkbox"
            checked={selected[key]}
            onChange={(event) => onChange({ ...selected, [key]: event.target.checked })}
          />
          <span>
            {label}
            <small>{description}</small>
          </span>
        </label>
      ))}
      <div className="source-options-presets">
        <button
          type="button"
          onClick={() => onChange({ use_deepwiki: false, use_knowledge: false, use_memory: false })}
        >
          仅本地源码
        </button>
        <button
          type="button"
          onClick={() => onChange({ use_deepwiki: true, use_knowledge: true, use_memory: true })}
        >
          使用全部资料
        </button>
      </div>
    </fieldset>
  );
  if (!compact) return fields;
  return (
    <div className="source-options-picker">
      <button
        ref={trigger}
        type="button"
        disabled={disabled}
        aria-expanded={open}
        aria-label="本轮知识来源"
        title="选择本轮使用的资料"
        onClick={() => setOpen(!open)}
      >
        {count === 0 ? '仅源码' : count === 3 ? '资料' : `资料 ${count}`}
        <ChevronDown size={12} />
      </button>
      {open &&
        createPortal(
          <div ref={popup} className="source-options-popup" style={position}>
            {fields}
          </div>,
          document.body,
        )}
    </div>
  );
}
