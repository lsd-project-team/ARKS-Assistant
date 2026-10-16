import * as Dialog from '@radix-ui/react-dialog';
import { useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import type { Choice } from './Controls';

function useMenuPosition(open: boolean, trigger: RefObject<HTMLButtonElement | null>) {
  const [position, setPosition] = useState<CSSProperties>();
  useLayoutEffect(() => {
    if (!open) return;
    function place() {
      const anchor = trigger.current?.getBoundingClientRect();
      if (!anchor) return;
      const below = innerHeight - anchor.bottom - 18;
      const above = anchor.top - 18;
      const flip = below < 240 && above > below;
      const height = Math.min(360, Math.max(0, flip ? above : below));
      const width = Math.min(Math.max(anchor.width, 300), innerWidth - 24);
      setPosition({
        width,
        left: Math.max(12, Math.min(anchor.left, innerWidth - width - 12)),
        top: flip ? undefined : anchor.bottom + 6,
        bottom: flip ? innerHeight - anchor.top + 6 : undefined,
        maxHeight: height,
      });
    }
    // 多选浮层也跟随表单滚动，避免长弹框中与触发按钮错位。
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open, trigger]);
  return position;
}

export function HandoverMultiSelect({
  value,
  onValueChange,
  options,
  label,
}: {
  value: string[];
  onValueChange: (value: string[]) => void;
  options: Choice[];
  label: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const trigger = useRef<HTMLButtonElement>(null);
  const position = useMenuPosition(open, trigger);
  const choices: Choice[] = [
    ...options,
    ...value
      .filter((id) => !options.some((option) => option.value === id))
      .map((id) => ({ value: id, label: `已关联记录（当前不可选）：${id}` })),
  ];
  const selected = choices.filter((option) => value.includes(option.value));
  const filtered = choices.filter((option) =>
    option.label.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setSearch('');
      }}
      modal={false}
    >
      <Dialog.Trigger asChild>
        <button
          ref={trigger}
          type="button"
          className="ui-select-trigger handover-select-trigger"
          aria-label={label}
        >
          <span className="ui-select-value">
            {selected.length ? selected.map((option) => option.label).join('、') : '未关联'}
          </span>
          {!!selected.length && <span className="handover-select-count">{selected.length}</span>}
          <ChevronDown size={14} />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Content
          className="handover-multi-content"
          style={position}
          aria-describedby={undefined}
        >
          <Dialog.Title className="handover-visually-hidden">选择{label}</Dialog.Title>
          <div className="handover-select-search">
            <Search size={14} aria-hidden="true" />
            <input
              aria-label={`搜索${label}`}
              placeholder="搜索记录"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <div className="handover-multi-options">
            {filtered.map((option) => (
              <label className="handover-multi-option" key={option.value}>
                <input
                  type="checkbox"
                  checked={value.includes(option.value)}
                  disabled={option.disabled}
                  onChange={(event) =>
                    onValueChange(
                      event.target.checked
                        ? [...value, option.value]
                        : value.filter((id) => id !== option.value),
                    )
                  }
                />
                <span>{option.label}</span>
              </label>
            ))}
            {!filtered.length && (
              <p className="handover-select-empty">
                {choices.length ? '没有匹配的记录' : '暂无可关联记录'}
              </p>
            )}
          </div>
          <div className="handover-select-footer">
            <span>已选 {value.length} 条</span>
            <Dialog.Close className="button" type="button">
              完成
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
