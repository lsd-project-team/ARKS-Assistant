import { choices, outcome, step } from './builders.ts';

// 预点胶是点胶节点的内层调用，不能画成普通配方消息的并列调度项。
export const s2AuxiliaryFlows = [
  choices(
    's2-dip-boundary',
    '蘸胶入口、空跑与漏晶',
    'DipFlux 在 try 前 WorkStart / Running；try 内先检查胶盘硬件，再检查 DryCycle。此 DoWork 没有统一 OffLine 提前返回，空跑辅助入口当前直接抛出“蘸胶空跑动作待验证”。',
    ['s2-dip-entry', 's2-dip-dry'],
    [
      step(
        'guard',
        '焊点、步骤与 DipMode 门控',
        'IsDoWork 排除 Disable、EnableInSystem1、不需要的 S2 步骤与 DipMode.Off；没有 EntityState.Process 门控。不要把这个判断改写成 DoWork 内部已有同样的检查。',
        ['s2-dip-guard'],
      ),
      step(
        'dry',
        'DryCycle 当前不是可用模拟路径',
        '缺胶盘配置会先抛异常；已配置且为 DryCycle 时进入辅助方法，该方法第一句就抛异常，后面的允许蘸胶等待和模拟位置代码不可沿此入口正常执行。外层 catch 准备返回 Exception，再 finally Stop / WorkStop。',
        ['s2-dip-entry', 's2-dip-dry', 's2-dip-final'],
      ),
      step(
        'wait',
        '普通分支等许可并准备位置',
        '取当前焊点后 Wait IsAllowDipFluxSignal，false 直接 Abort。成功后按胶盘负限位状态请求伸出，再把吸嘴高度、芯片厚度和距离模式 DipDistance 加到蘸胶 Z；安全位另加代码中的 5。这里不是先等单步许可的入口。',
        ['s2-dip-entry', 's2-dip-position'],
      ),
      step(
        'work',
        '移动与蘸胶失败原样返回',
        '先 JumpToSlideFluxer，再 System2Controller.DipFlux，任一非 Success 直接返回，成功才进入漏晶分支。当前 DoWork 正常结尾没有发被注释掉的 BondDipFluxFinishSignal，也没有 S2FinishedStep。',
        ['s2-dip-work', 's2-dip-final'],
      ),
      step(
        'leak',
        '漏晶：重测、退出、忽略或重取',
        '启用检测且漏晶时先去安全高度、增加真空报警数。Retry 只重测；Abort 返回；Ignore 继续；Cancel 抛料并增 Reject，重建 Pick 与 UpLook 两个消息，置 IsRepickComponent 后 Retry。这里未按精度配置裁掉 UpLook，也未把本次 Dip 加进该列表。',
        ['s2-dip-leak', 's2-dip-rework', 's2-rework-current'],
      ),
    ],
  ),
  choices(
    's2-pre-dispense',
    'S2 预点胶入口与触发条件',
    'S2DispenseActionNode 在单步等待和 WaitStart 后直接调用 S2PreDispenseActionNode.DoWork；非 Success 转成 Alarm。预点胶不在仓库普通 ActionNodes 列表里，不能画成同一层的配方类型选择。',
    ['s2-pre-caller', 's2-main-action-list'],
    [
      step(
        'gate',
        '先调用 IsDispense',
        '预点胶 WorkStart / Running 后进入 try；IsDispense 为 false 就 Success，finally 仍清 IsManual、Stop 和 WorkStop。未配置 S2 点胶先返回 false；手动且 Timing.Off 弹提示后 false，其他手动情况才 true。',
        ['s2-pre-entry', 's2-pre-manual-gate', 's2-pre-final'],
      ),
      step(
        'automatic',
        '自动首启与周期条件',
        '非手动时 Mode 与 Timing 同为 Off 先返回 false；之后 IsFirstDispense 为 true 才直接 true。Periodic 比较距离 LastDispenseTime 的毫秒数是否严格大于配置间隔，否则 false。此方法没有将 IsFirstDispense 自己清成 false。',
        ['s2-pre-auto-gate'],
      ),
      step(
        'work',
        '获取预点胶点位并执行',
        'GetEpoxy 返回 null 为 Abort；打印工具配置下图案缺吸嘴名抛异常，换嘴失败为 Abort。逐点调用 InterpolationApplication，DryCycle 传 isDrip=false，任一非 Success 转为 Alarm；空跑仍调用这个运动入口。',
        ['s2-pre-entry', 's2-pre-work'],
      ),
      step(
        'finish',
        '检测、手动定位与时间记录',
        '若查到胶后检测配置就调用 CheckEpoxyApplication；本层没有据其检查返回另设分支。手动时先清标记再移相机到最后点，随后更新 LastDispenseTime 并 Success；异常 catch 准备返回 Exception。内部胶检仍待展开，不能凭调用存在就写成质量验收通过。',
        ['s2-pre-final'],
        [
          outcome(
            '空点位列表的限制',
            '这里只查 lists == null，没有空列表保护；后续 Last() 或最后一项索引可能异常，finally 仍清手动标记。',
            's2-pre-entry',
            's2-pre-final',
          ),
        ],
      ),
    ],
  ),
];
