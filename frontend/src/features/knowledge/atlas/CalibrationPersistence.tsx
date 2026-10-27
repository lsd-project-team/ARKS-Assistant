const rows = [
  ['点胶', '相机 VM 坐标保存与刷新', 'Halcon 拟合 → 探针测高 → 参数 Save'],
  ['Bond', 'BMC 测高结果立即保存设备参数', '采点 → VM 保存 → Halcon → 回中心复核'],
  ['上视', 'VM 保存后继续拟合与旋转采点', '标定参数 Save → 放回标定片 → 写结果'],
  ['晶圆', '晶圆相机 VM 保存与刷新', '回中心/右标记复核 → 参数 Save → 晶圆台普通坐标保存'],
  ['焊头偏移', 'Bond 普通坐标保存与刷新', '最终两角度复核 → 再取片 → true'],
  ['S2 主链', '子任务各自可能已有写入', '全链到末尾 → 参数 Save → 结果窗口'],
];

export function CalibrationPersistence() {
  return (
    <div className="g0-example">
      <table>
        <caption>保存调用与后续步骤</caption>
        <thead>
          <tr>
            <th>任务</th>
            <th>较早发生的写入</th>
            <th>之后仍有步骤</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([task, saved, later]) => (
            <tr key={task}>
              <th>{task}</th>
              <td>{saved}</td>
              <td>{later}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
