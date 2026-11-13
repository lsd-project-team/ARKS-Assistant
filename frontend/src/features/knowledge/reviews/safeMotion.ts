// 按目标换算、软限位、安全高度、场景分派、几何工具、插补与收尾组织阅读；各入口的实际覆盖范围不同，不能相互套用。
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
      '先确认传进来的是机械目标还是 G0 点，再看选用的入口实际检查了哪些轴。',
      ['sm-target-wrappers', 'sm-convert', 'sm-limits'],
      [
        step(
          'convert',
          '三维 G0 点先转机械目标',
          '按三维点移动时，先用 Bond 坐标做一层逆变换，再进入安全 XYZ 移动；按相机点位移动时，先减去焊头到相机的偏移。完整的父级坐标链换算统一见 G0 图谱，不能把这层换算当作所有坐标类型都能通用。',
          ['sm-target-wrappers', 'sm-convert'],
        ),
        step(
          'overloads',
          '标量与四维重载不同',
          '四维换算只变换 XYZ，T 保持不变。只给一个方向标量的两个入口，分别用 (X,0,X) 和 (0,Y,0) 求分量，不能自动简化成三维点的做法；实际传入的位置参数仍要按当次调用理解。',
          ['sm-target-wrappers', 'sm-convert'],
        ),
        step(
          'limits',
          '软限位检查的实际范围',
          '模块的二维检查只看 XY，三维检查看 XYZ；四维的软限位检查当前同样只查 XYZ，不含 T。超出限值时抛异常，而不是给出失败结果；只传 Y 标量的入口，下限取软限位值，其他入口多取轴参数表中的值。',
          ['sm-limits'],
        ),
        step(
          'commands',
          '发命令与调用等待分开',
          '模块的 XY、XYT、XYZT 移动通常先给各轴发绝对移动指令，再等待到位。离线或就绪条件不满足时也可能直接无结果退出；轴对象和运动服务内部的实际结果，不能只凭这种返回形式推定。',
          ['sm-module-xy', 'sm-module-xyzt', 'sm-module-others', 'sm-ready'],
        ),
      ],
    ),
    choices(
      'sm-height',
      '安全高度来源',
      '安全高度会随载具、工具、工位状态和区域变化，并不是所有入口都共用一个固定的 Z。',
      ['sm-level-xyz', 'sm-level-xy', 'sm-level-xyzt', 'sm-level-current'],
      [
        step(
          'product',
          '载具、点胶气缸与吸嘴',
          '有载具时，以载具 G0 原点加上产品的安全高度为基础；S2 测高气缸打开且装有点胶器时，减去焊头与点胶器的 Z 差，否则加上吸嘴的测高偏移。没有载具时先取设备安全点，再换算成机械高度。',
          ['sm-level-xyz', 'sm-level-xyzt'],
        ),
        step(
          'regions',
          '非工作状态与静态区域',
          '带目标点的入口在非工作状态可以把安全高度改成设备安全 Z；配置了静态华夫盘，且当前或目标的 Y 落在对应区域时，再按避让位和吸嘴偏移抬高安全高度。不带目标点的入口只看当前所在区域，也没有同样的非工作状态覆盖。',
          ['sm-level-xyz', 'sm-level-xy', 'sm-level-current'],
        ),
        step(
          'checks',
          '最终高度复查并不一致',
          '二维和三维的目标入口在覆盖与静态避让之后，会检查最终的安全高度。四维入口只在有载具的早期位置检查一次，之后即使又被覆盖或抬高，也没有同样的最终复查；不能把这些入口概括成完全一样的保护。',
          ['sm-level-xyz', 'sm-level-xy', 'sm-level-xyzt'],
        ),
      ],
    ),
    choices(
      'sm-order',
      '二维三维四维',
      '安全移动先求安全高度、检查目标与单步状态，再按当前和目标的 Z 选择动作顺序。',
      ['sm-xyz', 'sm-xyzt', 'sm-xy'],
      [
        step(
          'overview',
          'XYZ 的三种实际顺序',
          '当前高度不低于安全高度时，先走 XY，再下降到目标 Z；当前低而目标不低时，先抬到目标 Z，再走 XY；当前和目标都低时，先抬到安全 Z，再走 XY，最后到目标 Z。四维移动的水平动作组里还包含 T。',
          ['sm-xyz', 'sm-xyzt'],
        ),
        step(
          'table',
          'XY 还会恢复原来的高度',
          '二维 XY 移动在当前高度不足时先抬到安全 Z，走完 XY 后再恢复到原来的 Z；三维和四维则以给定的目标 Z 收尾，或把它作为先行动作。下表只说明动作的先后，不能代替每一步的实际结果。',
          ['sm-xyz', 'sm-xyzt', 'sm-xy'],
        ),
        step(
          'return',
          'Z 返回失败没有统一阻断',
          '单步状态不允许时会直接退出；内部的 Z 轴移动也可能中途中止，但这一段没有逐次检查它的结果，后面的 XY 动作仍可能照常发出。没有匹配到任何高度分支时会走异常出口，不能把所有输入都当成正常移动。',
          ['sm-xyz', 'sm-xyzt', 'sm-z-command'],
        ),
      ],
    ),
    choices(
      'sm-regions',
      '生产区域切换',
      '各场景先选普通绝对移动或插补，再按本场景的过渡点与互锁执行。',
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
          '预取片先检查翻转台的交接位或回零位。重新取片走普通的安全 XYZT 移动，其他情况按轴移动方式选择绝对移动或跳跃式移动；绝对取片先等到安全 Z，再等 XY 接近后发目标 Z，最后等待到位。',
          ['sm-pick-dispatch', 'sm-pick-absolute'],
        ),
        step(
          'bond',
          '固晶位置的普通与 Jump',
          '普通固晶先在需要时抬到安全 Z，等 XY 接近后再发目标 Z；两段局部等待各有 10 秒的判断。跳跃式移动按当前 Z 是否低于抬升高度决定走两段还是三段，并使用本场景的速度和前瞻参数。',
          ['sm-bond-absolute', 'sm-bond-dispatch'],
        ),
        step(
          'uplook',
          '上视按来源区域分派',
          '上视入口按静态华夫盘、翻转台、晶圆和刮胶盘分别处理。普通模式选用不同的安全高度；插补模式进入各自的跳跃式移动。翻转台上校正前蘸胶、两点校正这两条路径会先抬高、发出完成信号，再等胶盘缩回，超过 5 秒则抛异常。',
          ['sm-uplook-dispatch'],
        ),
        step(
          'ipt',
          'IPT 使用专属过渡点',
          'IPT 按普通或插补、静态华夫盘或晶圆来源选择路径。从晶圆到 IPT 的插补走四段，清嘴台配置和左右 IPT 会改变中间点与高度；并不是把各个区域直接连成一条直线。',
          ['sm-ipt-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'maintenance',
          '换嘴、安全位与拍照位',
          '换嘴入口先去换嘴安全 Z，再移动 XY，两段各有离线与单步检查。普通安全位会先收回 S2 测高气缸；上视、取片、测高和避让位置各自使用自己的参数或偏移来源。',
          ['sm-maintenance', 'sm-target-wrappers', 'sm-nozzle-height'],
        ),
      ],
    ),
    choices(
      'sm-geometry',
      '碰撞圆与规划工具',
      '运行中的圆限位和几何工具要分开阅读，不能因为工具名称就推定所有动作都经过了完整的避障规划。',
      ['sm-wafer-circle', 'sm-wafer-move', 'sm-path', 'sm-profile'],
      [
        step(
          'circle',
          '晶圆环限位检查目标 XY',
          '启用环限位时，比较目标到晶圆台中心的 XY 平方距离和半径平方；半径先取整，边界相等时算通过。它只检查目标的平面位置，不检查 Z，也不能证明整条路径全程不会碰撞。',
          ['sm-wafer-circle'],
        ),
        step(
          'wafer',
          '晶圆移动先有其他副作用',
          '带搜索的 G0 移动先关闭顶针台真空，再判断是否离线；特定搜索模式还会检查顶针的准备高度。条件通过后换算到晶圆普通坐标，发 X、Y 指令并等待到位；离线时的提前退出也不代表此前什么调用都没发生。',
          ['sm-wafer-move'],
        ),
        step(
          'intersection',
          '安全区域交点的计算边界',
          '路径规划工具按四个点的 XY 包围范围检查终点，并按固定的边顺序取第一个交点。求交时只检查起止线段的 X 范围，没有完整检查两条线段的 X、Y 范围，因此不能当作通用的精确避障求解。',
          ['sm-intersection', 'sm-path'],
        ),
        step(
          'tools',
          '半径、离散路径与距离参数',
          '取半径时，在交点到终点的 XY 距离与 Z 差绝对值之间取较小值；生成移动线时给出两组各 11 个点，零距离这类退化输入没有统一保护。距离参数这一段只给出加速、减速和加加速度的取值，不发出移动指令；目前只在速度实验中查到它对路径工具的直接调用。',
          ['sm-path', 'sm-profile', 'sm-path-experiment'],
        ),
      ],
    ),
    choices(
      'sm-interpolation',
      '插补与驱动',
      '生产动作按所属轴卡选择接口，ETEL 轴组和本地固高的辅助入口各有明确的适用范围。',
      ['sm-groups', 'sm-pick-jump', 'sm-gg-setup', 'sm-gg-run', 'sm-gg-pick'],
      [
        step(
          'groups',
          '按轴集合组织插补',
          'Bond 插补在 T 单独运动时只给 XYZ，其余情况给 XYZT；XY 组合只给 XY。XY、XYZ、XYZT 这三种插补组则明确按 ETEL 轴转换并缓存 ETEL 组，并不是能自动适配任意驱动的接口。',
          ['sm-groups'],
        ),
        step(
          'production',
          '按首轴找到所属轴卡',
          '取片、固晶和 IPT 的跳跃式移动，先用第一个轴查出所属轴卡，再交给该轴卡的运动控制器发起连续插补。取片按静态华夫盘、Bond 相机搜索和晶圆来源组合出不同的过渡段；T 的单独运动在外部任务中处理。',
          ['sm-pick-jump', 'sm-bond-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'gugao',
          '本地固高工具的组与指令流',
          '本地固高工具以第 2 个控制核心发起连续插补，传入轴组、轴号和脉冲当量，设置平滑与前瞻，再逐段写入绝对直线，非末段还带过渡衔接。数据结束的等待没有统一超时；启动后监视轴组和指令流，超过 30 秒抛异常，无论成败都会解散轴组并禁用。',
          ['sm-gg-setup', 'sm-gg-run'],
          [
            outcome(
              '接口归属',
              '实际生产调用的是轴卡接口，不能只因为同名就断定一定进入这个本地工具；部分结果逐次累加、部分直接覆盖，也不能说每条调用都即时独立通过。',
              'sm-pick-jump',
              'sm-gg-run',
            ),
          ],
        ),
        step(
          'pick-helper',
          '另一个辅助方法没有同样超时',
          '另一个取片插补的辅助入口把控制核心、轴组列表和轴组都固定为 2，使用固定的组约束和前瞻参数；数据结束和状态等待都没有上述 30 秒检查，要求高精度时还会逐轴等待实际到位。目前查到的直接调用在速度实验里，不能标成生产取片的必经步骤。',
          ['sm-gg-pick', 'sm-drive-experiment'],
        ),
      ],
    ),
    choices(
      'sm-completion',
      '等待、异常与停止',
      '发出指令、接口返回、等待完成，以及设备与任务是否全部停止，要分别确认。',
      ['sm-module-xy', 'sm-module-others', 'sm-pick-jump', 'stop-state', 'emergency-axes'],
      [
        step(
          'wait',
          '等待调用的不同范围',
          '普通模块发令后会调用轴到位服务；不带安全高度的 XYZ 移动，实际是先发 Z 并等待，再发 XY 并等待。ETEL 测试入口另外等待插补结束；各轴、运动服务和轴卡底层库内部等待的完整约定，仍属于外部库的边界。',
          ['sm-module-xy', 'sm-module-others', 'sm-etel-test'],
        ),
        step(
          'tasks',
          'T 轴任务还需要单独等待',
          '有些跳跃式移动会先启动后台的 T 任务，等 Z 满足条件才旋转，插补接口返回后再等待该任务结束。取片、固晶和 IPT 的条件与局部超时各不相同，提前返回或出错的路径并没有统一等待已启动的任务结束。',
          ['sm-pick-jump', 'sm-bond-dispatch', 'sm-ipt-jump'],
        ),
        step(
          'failures',
          '返回与输入也有副作用',
          'Z 轴移动可能中途中止，有些无结果的包装入口不接收这个结果；移动参数入口还会在原处把速度比例乘进去。插补出错、软件提前返回、轴等待出错时，都不会统一撤销已经发出的指令或恢复原来的参数。',
          ['sm-z-command', 'sm-module-parameters', 'sm-pick-jump', 'sm-gg-run'],
        ),
        step(
          'stop',
          '停止状态不代替逐轴结束',
          '普通停止只写入停止状态并清掉部分信号和输出，既没有逐轴停止，也没有统一等待任务结束。急停另外并行请求轴停止，再做普通停止并中止三个任务；这一层没有统一等待任务收尾，也没有物料恢复，后续处理见恢复图谱。',
          ['stop-state', 'stop-signals', 'stop-outputs', 'emergency-axes', 'emergency-tasks'],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖目标换算、软限位、安全高度的取值顺序、场景分派、圆限位与路径工具、插补，以及等待和停止。图表按当前做法整理，没有执行现场轴运动，也没有测定安全距离或验证驱动精度。各区域动作的完整工艺步骤在所属生产图谱继续展开。',
      refs: ['sm-xyz', 'sm-limits', 'sm-uplook-dispatch', 'sm-gg-run', 'emergency-axes'],
    },
  ],
};
