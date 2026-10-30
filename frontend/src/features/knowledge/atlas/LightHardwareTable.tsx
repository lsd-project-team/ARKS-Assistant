const rows = [
  ['点胶相机', '点胶三色点光-红／绿／蓝', '点胶三色环光-红／绿／蓝'],
  ['BOND 相机', '邦头三色点光-红／绿／蓝', '邦头三色环光-红／绿／蓝'],
  ['上视相机', '上视点光（同名共用）', '上视环光（同名共用）'],
  ['晶圆相机', '晶圆三色点光-红／绿／蓝', '下视环光（同名共用）'],
  ['BondZ 标定相机', '使用点胶点光', '使用点胶环光'],
];

export function LightHardwareTable() {
  return (
    <div className="g0-example">
      <table>
        <caption>相机与光源硬件对应</caption>
        <colgroup>
          <col style={{ width: '24%' }} />
          <col style={{ width: '38%' }} />
          <col style={{ width: '38%' }} />
        </colgroup>
        <thead>
          <tr>
            <th>相机</th>
            <th>点光</th>
            <th>环光</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([camera, spot, ring]) => (
            <tr key={camera}>
              <th>{camera}</th>
              <td>{spot}</td>
              <td>{ring}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
