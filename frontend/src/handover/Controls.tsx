import * as Select from '@radix-ui/react-select';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useId, useRef, useState } from 'react';
import './controls.css';

export interface Choice {
  value: string;
  label: string;
  disabled?: boolean;
}

const emptyChoice = '__handover_empty_choice__';

export function HandoverSelect({
  value,
  onValueChange,
  options,
  label,
  required,
  disabled,
}: {
  value: string;
  onValueChange: (value: string) => void;
  options: Choice[];
  label: string;
  required?: boolean;
  disabled?: boolean;
}) {
  const placeholder = options.find((option) => !option.value)?.label || '请选择';
  const [invalid, setInvalid] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const errorId = useId();
  const choices =
    value && !options.some((option) => option.value === value)
      ? [...options, { value, label: `已关联记录（当前不可选）：${value}`, disabled: true }]
      : options;
  return (
    <div
      className="handover-select-control"
      onInvalidCapture={(event) => {
        // Radix 的隐藏 select 保留原生必填校验，错误和焦点展示在可见控件上。
        event.preventDefault();
        setInvalid(true);
        trigger.current?.focus();
      }}
    >
      <Select.Root
        value={value}
        onValueChange={(next) => {
          setInvalid(false);
          onValueChange(next === emptyChoice ? '' : next);
        }}
        required={required}
        disabled={disabled}
      >
        <Select.Trigger
          ref={trigger}
          className="ui-select-trigger handover-select-trigger"
          aria-label={label}
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? errorId : undefined}
        >
          <span className="ui-select-value">
            <Select.Value placeholder={placeholder} />
          </span>
          <Select.Icon>
            <ChevronDown size={14} />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content
            className="ui-select-content handover-select-content"
            position="popper"
            sideOffset={6}
            align="start"
            collisionPadding={12}
          >
            <Select.ScrollUpButton className="ui-select-scroll">
              <ChevronUp size={14} />
            </Select.ScrollUpButton>
            <Select.Viewport className="ui-select-viewport">
              {choices.map((option) => (
                <Select.Item
                  className="ui-select-item"
                  key={option.value}
                  value={option.value || emptyChoice}
                  disabled={option.disabled}
                >
                  <Select.ItemText>{option.label}</Select.ItemText>
                  <Select.ItemIndicator className="ui-select-indicator">
                    <Check size={14} />
                  </Select.ItemIndicator>
                  {!value && !option.value && (
                    <span className="ui-select-indicator">
                      <Check size={14} />
                    </span>
                  )}
                </Select.Item>
              ))}
            </Select.Viewport>
            <Select.ScrollDownButton className="ui-select-scroll">
              <ChevronDown size={14} />
            </Select.ScrollDownButton>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
      {invalid && (
        <span className="handover-select-error" id={errorId}>
          请选择{label}
        </span>
      )}
    </div>
  );
}
