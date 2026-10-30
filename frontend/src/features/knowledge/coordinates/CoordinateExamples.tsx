export function TransformFormula({ inverse = false }: { inverse?: boolean }) {
  return (
    <div className="g0-formula" aria-label={inverse ? '普通坐标逆变换公式' : '普通坐标正变换公式'}>
      <span className="g0-formula-label">
        {inverse ? '上层 → 本地' : '本地 → 上层'} · θ 为当前层的 Degree
      </span>
      {inverse ? (
        <>
          <code>u = X − ΔX，v = Y − ΔY</code>
          <code>x = u cos θ + v sin θ</code>
          <code>y = −u sin θ + v cos θ</code>
          <code>z = Z − ΔZ</code>
        </>
      ) : (
        <>
          <code>X = x cos θ − y sin θ + ΔX</code>
          <code>Y = x sin θ + y cos θ + ΔY</code>
          <code>Z = z + ΔZ</code>
        </>
      )}
    </div>
  );
}

export function NumericalExample() {
  return (
    <div className="g0-example" aria-label="普通坐标转换的假设数值例子">
      <table>
        <caption>旋转 90°，再平移；长度沿用同一假设单位</caption>
        <thead>
          <tr>
            <th>计算位置</th>
            <th>X</th>
            <th>Y</th>
            <th>Z</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>本地点</th>
            <td>10</td>
            <td>0</td>
            <td>2</td>
          </tr>
          <tr>
            <th>旋转后</th>
            <td>0</td>
            <td>10</td>
            <td>2</td>
          </tr>
          <tr>
            <th>加平移后 · G0</th>
            <td>100</td>
            <td>60</td>
            <td>5</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function ProductionPath({ bond = false }: { bond?: boolean }) {
  const items = bond
    ? ['焊点局部补偿', '沿产品链到 G0', '组合分支补偿', '转为 Bond 轴目标']
    : ['胶型局部偏移', '沿焊点链到 G0', '加入点胶补偿', '插补接口继续处理'];
  return (
    <ol className="g0-production-path" aria-label={bond ? '固晶目标形成路径' : '点胶目标形成路径'}>
      {items.map((item, index) => (
        <li key={item}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          {item}
        </li>
      ))}
    </ol>
  );
}

export function StorageMap() {
  return (
    <div className="g0-storage" aria-label="坐标参数、标定文件与内存对象的保存关系">
      <div>
        <b>坐标目录 JSON</b>
        <span>名称、父级名称、平移、角度、模式与采点</span>
      </div>
      <div>
        <b>标定文件 .iwcal</b>
        <span>相机像素到物理 XY 的转换关系</span>
      </div>
      <div>
        <b>内存中的对象</b>
        <span>父引用与转换工具按需重建，旧引用需单独核对</span>
      </div>
    </div>
  );
}
