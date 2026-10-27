const rows = [
  ['普通真实扫描', '写实测 ScanAxis', '正常退出循环后保存；finally 刷新日志'],
  ['带补偿真实扫描', '写实测 ScanAxis', 'finally 刷新日志；没有同样的尾部域保存'],
  ['普通模拟扫描', '写随机偏差结果', '正常结束保存；无相同的尾部 finally'],
  ['带补偿模拟', '记录目标与估算结果', '无相同的 ScanAxis 写回和域保存'],
  ['导入扫描列表', '替换内存点列', '替换之前先保存旧域，之后未立即再保存'],
  ['区域编辑', '增删、排序内存区域', '域保存由对应 Save 入口另做'],
  ['旧二维映射', '累计误差列表', '每轮生成数据，再进入下载和激活调用'],
  ['独立 Bond 标定', '更新偏移表对象', '逐轮导出 Excel；域配置由保存按钮写入'],
];

export function GlobalCalibrationPersistence() {
  return (
    <div className="g0-example">
      <table>
        <caption>扫描、编辑与补偿的收尾时点</caption>
        <colgroup>
          <col style={{ width: '25%' }} />
          <col style={{ width: '30%' }} />
          <col style={{ width: '45%' }} />
        </colgroup>
        <thead>
          <tr>
            <th>路径</th>
            <th>对象变化</th>
            <th>保存与输出</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([path, change, persistence]) => (
            <tr key={path}>
              <th>{path}</th>
              <td>{change}</td>
              <td>{persistence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
