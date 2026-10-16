import { choices, flow, step } from './builders.ts';

export const waferBoxFlows = [
  flow(
    'wafer-box-slots',
    'Box：蛇形槽索引与下一颗候选',
    '盒式候选由槽网格和 CurrentIndex 决定，只接受状态为 Good 的槽。',
    ['ws-box-grid', 'ws-box-index', 'ws-box-next'],
    [
      step(
        'grid',
        '网格位置与蛇形编号',
        'AdapterSlotEntity 按行列创建槽：位置为 FirstPosition 减列步距乘列号、减行步距乘行号；偶数行从左到右编号，奇数行反向。配置为 null 时构造函数提前返回，不建立网格。AcupointEntity 的 SlotState 默认 None，创建槽不等于已经全部 Good。',
        ['ws-box-grid', 'ws-box-index', 'ws-box-slot-default'],
      ),
      step(
        'find',
        '按当前索引查槽，只保留 Good',
        'GetWaffleSlot 在网格转成的列表中找 Index==CurrentIndex。GetWaffleNextPositionInfo 对 Good 直接返回；其他状态都把 CurrentIndex 加一、调用保存，再重新查找。这个局部循环没有 StopSearch、Sleep 或重试次数限制。',
        ['ws-box-slot-get', 'ws-box-next'],
      ),
      step(
        'empty',
        '查不到槽则请求换料',
        '候选为 null 时 SearchDieBox 置原始换料标记、把料片槽设 Bad、调用保存，然后 false。这条提前返回没有经过后面的 StopSearch。有效候选的位置才进入定位。',
        ['ws-box-search-a'],
      ),
    ],
  ),
  choices(
    'wafer-box-search',
    'Box：双点、静态盒式与跳过重搜',
    '标准定位的三种实际路径不同，静态单点不会在这里移动晶圆台或调用视觉。',
    ['ws-box-search-a', 'ws-box-search-b', 'ws-box-search-c'],
    [
      step(
        'two',
        '双点分别取自同一槽位',
        '开启双点时 P1、P2 分别以原 currentDiePosition 减 DistanceP1/P2，移动并调用各自 PR。两次不跳过时平均角度；P1 或 P2 跳过则把 CurrentIndex 设为槽索引加一并保存。后续取晶中心方法使用两中心的平均位置。',
        ['ws-box-search-a', 'ws-box-search-b', 'ws-pick-center-a'],
      ),
      step(
        'static',
        '静态单点只设置取晶结果位置',
        'StaticWaffle 单点分支用槽位置加 RelativeDistanceMarkWithCenter 写 resultDieG0Pos，并用配置的 Z；没有在这个分支移动晶圆台或 AnalyseDie。后续仍调用 MoveDieToPickCenter，但其 Box/StaticWaffle 分支也不移动晶圆台。',
        ['ws-box-search-b', 'ws-pick-center-a'],
      ),
      step(
        'moving',
        '非静态单点定位，跳过后推进索引',
        '非静态盒式先移动到槽位置减 RelativeDistanceMarkWithCenter，再 AnalyseDie(PR1)。isSkip 时索引加一并保存；受支持分支处理后 StopSearch，再按 isSkip 决定继续查槽或进入取晶中心返回 true。MultipleSearch、未知定位模式和关闭位置搜索均抛异常。',
        ['ws-box-search-b', 'ws-box-search-c'],
      ),
    ],
  ),
  flow(
    'wafer-box-commit',
    'Box：取晶后标槽与设备参数保存',
    '槽状态、当前索引、参数保存和界面刷新按调用顺序执行；方法名 Async 不能证明后台写入。',
    ['ws-box-picked', 'ws-box-save', 'ws-device-save'],
    [
      step(
        'remember',
        '先保存本次槽，再更新已取状态',
        'RemeberWafflePickedDieInfo 将 currentWaffleSlot 记为 previousWaffleSlot。RefreshWafflePickedDieStatus 把它对应网格槽设 Bad、CurrentIndex 设为已取索引加一，然后保存并 RefreshMap。SetSlotState 的数组访问失败会转成“更新槽状态失败”的异常。',
        ['ws-box-picked', 'ws-box-slot-get', 'w-refresh-mode'],
      ),
      step(
        'ui',
        'AsyncSave 当前经同步 UI Invoke 调用',
        'AsyncSaveWaferSubDevicePara 调 MainForm.SendUiAction，在委托中执行设备参数 Save。主窗体将 SendUiAction 绑定到 PostAction，PostAction 使用 this.Invoke(action)。这条已核对的绑定没有创建 Task 或使用 BeginInvoke；不能把它写成已启动后台保存。',
        ['ws-box-save', 'w-form-ui'],
      ),
      step(
        'file',
        'Save 加锁后请求写 JSON 和备份',
        '设备参数 Save 在 lock 内先调用 SaveGenericObject，再调用 CopyFile 到目录名拼接 Baks 的目标，参数包含 true 和 50。没有在 Save 内建立回滚或后台任务；JSON helper 的底层实现尚未展开，不能据方法名承诺原子落盘或备份保留规则。',
        ['ws-device-save'],
      ),
    ],
  ),
];
