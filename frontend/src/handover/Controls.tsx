import { useId, useRef, useState } from 'react';
import { Select } from '../components/Select';
import './controls.css';

export interface Choice {
  value: string;
  label: string;
  disabled?: boolean;
}

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
      <Select
        value={value}
        onValueChange={(next) => {
          setInvalid(false);
          onValueChange(next);
        }}
        required={required}
        disabled={disabled}
        triggerRef={trigger}
        className="handover-select-trigger"
        aria-label={label}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? errorId : undefined}
      >
        {choices.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </Select>
      {invalid && (
        <span className="handover-select-error" id={errorId}>
          请选择{label}
        </span>
      )}
    </div>
  );
}
