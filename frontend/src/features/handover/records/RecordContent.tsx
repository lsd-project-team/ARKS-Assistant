import { Button } from '../../../shared/ui/ui';
import { SourceContent } from '../materials/SourceContent';
import { fieldSections } from '../shared/fieldLayout';
import { localTime } from '../shared/format';
import type { Definitions, HandoverRecord, Payload } from '../shared/types';
import { ids, refs, text } from '../shared/types';
import { workStatusLabel } from '../tasks/workStatus';

export function RecordContent({
  row,
  records,
  definitions,
  onOpen,
  showConfirmation = true,
}: {
  row: HandoverRecord;
  records: HandoverRecord[];
  definitions: Definitions;
  onOpen: (id: string, version?: number) => void;
  showConfirmation?: boolean;
}) {
  if (row.kind === 'source') return <SourceContent row={row} />;
  const properties = definitions.schemas[row.kind]?.properties || {};
  const sections = fieldSections(
    row.kind,
    Object.keys(row.payload).filter((key) => definitions.fields[key] && key !== 'origin'),
    properties,
  ).sort((a, b) => Number(b.id === 'content') - Number(a.id === 'content'));
  function valueText(value: unknown, field?: string) {
    if (typeof value === 'number') return String(value);
    if (Array.isArray(value))
      return ids(value)
        .map((id) => records.find((item) => item.id === id)?.title || id)
        .join('、');
    const valueString = text(value);
    if (field && properties[field]?.enum) return definitions.values[valueString] || valueString;
    if (field === 'format')
      return (
        (
          { source: '源码文本', zip: '固定源码 ZIP', docx: 'Word 文档', pdf: 'PDF 文档' } as Record<
            string,
            string
          >
        )[valueString] || valueString
      );
    return (
      records.find((item) => item.id === valueString)?.title ||
      definitions.values[valueString] ||
      valueString
    );
  }
  return (
    <>
      {sections.map((section) => (
        <section className="handover-content-section" key={section.id}>
          <h3>{section.title}</h3>
          <dl className="handover-record-fields">
            {section.keys.map((key) => (
              <div key={key}>
                <dt>{definitions.fields[key]}</dt>
                <dd>
                  {key === 'work_status'
                    ? workStatusLabel(row, definitions.values)
                    : valueText(row.payload[key], key) || '未填写'}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      {Array.isArray(row.payload.steps) && (
        <section>
          <h3>接续步骤</h3>
          {(row.payload.steps as Payload[]).map((step, index) => (
            <article className="handover-step" key={index}>
              <h4>
                {index + 1}. {text(step.action)}
              </h4>
              {Object.entries({
                prerequisite: '前提',
                output: '输出',
                verification: '验证',
                stop: '停止条件',
                rollback: '回退',
                owner: '负责人',
              }).map(([key, label]) => (
                <p key={key}>
                  <strong>{label}：</strong>
                  {text(step[key]) || '未填写'}
                </p>
              ))}
            </article>
          ))}
        </section>
      )}
      <section className="handover-form-section">
        {row.kind === 'package' && (
          <>
            <h3>包内固定版本</h3>
            <div className="handover-actions">
              {refs(row.payload.records).map((item) => (
                <Button
                  key={`${item.record_id}:${item.version}`}
                  onClick={() => onOpen(item.record_id, item.version)}
                >
                  {records.find((record) => record.id === item.record_id)?.title || item.record_id}{' '}
                  · v{item.version}
                </Button>
              ))}
            </div>
          </>
        )}
        <h3>来源与固定版本</h3>
        {!refs(row.payload.evidence).length && <p className="handover-muted">尚未关联来源证据。</p>}
        {refs(row.payload.evidence).map((item, index) => (
          <div className="handover-evidence" key={index}>
            <Button onClick={() => onOpen(item.record_id, item.version)}>
              {records.find((row) => row.id === item.record_id)?.title || item.record_id} · v
              {item.version}
            </Button>
            <span>{item.locator || '未填写定位'}</span>
            {item.quote && <blockquote>{item.quote}</blockquote>}
          </div>
        ))}
      </section>
      {showConfirmation && row.confirmation?.actor && (
        <p className="handover-notice">
          {row.confirmation.decision === 'reject' ? '拒绝审核人' : '确认人'}：
          {row.confirmation.actor} · {row.confirmation.role} · {localTime(row.confirmation.time)}
          <br />
          {row.confirmation.opinion}
        </p>
      )}
    </>
  );
}
