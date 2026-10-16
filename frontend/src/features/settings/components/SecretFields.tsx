import { Plus, X } from 'lucide-react';
import { useState } from 'react';

export function SecretFields({
  title,
  values,
  onChange,
}: {
  title: string;
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
}) {
  const [error, setError] = useState('');
  return (
    <fieldset className="secret-fields">
      <legend>{title}</legend>
      {Object.entries(values).map(([key, value], index) => (
        <div key={index}>
          <input
            aria-label={`${title}名称 ${index + 1}`}
            value={key}
            placeholder="名称"
            onChange={(event) => {
              if (event.target.value !== key && event.target.value in values) {
                setError('名称已存在，请使用不同名称');
                return;
              }
              setError('');
              const rows = Object.entries(values);
              rows[index] = [event.target.value, value];
              onChange(Object.fromEntries(rows));
            }}
          />
          <input
            type="password"
            autoComplete="new-password"
            aria-label={`${title}值 ${index + 1}`}
            value={value === '••••••' ? '' : value}
            placeholder={value === '••••••' ? '已保存 · 留空保留' : '值'}
            onChange={(event) => onChange({ ...values, [key]: event.target.value })}
          />
          <button
            aria-label={`移除${title} ${key || index + 1}`}
            onClick={() =>
              onChange(Object.fromEntries(Object.entries(values).filter(([name]) => name !== key)))
            }
          >
            <X size={13} />
          </button>
        </div>
      ))}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <button
        className="add-secret-field"
        onClick={() => {
          let name = '';
          while (name in values) name += '_';
          onChange({ ...values, [name]: '' });
        }}
      >
        <Plus size={12} />
        添加{title}
      </button>
    </fieldset>
  );
}
