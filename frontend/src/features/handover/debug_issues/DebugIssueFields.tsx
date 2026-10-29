import { text, type Payload } from '../shared/types';
import { debugIssueFields } from './debugIssues';

type Field = (typeof debugIssueFields)[number];

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
        const required =
          'required' in field ||
          (field.key === 'solution' &&
            payload.record_type === 'problem' &&
            payload.resolution_status === 'resolved');
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
                placeholder={'placeholder' in field ? field.placeholder : undefined}
                onChange={(event) => onChange(field.key, event.target.value)}
              />
            ) : (
              <textarea
                required={required}
                maxLength={30000}
                rows={3}
                value={text(payload[field.key])}
                placeholder={
                  field.key === 'problem'
                    ? '记录问题或经验，可把发生条件、处理经过和已知原因一并写在这里。'
                    : 'placeholder' in field
                      ? field.placeholder
                      : '可选'
                }
                onChange={(event) => onChange(field.key, event.target.value)}
              />
            )}
          </label>
        );
      })}
    </div>
  );
}
