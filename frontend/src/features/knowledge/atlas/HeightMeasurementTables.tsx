const readingRows = [
  ['S1 共用测高', '状态 + G0 高度', '机械值换 G0；在线正常尾部保留四位'],
  ['S2 激光原值', '传感器读数', '单次 GetValue，尚未形成物料局部高度'],
  ['S2 InGo', 'G0 高度计算', '当前 G0 Z − 测高偏移 Z − 激光值'],
  ['焊头 TD / ForceSensor', '状态 + 机械 Z', '调用方再决定 G0 换算和结果门控'],
  ['独立压力工具', '机械 Z', '下降和微调后的轴真实位置'],
  ['物料生产测高', '整体 Z 增量', '各支路整理读数后作均值差，公式分别说明'],
  ['平面度结果', '本轮极差', '实际返回列表 Max − Min'],
];
const persistenceRows = [
  ['生产物料', '测高结果、坐标 Z、已测高标记', '当前方法更新内存；没有同处配置 Save'],
  ['产品点列示教', '点列与示教状态', '窗内 Save 先于点击处理中的新点列赋值'],
  ['固晶水平示教', '中心 XY 与预测 Z', '分别写水平配置并 Save'],
  ['S1/S2 平面度', '点列、预测 Z、S2 勾选项', '对应配置仓库 Save；结果表另行生成'],
  ['平面度结果', '当前批次结果表', '用户选择路径后导出 XLS'],
  ['多高度测量', '结果列与 TestList', '外层列表 Count > 100 时写固定目录 XLSX'],
  ['独立数据窗', '接收的测高记录', '已实例化并接入时，关闭询问 XLS 导出'],
];

function MeasurementTable({
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
          <col style={{ width: '30%' }} />
          <col style={{ width: '26%' }} />
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
              <th>{name}</th>
              <td>{value}</td>
              <td>{detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function HeightReadingTable() {
  return (
    <MeasurementTable
      caption="读数与高度结果的口径"
      headers={['入口', '返回或结果', '怎样理解']}
      rows={readingRows}
    />
  );
}
export function HeightPersistenceTable() {
  return (
    <MeasurementTable
      caption="测高结果与保存出口"
      headers={['路径', '对象变化', '保存与输出']}
      rows={persistenceRows}
    />
  );
}
