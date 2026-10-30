import type { SourceGuide } from '../sourceGuides';
import { choices, outcome, step } from './builders.ts';

export const safeMotionGuide: SourceGuide = {
  id: 'safe-motion-source-review',
  topic: 'motion-safety',
  diagrams: ['safe-motion-process'],
  initialFlows: { 'motion-safety': 'sm-order', 'safe-motion-process': 'sm-order' },
  title: '建议阅读顺序',
  flows: [
    choices(
      'sm-targets',
      '目标与软限位',
      '先确认调用者传的是机械目标还是 G0 点，再看所选重载实际检查哪些轴。',
      ['sm-target-wrappers', 'sm-convert', 'sm-limits'],
      [
        step(
          'convert',
          '三维 G0 点先转机械目标',
          '三维 MoveToG0Pos 先用 Bond 坐标的一层逆变换，再进入安全 XYZ；CameraMoveToG0Pos 先减焊头到相机偏移。完整父链转换统一见 G0 专题，不把这层接口当作所有坐标类型的通用变换。',
          ['sm-target-wrappers', 'sm-convert'],
        ),
        step(
          'overloads',
          '标量与四维重载不同',
          '四维转换只变换 XYZ 并保留 T。双标量 MoveToG0Pos 分别用 (X,0,X) 与 (0,Y,0) 求分量，不能自动简化为三维点重载；位置参数的实际组合仍按该调用读取。',
          ['sm-target-wrappers', 'sm-convert'],
        ),
        step(
          'limits',
          '软限位检查的实际范围',
          '模块二维只查 XY，三维查 XYZ；四维 CheckSoftLimit 当前也只查 XYZ，没有 T。超限抛异常，不是返回 false；双标量 Y 的下限使用 GetSoftLimit，其他多取 AxisSetPara。',
          ['sm-limits'],
        ),
        step(
          'commands',
          '发命令与调用等待分开',
          '模块 XY、XYT、XYZT 通常先向各轴 SendAbsoluteMoveCommand，再调用 WaitAxesArrival。离线或 IsReady 不满足也可能直接 void return；Axis 和 MotionService 的内部结果不能由这个返回形式统一推定。',
          ['sm-module-xy', 'sm-module-xyzt', 'sm-module-others', 'sm-ready'],
        ),
      ],
    ),
    choices(
      'sm-height',
      '安全高度来源',
      '安全高度会随载具、工具、工位状态和区域变化，不是所有重载共用一个固定 Z。',
      ['sm-level-xyz', 'sm-level-xy', 'sm-level-xyzt', 'sm-level-current'],
      [
        step(
          'product',
          '载具、点胶气缸与吸嘴',
          '有载具时，以载具 G0 原点加产品 SafeHeight 为基础；S2 测高气缸打开且有点胶器时减焊头/点胶器 Z 差，否则加吸嘴测高偏移。无载具先取设备安全点，再转换成机械高度。',
          ['sm-level-xyz', 'sm-level-xyzt'],
        ),
        step(
          'regions',
          '非工作状态与静态区域',
          '带目标的重载在非工作状态可覆盖为设备安全 Z；有静态 Waffle 配置且当前或目标 Y 跨到对应区域时，再按避让位与吸嘴偏移提高安全高度。无参数重载只看当前区域，也没有同样的非工作覆盖。',
          ['sm-level-xyz', 'sm-level-xy', 'sm-level-current'],
        ),
        step(
          'checks',
          '最终高度复查并不一致',
          '二维、三维目标重载在覆盖和静态避让之后检查最终安全高度。四维重载只在有载具的早期位置检查，后续覆盖或提高未做同样的最终复查；不能把各重载概括为完全一样的保护。',
          ['sm-level-xyz', 'sm-level-xy', 'sm-level-xyzt'],
        ),
      ],
    ),
    choices(
      'sm-order',
      '二维三维四维',
      '安全移动先求安全高度、检查目标和单步，再按当前/目标 Z 选择动作顺序。',
      ['sm-xyz', 'sm-xyzt', 'sm-xy'],
      [
        step(
          'overview',
          'XYZ 的三种实际顺序',
          '当前不低于安全高度时，先 XY 后目标 Z；当前低而目标不低时，先目标 Z 后 XY；当前与目标都低时，先安全 Z、再 XY、最后目标 Z。XYZT 的水平动作组包含 T。',
          ['sm-xyz', 'sm-xyzt'],
        ),
        step(
          'table',
          'XY 还会恢复原来的高度',
          '二维 XY 方法在当前高度不足时抬到安全 Z，移动 XY 后恢复原 Z；三维、四维则以给定目标 Z 收尾或作为先行动作。下表只说明调用顺序，不能替代每个子调用的成功结果。',
          ['sm-xyz', 'sm-xyzt', 'sm-xy'],
        ),
        step(
          'return',
          'Z 返回失败没有统一阻断',
          '单步门控拒绝会直接退出当前方法；内部 MoveZAxis 也可能返回 Abort，但控制器没有逐次检查其结果，后续 XY 仍可能被调用。未匹配任何高度分支时会走异常出口，不能把所有输入都理解为正常移动。',
          ['sm-xyz', 'sm-xyzt', 'sm-z-command'],
        ),
      ],
    ),
    choices(
      'sm-regions',
      '生产区域切换',
      '场景方法先选普通绝对移动或插补，再消费本场景的过渡点与互锁。',
      [
        'sm-pick-dispatch',
        'sm-bond-dispatch',
        'sm-uplook-dispatch',
        'sm-ipt-dispatch',
        'sm-maintenance',
      ],
      [
        step(
          'pick',
          '取片位置与翻转互锁',
          '预取片先检查翻转台交接位或回零位。重新取片走普通安全 XYZT，其他按 AxisMoveMode 选择绝对或 Jump；绝对取片先等安全 Z，再等 XY 接近后发目标 Z，最后调用到位等待。',
          ['sm-pick-dispatch', 'sm-pick-absolute'],
        ),
        step(
          'bond',
          '固晶位置的普通与 Jump',
          '普通固晶先在需要时抬安全 Z，等 XY 接近再发目标 Z；两段局部等待各有 10 秒判断。Jump 根据当前 Z 是否低于抬升高度选择两段或三段，并使用本场景的速度与前瞻参数。',
          ['sm-bond-absolute', 'sm-bond-dispatch'],
        ),
        step(
          'uplook',
          '上视按来源区域分派',
          '上视入口区分静态 Waffle、翻转台、晶圆与刮胶盘。普通模式选择不同安全高度；插补模式进入各自 Jump。翻转且校正前蘸胶、两点校正的路径会先抬高、发完成信号，并等待胶盘缩回，超过 5 秒抛异常。',
          ['sm-uplook-dispatch'],
        ),
        step(
          'ipt',
          'IPT 使用专属过渡点',
          'IPT 按普通/插补、静态 Waffle/晶圆来源选择路径。晶圆到 IPT 的插补使用四段，清嘴台配置和左右 IPT 改变中间点及高度；不是直接把全部区域连成同一条直线。',
          ['sm-ipt-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'maintenance',
          '换嘴、安全位与拍照位',
          '换嘴入口先去换嘴安全 Z，再移动 XY，并各有离线/单步门控。普通安全位会先收回 S2 测高气缸；上视、取片、测高与避让位置各使用自己的参数或偏移来源。',
          ['sm-maintenance', 'sm-target-wrappers', 'sm-nozzle-height'],
        ),
      ],
    ),
    choices(
      'sm-geometry',
      '碰撞圆与规划工具',
      '运行中的圆限位与几何工具分开阅读，不由工具名称推定所有动作都经过完整避障规划。',
      ['sm-wafer-circle', 'sm-wafer-move', 'sm-path', 'sm-profile'],
      [
        step(
          'circle',
          '晶圆环限位检查目标 XY',
          '启用环限位时，比较目标到晶圆台中心的 XY 平方距离与半径平方；半径先转 long，边界相等通过。它只检查目标平面位置，不检查 Z，也不是对整条路径的全程避碰证明。',
          ['sm-wafer-circle'],
        ),
        step(
          'wafer',
          '晶圆移动先有其他副作用',
          '带搜索 G0 移动先关顶针台真空，再判断离线；特定搜索模式检查顶针准备高度。通过条件后转晶圆普通坐标，发 X/Y 指令并 WaitAxesArrival；离线返回也不等于此前没有任何调用。',
          ['sm-wafer-move'],
        ),
        step(
          'intersection',
          '安全区域交点的计算边界',
          'MotionPlan 工具按四点 XY 包围范围检查终点，依固定边顺序取首个交点。交点方法求直线交点后只检查起终线段的 X 范围，未完整检查两条线段的 X/Y 参数范围，不能当作通用精确避障求解。',
          ['sm-intersection', 'sm-path'],
        ),
        step(
          'tools',
          '半径、离散路径与距离参数',
          'GetRadius 取交点到终点 XY 距离与 Z 差绝对值的较小值；GetMoveLine 生成两组各 11 个点，零距离等退化输入未统一保护。距离参数方法只返回 Acc/Dec/Jerk，没有发令；当前直接调用检索只在速度实验定位到路径工具。',
          ['sm-path', 'sm-profile', 'sm-path-experiment'],
        ),
      ],
    ),
    choices(
      'sm-interpolation',
      '插补与驱动',
      '生产动作选择所属轴卡接口，ETEL 组与本地固高辅助方法各自有明确边界。',
      ['sm-groups', 'sm-pick-jump', 'sm-gg-setup', 'sm-gg-run', 'sm-gg-pick'],
      [
        step(
          'groups',
          '按轴集合组织插补',
          'GetBondIpolAxis 在 T 单独运动时只给 XYZ，否则给 XYZT；XY 集合只给 XY。GetXY/XYZ/XYZTIpolGroup 则明确转换 ETELAxis 并缓存 ETEL 组，不是自动适配任意驱动的接口。',
          ['sm-groups'],
        ),
        step(
          'production',
          '按首轴找到所属轴卡',
          'Pick、Bond、IPT 的 Jump 由首个驱动查所属 AxisCard，再调用该卡 MotionController.ContinueInterpolationMove。取片根据静态 Waffle、Bond 相机搜索和晶圆来源组成不同过渡段；T 单独运动在外部任务处理。',
          ['sm-pick-jump', 'sm-bond-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'gugao',
          '本地固高工具的组与指令流',
          'ContinueInterpolationMove 配 core=2、传入 list/group、轴号和 PulseEquivalent，设置平滑与前瞻，逐段写绝对直线及非末段 blending。DataEnd 循环没有本地统一超时；启动后监视组/指令流，超过 30 秒抛异常，finally 解组并禁用。',
          ['sm-gg-setup', 'sm-gg-run'],
          [
            outcome(
              '接口归属',
              '实际生产调用的是轴卡接口，不能只因同名就断定一定进入这个本地静态方法；部分 rtn 累加、部分覆盖，也不能称每条 API 都已即时独立通过。',
              'sm-pick-jump',
              'sm-gg-run',
            ),
          ],
        ),
        step(
          'pick-helper',
          '另一个辅助方法没有同样超时',
          'PickContinueInterpolationMove 的 core/list/group 都固定为 2，使用固定组约束和前瞻参数；数据结束及状态等待没有上述 30 秒检查，HighAccuracy 再逐轴 WaitInRealPosition。当前定位到的直接调用在速度实验，不能标为生产取片必经实现。',
          ['sm-gg-pick', 'sm-drive-experiment'],
        ),
      ],
    ),
    choices(
      'sm-completion',
      '等待、异常与停止',
      '发出指令、所属接口返回、等待完成与设备/任务全部停止分别确认。',
      ['sm-module-xy', 'sm-module-others', 'sm-pick-jump', 'stop-state', 'emergency-axes'],
      [
        step(
          'wait',
          '等待调用的不同范围',
          '普通模块发令后调用轴到位服务，无安全 XYZ 实际先发 Z 并等待，再发 XY 并等待。ETEL 测试方法另调用 ipolWaitMovement；各轴、MotionService 和卡 SDK 内部等待的完整契约仍在引用库边界。',
          ['sm-module-xy', 'sm-module-others', 'sm-etel-test'],
        ),
        step(
          'tasks',
          'T 轴任务还需要单独等待',
          '部分 Jump 先开后台 T 任务，等 Z 达条件才旋转；插补接口返回后再 Wait 该任务。取片、固晶、IPT 的条件与局部超时不同，提前返回或异常路径没有统一 join 已启动任务。',
          ['sm-pick-jump', 'sm-bond-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'failures',
          '返回与输入也有副作用',
          'MoveZAxis 可返回 Abort，某些 void 包装不接收该结果；MovePara 重载还会就地乘速度比例。插补异常、软件提前返回、轴等待异常并不统一撤销已发命令或恢复原参数。',
          ['sm-z-command', 'sm-module-parameters', 'sm-pick-jump', 'sm-gg-run'],
        ),
        step(
          'stop',
          '停止状态不代替逐轴结束',
          '普通 Stop 写状态并清部分信号/输出，没有逐轴 StopMove 或统一等待任务。急停另并行请求轴停止，再普通 Stop 并调用三个任务中止接口；这一层没有统一 join 或物料恢复，后续处理见恢复专题。',
          ['stop-state', 'stop-signals', 'stop-outputs', 'emergency-axes', 'emergency-tasks'],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖目标转换、软限位、安全高度顺序、场景分派、圆限位/路径工具、插补及等待停止。图表依据当前实现，没有执行现场轴运动、测定安全距离或验证驱动精度。区域动作的完整工艺步骤在所属生产专题继续展开。',
      refs: ['sm-xyz', 'sm-limits', 'sm-uplook-dispatch', 'sm-gg-run', 'emergency-axes'],
    },
  ],
};
