import * as SelectPrimitive from '@radix-ui/react-select';
import { Children, isValidElement, type ReactNode } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from './ui';

type OptionProps = { value: string | number; children: ReactNode; disabled?: boolean };

export function Select({
  value,
  onValueChange,
  children,
  disabled,
  className,
  'aria-label': label,
}: {
  value: string | number;
  onValueChange: (value: string) => void;
  children: ReactNode;
  disabled?: boolean;
  className?: string;
  'aria-label': string;
}) {
  // 沿用各表单的选项定义，统一浮层定位、键盘导航和焦点恢复。
  const options = Children.toArray(children).filter(isValidElement<OptionProps>);
  return (
    <SelectPrimitive.Root value={String(value)} onValueChange={onValueChange} disabled={disabled}>
      <SelectPrimitive.Trigger className={cn('ui-select-trigger', className)} aria-label={label}>
        <span className="ui-select-value">
          <SelectPrimitive.Value />
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
                value={String(option.props.value)}
                disabled={option.props.disabled}
              >
                <SelectPrimitive.ItemText>{option.props.children}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator className="ui-select-indicator">
                  <Check size={14} />
                </SelectPrimitive.ItemIndicator>
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
