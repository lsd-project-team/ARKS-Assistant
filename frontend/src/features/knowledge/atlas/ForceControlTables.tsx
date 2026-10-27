const readingRows = [
  ['原始寄存器', 'int 数组', '按地址和数量读取；此层未换算为力'],
  ['GT 焊头高层', 'ADC / 32767 × 量程', '保留 6 位后乘 1000'],
  ['GT 平台高层', 'ADC × 平台量程', '保留 6 位后乘 100；未先除 32767'],
  ['GT 当前值', '当前静态通道的归一化 ADC', '乘量程并保留 8 位，再乘 1000；bool 不即时切通道'],
  ['独立 LVDT', 'LVDT 通道归一化 ADC', '按 LVDT 量程换算；不同于传感器直接 PDO 读取'],
  ['生产末次力', '当前值 − 运行时初值', '再按最近角度样本逆换算；仅力模式且非 ETEL 写入'],
  ['检验平台净力', '平台当前值 − 本轮基线', '固定目标的重复检验据此求极差'],
];

const persistenceRows = [
  ['通讯配置', '端口、站号、地址等', '在线连接前 Save；与连接是否成功分开'],
  ['标定参数', '模式、范围、间距和延时', '启动任务前保存 ForceConfig'],
  ['标定点示教', 'G0 标定位置', 'TD 测高成功后保存设备参数'],
  ['角度初值刷新', '当前内存字典', '单独刷新按钮未在同处 Save'],
  ['大小力样本', '角度表、初值字典、耗时', '到达共用 Save 尾部才保存标定数据'],
  ['范围和时间', '力范围、完成时间和配置', '共用 Save 中分别保存；不是跨文件事务'],
  ['实时曲线', '独立后台缓存', '手动或超过 5000 条时发起 XLSX 导出'],
  ['检验与生产', '列表或末次取贴力', '检验手动导出；生产文件受独立开关和载具门控'],
];

function ForceTable({
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
          <col style={{ width: '28%' }} />
          <col style={{ width: '42%' }} />
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

export function ForceReadingTable() {
  return (
    <ForceTable
      caption="原始读数与最终力值的口径"
      headers={['入口', '数据口径', '换算或适用范围']}
      rows={readingRows}
    />
  );
}

export function ForcePersistenceTable() {
  return (
    <ForceTable
      caption="力控数据的保存出口"
      headers={['对象', '保存内容', '触发与边界']}
      rows={persistenceRows}
    />
  );
}
