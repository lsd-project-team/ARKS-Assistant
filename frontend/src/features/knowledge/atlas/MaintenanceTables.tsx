const entryRows = [
  ['面板预点胶', 'Mode 为 Off 拦截', '置手动标志再 DoWork；未消费返回值'],
  ['快捷预点胶', '先停机检查', 'Mode、Timing 均 Off 才拦截；按工位分派'],
  ['板上试胶', '头与板就绪', '先占单点；直接传出胶 true；未门控插补结果'],
  ['手动挤胶', '按输出切换', '开启时设示教压力；处理器没有同样停机检查'],
  ['换胶入口', '各入口不同', '面板直接开窗；快捷先停机、再按工位分派'],
  ['清板重置', '调用 InitPre', '重建点列、索引归零；该方法不执行物理擦板'],
];

const saveRows = [
  ['运行次数', '运行时字段', '开启分支尾部更新；不按取晶成功计数'],
  ['清嘴区域', 'BondProgram', '重建和取点时保存，早于实际清洁'],
  ['清洁台点', '设备与程序', '内部成功写两角高度/行列；外层仍保存设备'],
  ['抛料位置', '设备参数', '在线 Done 保存；离线 OK 不写新点'],
  ['板面与索引', '设备与程序', '板参数先保存；重建/取点另保存程序'],
  ['信号距离', '设备参数', '两次 Z 差在 (0, 1] 内才保存'],
  ['换胶与偏移', '设备、程序、仓库', '位置在 Next 中途保存；最后另存针偏移与状态'],
  ['清位置', '设备内存', '清六个位置字段；该方法自身未 Save'],
];

function MaintenanceTable({
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
          {rows.map(([name, target, detail]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>{target}</td>
              <td>{detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MaintenanceEntryTable() {
  return (
    <MaintenanceTable
      caption="维护入口的门控与结果消费"
      headers={['入口', '前置条件', '实际调用范围']}
      rows={entryRows}
    />
  );
}

export function MaintenanceSaveTable() {
  return (
    <MaintenanceTable
      caption="维护操作的保存与状态范围"
      headers={['对象', '写入位置', '保存时点与边界']}
      rows={saveRows}
    />
  );
}
