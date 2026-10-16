import * as SelectPrimitive from '@radix-ui/react-select';
import { Children, isValidElement, useId, type ReactNode, type Ref } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from './ui';

type OptionProps = { value: string | number; children: ReactNode; disabled?: boolean };

export function Select({
  value,
  onValueChange,
  children,
  disabled,
  required,
  className,
  triggerRef,
  'aria-invalid': invalid,
  'aria-describedby': describedBy,
  'aria-label': label,
}: {
  value: string | number;
  onValueChange: (value: string) => void;
  children: ReactNode;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  triggerRef?: Ref<HTMLButtonElement>;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
  'aria-label': string;
}) {
  // 沿用各表单的选项定义，统一浮层定位、键盘导航和焦点恢复。
  const options = Children.toArray(children).filter(isValidElement<OptionProps>);
  const emptyChoice = useId();
  const emptyLabel = options.find((option) => String(option.props.value) === '')?.props.children;
  return (
    <SelectPrimitive.Root
      value={String(value)}
      onValueChange={(next) => onValueChange(next === emptyChoice ? '' : next)}
      disabled={disabled}
      required={required}
    >
      <SelectPrimitive.Trigger
        ref={triggerRef}
        className={cn('ui-select-trigger', className)}
        aria-label={label}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
      >
        <span className="ui-select-value">
          <SelectPrimitive.Value placeholder={emptyLabel || '请选择'} />
        </span>
        <SelectPrimitive.Icon>
          <ChevronDown size={14} />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className="ui-select-content"
          position="popper"
          sideOffset={6}
          align="start"
          collisionPadding={12}
        >
          <SelectPrimitive.ScrollUpButton className="ui-select-scroll">
            <ChevronUp size={14} />
          </SelectPrimitive.ScrollUpButton>
          <SelectPrimitive.Viewport className="ui-select-viewport">
            {options.map((option) => (
              <SelectPrimitive.Item
                className="ui-select-item"
                key={String(option.props.value)}
                value={String(option.props.value) || emptyChoice}
                data-empty-selected={
                  (String(value) === '' && String(option.props.value) === '') || undefined
                }
                {...(String(value) === '' && String(option.props.value) === ''
                  ? { 'aria-selected': true }
                  : {})}
                disabled={option.props.disabled}
              >
                <SelectPrimitive.ItemText>{option.props.children}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator className="ui-select-indicator">
                  <Check size={14} />
                </SelectPrimitive.ItemIndicator>
                {/* 空值仍交给原生表单校验，浮层用独立标识表示“全部 / 未选择”。 */}
                {String(value) === '' && String(option.props.value) === '' && (
                  <span className="ui-select-indicator">
                    <Check size={14} />
                  </span>
                )}
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
          <SelectPrimitive.ScrollDownButton className="ui-select-scroll">
            <ChevronDown size={14} />
          </SelectPrimitive.ScrollDownButton>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}
