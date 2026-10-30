import { choices, outcome, step } from './builders.ts';

export const g0Production = choices(
  'g0-production',
  '生产应用',
  '下面是不同模块消费 G0 的方式，它们不是依次执行的一条生产链。',
  ['g0-s1', 'g0-s2', 'g0-wafer-move', 'g0-eject'],
  [
    step(
      's1',
      'S1：产品点变为点胶目标',
      '点胶节点把胶型的局部 XY 偏移经焊点坐标链转换到 G0，再加焊点点胶补偿和设备点胶偏移。角度取父链累计角度，转成度后加旋转补偿，随后交给插补接口。',
      ['g0-s1'],
      [
        outcome(
          '视觉与机械位置',
          '视觉识别经相机从属坐标得到 G0 点；移动前，点胶控制器再调用普通坐标的 G0PosToSelf 转为机械目标。',
          'g0-ds-convert',
          'g0-ds-move',
        ),
      ],
    ),
    step(
      's2',
      'S2：焊点位置与补偿汇合',
      '固晶节点先把焊点位置补偿放进产品坐标链得到 G0 目标，再叠加焊后、单焊点等补偿；随后按盲贴、IPT 或上视分支处理工具偏移，并扣除载具补偿。',
      ['g0-s2'],
      [
        outcome(
          '转为轴位置',
          'ConvertG0ToMachinePos 后还会加上该分支的 point3D 修正。BondModule 的三维重载只调用当前 Bond 坐标的一层逆变换；完整 Z 和 T 目标还包含吸嘴、高度及角度参数。',
          'g0-s2',
          'g0-bond-convert',
        ),
      ],
    ),
    step(
      'wafer',
      '晶圆台：G0 目标转为 XY 指令',
      'MoveWaferTableToG0Pos 在单步及安全条件检查后，以晶圆台坐标的 G0PosToSelf 求出轴位置，再分别发送 X、Y 绝对运动命令，并调用等待到位接口。',
      ['g0-wafer-move'],
      [
        outcome(
          '执行前的副作用',
          '该方法先关闭顶针台真空，再判断离线并返回；不能把离线分支理解为此前没有任何调用。',
          'g0-wafer-move',
        ),
      ],
    ),
    step(
      'axes',
      '单轴接口怎样使用坐标',
      '晶圆辅助方法将单个轴值放到三维点对应的 X、Y 或 Z 分量，再交给普通坐标 SelfPosToG0。顶针相关实位属性则借助 NullCoordinateSystem 包装单轴值。',
      ['g0-axis-helper', 'g0-eject'],
      [
        outcome(
          '保留分量含义',
          '这些接口没有自动推断轴类型、单位或补齐其他轴实位；阅读返回点时，要看调用者究竟把哪个轴值放进了哪个分量。',
          'g0-axis-helper',
          'g0-eject',
        ),
      ],
    ),
  ],
);

export const g0Limits = choices(
  'g0-limits',
  '使用边界',
  '最后检查配置、接口能力和运动边界，避免把计算得到的点当成已经完成的动作。',
  ['g0-catalog', 'g0-forward', 'g0-inverse', 'g0-dependent', 'g0-back'],
  [
    step(
      'chain',
      '父链需要有效且无环',
      '目录按名称绑定父对象，但没有统一拒绝缺失父级、同名对象或父链成环。普通转换遇到 null 就结束，因此缺失父级可能提前结束；成环则可能无法终止。',
      ['g0-catalog', 'g0-create', 'g0-forward', 'g0-inverse'],
      [
        outcome(
          '从属坐标不同',
          '从属转换直接使用父引用，没有同样的逐级终止逻辑，也没有本地空父级保护。配置错误不能一概当成返回零点。',
          'g0-dependent',
        ),
      ],
    ),
    step(
      'capability',
      '并非每个方向都已实现',
      'Base 的 VM 三维逆变换显式抛出不支持异常；DependentCoordinateSystem 的 G0PosToSelf 当前仅返回一个新建点，没有执行逆转换。',
      ['g0-back', 'g0-dependent'],
      [
        outcome(
          '旧重载也需区分',
          '标记 Obsolete 的二维 VM 正向分支为空，二维逆向分支只创建工具对象；不能把它们当作现用三维变换的等价实现。',
          'g0-legacy',
        ),
      ],
    ),
    step(
      'motion',
      '转换结果与动作完成分开读',
      '坐标方法负责计算和返回点。机械运动由上层控制器继续做限位、安全位置、速度、发指令与到位等待；相机 SDK 的运行和标定有效性也不能由一个坐标返回值替代验证。',
      ['g0-math', 'g0-tool', 'g0-ds-move', 'g0-wafer-move'],
    ),
  ],
);
