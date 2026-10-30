const rows = [
  ['XYZ / XYZT', '当前 Z ≥ 安全 Z', 'XY（含 T）→ 目标 Z'],
  ['XYZ / XYZT', '当前低，目标不低', '目标 Z → XY（含 T）'],
  ['XYZ / XYZT', '当前、目标都低', '安全 Z → XY（含 T）→ 目标 Z'],
  ['XY', '当前 Z ≥ 安全 Z', '直接 XY'],
  ['XY', '当前 Z < 安全 Z', '安全 Z → XY → 恢复原 Z'],
];

export function MotionOrdering() {
  return (
    <div className="g0-example">
      <table>
        <caption>不同维度的安全移动顺序；“含 T”只适用于 XYZT</caption>
        <thead>
          <tr>
            <th>入口</th>
            <th>高度条件</th>
            <th>调用顺序</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([mode, condition, order]) => (
            <tr key={`${mode}-${condition}`}>
              <th>{mode}</th>
              <td>{condition}</td>
              <td>{order}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
