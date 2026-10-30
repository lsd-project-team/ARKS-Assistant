const statusRows = [
  ['工具实体', '按名查库', '定义几何、偏移和三项示教状态'],
  ['工具槽位', '名称与状态', '配置在哪里、记忆中在架还是在头'],
  ['当前工具', '设备当前名', '据此查实体；改名不自动同步全部槽位'],
  ['物理在位', '开关／真空', '本次检测结果；读取会开真空并等待'],
];

const persistenceRows = [
  ['当前工具名', '设备参数', 'SetCurrentNozzleName 立即保存'],
  ['槽位与状态', '工具架仓库', '取还嘴尾部、设置确认及部分人工刷新'],
  ['工具实体', '吸嘴仓库', '几何、编辑、新建和配方归属分别保存'],
  ['工具架选择', 'BondProgram', '工具架设置确认时保存'],
  ['位置与角度', '设备参数', '示教插值保存位置、角度、槽数及安全 Z'],
  ['ToolBank 坐标', '坐标目录', '首槽步骤中途保存；取消不统一回滚'],
];

function ToolBankTable({
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
          {rows.map(([name, value, detail]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>{value}</td>
              <td>{detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ToolBankStatusTable() {
  return (
    <ToolBankTable
      caption="四种状态的读取口径"
      headers={['对象', '读取内容', '含义与边界']}
      rows={statusRows}
    />
  );
}

export function ToolBankPersistenceTable() {
  return (
    <ToolBankTable
      caption="工具与换嘴结果的保存对象"
      headers={['对象', '保存位置', '触发时点与范围']}
      rows={persistenceRows}
    />
  );
}
