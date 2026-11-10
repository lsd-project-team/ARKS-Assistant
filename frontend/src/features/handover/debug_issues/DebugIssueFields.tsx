import { text, type Payload } from '../shared/types';
import { debugIssueFields, debugMetadataFields } from './debugIssues';

type Field = (typeof debugIssueFields)[number] | (typeof debugMetadataFields)[number];

export function DebugIssueFields({
  fields,
  payload,
  onChange,
}: {
  fields: readonly Field[];
  payload: Payload;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <div className="debug-issue-editor-fields">
      {fields.map((field) => {
        const required = 'required' in field;
        return (
          <label key={field.key} className={`debug-issue-field ${'short' in field ? 'short' : ''}`}>
            <span>
              {field.label}
              {required && <b> *</b>}
            </span>
            {'short' in field ? (
              <input
                maxLength={2000}
                value={text(payload[field.key])}
                placeholder={'placeholder' in field ? String(field.placeholder) : undefined}
                onChange={(event) => onChange(field.key, event.target.value)}
              />
            ) : (
              <textarea
                required={required}
                maxLength={field.key === 'answer' ? 100000 : 30000}
                rows={field.key === 'answer' ? 7 : 2}
                value={text(payload[field.key])}
                placeholder={'placeholder' in field ? field.placeholder : '可选'}
                onChange={(event) => onChange(field.key, event.target.value)}
              />
            )}
          </label>
        );
      })}
    </div>
  );
}
