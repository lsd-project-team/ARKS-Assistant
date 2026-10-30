const rows = [
  ['中心 / 高度示教', 'DoneAction 返回后保存吸嘴', '高度外层仍可能设可用并返回 OK'],
  ['吸嘴 PR 重教', '点完成后保存吸嘴', '缺模板或定位失败早退后仍会调用保存'],
  ['吸嘴自动校准', '两次成功、去安全位后保存', '首次中心写入早于第二次结果'],
  ['顶针 PR 重教', '点完成后保存顶针配置', '保存调用不以 DoneAction 成功返回值门控'],
  ['单顶针自动', 'finally 先安全移动，再保存', 'Fail / Exception 也进入；安全移动抛出会阻断后续'],
  ['全部顶针旧接口', '收尾保存代码已注释', '不是当前一键成功与统一保存入口'],
  ['取片偏移', '累加后抛料、到安全位，再保存物料', '后续异常没有统一撤回已累加值'],
];

export function ToolCalibrationPersistence() {
  return (
    <div className="g0-example">
      <table>
        <caption>各入口的保存调用与返回边界</caption>
        <colgroup>
          <col style={{ width: '24%' }} />
          <col style={{ width: '31%' }} />
          <col style={{ width: '45%' }} />
        </colgroup>
        <thead>
          <tr>
            <th>入口</th>
            <th>保存时点</th>
            <th>需要分开的状态</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([entry, save, boundary]) => (
            <tr key={entry}>
              <th>{entry}</th>
              <td>{save}</td>
              <td>{boundary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
