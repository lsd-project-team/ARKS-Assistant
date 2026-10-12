import { Button } from '../components/ui';
import type { Definitions, Evidence, HandoverRecord, Kind, Payload, Property } from './types';
import { ids, refs, text } from './types';

const relations: Record<string, Kind> = {
  task_id: 'task',
  task_ids: 'task',
  dependencies: 'task',
  constraints: 'constraint',
  baseline_id: 'baseline',
  source_id: 'source',
  package_id: 'package',
};
const shortFields = new Set([
  'author',
  'interviewer',
  'date',
  'topic',
  'owner',
  'due',
  'location',
  'authority',
  'software_version',
  'commit',
  'firmware',
  'sdk',
  'device',
  'recipe',
  'calibration',
  'tester',
  'audience',
  'receiver',
  'trainer',
  'provider',
  'source_version',
]);
export function defaults(definitions: Definitions, kind: Kind): Payload {
  const result: Payload = {};
  for (const [key, property] of Object.entries(definitions.schemas[kind]?.properties || {})) {
    if (property.default !== undefined) result[key] = property.default;
    else if (property.type === 'array') result[key] = [];
  }
  return result;
}

export function Fields({
  kind,
  value,
  onChange,
  definitions,
  records,
  exclude = [],
}: {
  kind: Kind;
  value: Payload;
  onChange: (payload: Payload) => void;
  definitions: Definitions;
  records: HandoverRecord[];
  exclude?: string[];
}) {
  const properties = definitions.schemas[kind]?.properties || {};
  const set = (field: string, next: unknown) => onChange({ ...value, [field]: next });
  return (
    <div className="handover-fields">
      {Object.entries(properties)
        .filter(([key]) => !['origin', 'evidence', 'steps', ...exclude].includes(key))
        .map(([key, property]) => {
          const label = definitions.fields[key];
          if (!label) return null;
          const relation = relations[key];
          const options = records.filter(
            (row) =>
              row.kind === relation &&
              row.state !== 'archived' &&
              !(
                kind === 'baseline' &&
                key === 'source_id' &&
                !['source', 'zip', 'cs', 'cpp', 'c', 'h'].includes(text(row.payload.format))
              ),
          );
          const wide = !shortFields.has(key) && !property.enum && !relation;
          return (
            <label key={key} className={wide ? 'handover-field-wide' : ''}>
              <span>{label}</span>
              {relation ? (
                <select
                  aria-label={label}
                  multiple={property.type === 'array'}
                  value={property.type === 'array' ? ids(value[key]) : text(value[key])}
                  onChange={(event) =>
                    set(
                      key,
                      property.type === 'array'
                        ? Array.from(event.currentTarget.selectedOptions, (option) => option.value)
                        : event.target.value,
                    )
                  }
                >
                  {property.type !== 'array' && <option value="">未关联</option>}
                  {options.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.title} · v{row.version} · {definitions.states[row.state]}
                    </option>
                  ))}
                </select>
              ) : property.enum ? (
                <select
                  aria-label={label}
                  value={text(value[key]) || text(property.default)}
                  onChange={(event) => set(key, event.target.value)}
                >
                  {property.enum.map((option) => (
                    <option value={option} key={option}>
                      {definitions.values[option] || option}
                    </option>
                  ))}
                </select>
              ) : property.type === 'integer' ? (
                <input
                  aria-label={label}
                  type="number"
                  min={1}
                  value={Number(value[key] || 1)}
                  onChange={(event) => set(key, Number(event.target.value))}
                />
              ) : wide ? (
                <textarea
                  aria-label={label}
                  rows={key === 'transcript' ? 9 : 3}
                  maxLength={property.maxLength || 100000}
                  value={text(value[key])}
                  onChange={(event) => set(key, event.target.value)}
                />
              ) : (
                <input
                  aria-label={label}
                  value={text(value[key])}
                  maxLength={property.maxLength || 2000}
                  type={['date', 'due'].includes(key) ? 'date' : 'text'}
                  onChange={(event) => set(key, event.target.value)}
                />
              )}
              {property.type === 'array' && relation && <small>按住 Ctrl 或 Command 多选</small>}
            </label>
          );
        })}
    </div>
  );
}

