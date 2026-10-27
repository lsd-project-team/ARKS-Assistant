const sourceRows = [
  ['S1胶水', '时间寿命', '工位已配置且胶水实体存在'],
  ['S2胶水', '时间寿命', '启用S2点胶且胶水实体存在'],
  ['助焊剂', '时间寿命', '配置刮胶盘；并入时间列表'],
  ['吸嘴', '次数寿命', '当前架按名查实体'],
  ['顶针', '次数寿命', '取当前顶针库各槽配置'],
  ['翻转工具', '次数对象', '取列表接口未接入这条扫描与窗口'],
  ['点胶头', '次数对象', '可编辑，未加入当前汇集列表'],
];

const resetRows = [
  ['次数清零', '当前数归零', '清已提醒；保留限值、Enable与冷却记忆'],
  ['时间清零', '开始改为此刻', '清已提醒；保留寿命、Enable与冷却记忆'],
  ['改开始时间', '写入输入时间', '清已提醒；保留报警时间与IsAlarmed'],
  ['改开关寿命', '仅写编辑字段', '处理器未重置已提醒或冷却状态'],
];

function ConsumableTable({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <div className="g0-example">
      <table>
        <caption>{caption}</caption>
        <colgroup>
          <col style={{ width: '28%' }} />
          <col style={{ width: '28%' }} />
          <col style={{ width: '44%' }} />
        </colgroup>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, type, scope]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>{type}</td>
              <td>{scope}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ConsumableSourceTable() {
  return (
    <ConsumableTable
      caption="耗材对象与当前汇集范围"
      headers={['对象', '模型', '接入条件与状态']}
      rows={sourceRows}
    />
  );
}

export function ConsumableResetTable() {
  return (
    <ConsumableTable
      caption="编辑与复位的实际字段变化"
      headers={['操作', '主要变化', '提醒与冷却边界']}
      rows={resetRows}
    />
  );
}