const stepFields = {
  prerequisite: '前提',
  action: '执行动作',
  output: '输出',
  verification: '验证方式',
  stop: '停止条件',
  rollback: '回退方式',
  owner: '负责人',
};
export function PlanSteps({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: Payload[]) => void;
}) {
  const steps = (Array.isArray(value) ? value : []) as Payload[];
  return (
    <section className="handover-form-section">
      <h3>接续步骤</h3>
      <p className="handover-muted">每一步都应具备可执行的前提、验证方法、停止条件和回退方式。</p>
      {steps.map((step, index) => (
        <fieldset key={index}>
          <legend>步骤 {index + 1}</legend>
          <div className="handover-fields">
            {Object.entries(stepFields).map(([key, label]) => (
              <label key={key}>
                <span>{label}</span>
                <textarea
                  rows={2}
                  aria-label={label}
                  maxLength={2000}
                  value={text(step[key])}
                  onChange={(event) =>
                    onChange(
                      steps.map((item, position) =>
                        position === index ? { ...item, [key]: event.target.value } : item,
                      ),
                    )
                  }
                />
              </label>
            ))}
          </div>
          <div className="handover-actions">
            <Button
              type="button"
              disabled={!index}
              onClick={() => {
                const next = [...steps];
                [next[index - 1], next[index]] = [next[index], next[index - 1]];
                onChange(next);
              }}
            >
              上移
            </Button>
            <Button
              type="button"
              onClick={() => onChange(steps.filter((_, position) => position !== index))}
            >
              删除步骤
            </Button>
          </div>
        </fieldset>
      ))}
      <Button
        type="button"
        disabled={steps.length >= 100}
        onClick={() =>
          onChange([...steps, Object.fromEntries(Object.keys(stepFields).map((key) => [key, '']))])
        }
      >
        添加步骤
      </Button>
    </section>
  );
}

export function EvidenceFields({
  value,
  onChange,
  records,
}: {
  value: unknown;
  onChange: (value: Evidence[]) => void;
  records: HandoverRecord[];
}) {
  const evidence = refs(value);
  const available = records.filter(
    (row) => !['job', 'candidate', 'package'].includes(row.kind) && row.state !== 'archived',
  );
  const set = (index: number, changes: Partial<Evidence>) =>
    onChange(
      evidence.map((item, position) => (position === index ? { ...item, ...changes } : item)),
    );
  return (
    <section className="handover-form-section">
      <h3>来源证据</h3>
      <p className="handover-muted">
        引用固定版本。逐字引文会与原文核对；没有引文时可填写字段、页码、段落或行号。
      </p>
      {evidence.map((item, index) => (
        <fieldset key={index}>
          <legend>证据 {index + 1}</legend>
          <div className="handover-fields">
            <label>
              <span>来源记录</span>
              <select
                required
                aria-label="来源记录"
                value={item.record_id}
                onChange={(event) => {
                  const row = available.find((row) => row.id === event.target.value);
                  set(index, {
                    record_id: event.target.value,
                    version: row?.version || 1,
                    quote: '',
                  });
                }}
              >
                <option value="">选择来源</option>
                {available.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>来源版本</span>
              <input
                type="number"
                min={1}
                required
                value={item.version}
                onChange={(event) => set(index, { version: Number(event.target.value) })}
              />
            </label>
            <label>
              <span>定位</span>
              <input
                maxLength={2000}
                value={item.locator || ''}
                placeholder="例如：第 3 页、段落 8、行 20–35"
                onChange={(event) => set(index, { locator: event.target.value })}
              />
            </label>
            <label>
              <span>逐字引文</span>
              <textarea
                rows={3}
                aria-label="逐字引文"
                maxLength={2000}
                value={item.quote || ''}
                onChange={(event) => set(index, { quote: event.target.value })}
              />
            </label>
          </div>
          <Button
            type="button"
            onClick={() => onChange(evidence.filter((_, position) => position !== index))}
          >
            移除证据
          </Button>
        </fieldset>
      ))}
      <Button
        type="button"
        disabled={!available.length || evidence.length >= 100}
        onClick={() =>
          onChange([...evidence, { record_id: '', version: 1, locator: '', quote: '' }])
        }
      >
        添加来源证据
      </Button>
    </section>
  );
}
