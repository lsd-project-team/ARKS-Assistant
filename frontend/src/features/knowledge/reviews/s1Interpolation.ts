import { flow, outcome, step } from './builders.ts';

export const s1InterpolationFlows = [
  flow(
    's1-pattern-preprocessing',
    '胶型坐标如何进入执行',
    'InterpolationApplication 将目标转换到机械坐标和点胶头位置，再调用 EpoxyPretreatment。后者克隆胶型，归一化、缩放运动参数，再旋转并平移图案点。',
    ['s1-ipol-data', 's1-pattern-extents', 's1-pattern-transform'],
    [
      step(
        'extent',
        '按整体包围范围归一化',
        'EpoxyPretreatment 先克隆图案，扫描全部段的 XY 最大最小值，取包围中心。每点减中心后按 SizeX/SizeY 和半范围缩放；两点段且策略为 SingleDotOnly 时再把首点改成两点平均位置。',
        ['s1-pattern-extents', 's1-pattern-normalize'],
      ),
      step(
        'motion',
        '补默认速度并乘比例',
        'Speed、Acc、Dec 小于等于 0 时分别补为 100、1000、1000，再乘 SpindleSpeedPercentage/100。这里把 NaN 的 X/Y 改为 0，没有同样处理 Infinity，也没有因 NaN 而拒绝整个胶型。',
        ['s1-pattern-motion'],
      ),
      step(
        'rotate',
        '旋转与高度分开处理',
        '按胶型 Angle 加调用角度旋转 XY，再加目标位置；图案 Z 加目标 Z。InterpolationApplication 随后按 isPrePlant 选择 PrePlantOffSetZ 或 OffsetZ，并用 SecurityHeightForEpoxyApplication 计算准备高度。',
        ['s1-pattern-transform', 's1-ipol-data'],
      ),
    ],
  ),
  flow(
    's1-interpolation-path',
    '插补、点胶与空跑',
    '控制器按图案段执行：先调用蘸胶辅助和首点准备，再处理提前开胶、到位等待、单点或曲线，按配置断尾。Success 只表示该方法到达返回语句，部分底层返回值没有被检查。',
    ['s1-ipol-first', 's1-ipol-advance', 's1-ipol-dot', 's1-ipol-tail'],
    [
      step(
        'first',
        '首点与空跑的返回位置',
        '每段先调用 PrintEpoxy；首段或 PrintingTool 类型启动胶压 Task，再等单步、移动到首段首点的准备高度、等待胶压 Task。IsDryCycle 在这些语句之后才返回 Success，因此会跳过后面的画胶和断尾，但不等于入口立即返回。',
        ['s1-ipol-first', 's1-ipol-print'],
        [
          outcome(
            '蘸胶配置',
            'PrintEpoxy 在硬件配置允许且类型为 PrintingTool 时停止蘸胶盘、移到蘸胶位、升降与停留，再启动盘转动；该辅助方法没有空跑门控。',
            's1-ipol-print',
          ),
        ],
      ),
      step(
        'advance',
        '提前开胶与到位等待',
        'AdvanceOpenDistanceNew 非零时发 Z 下降指令，循环读 Z，到阈值便开胶，再等待 Z 到位。该循环只睡眠并读位置，没有整体超时或 Stop/Pause 判断。DispenserLeadTime>0 时再按开关开胶或关胶并睡眠；这些开胶语句没有 isDrip 判断。',
        ['s1-ipol-advance', 's1-ipol-lead'],
      ),
      step(
        'dot',
        '单点分支使用 isDrip',
        '当前段恰为两点且 XY 相等，或策略为 SingleDotOnly 时进入单点分支。单步通过后按 isDrip 开胶或关胶；延时为首点 DripTime，加首次非预点胶的 FisrtDispenseDelay，随后关胶。',
        ['s1-ipol-dot'],
      ),
      step(
        'curve',
        '曲线的两种驱动路径',
        'ETEL X 轴取得插补组，按前一个点设置速度与加减速，逐点按 OpenGlueFlag 设置 IO，并发线性插补及等待。非 ETEL 调用 GuGaoDrive.Interpolation，但没有检查其 bool 结果；曲线分支自身不按 isDrip 屏蔽这些 IO。',
        ['s1-ipol-etel-setup', 's1-ipol-etel-io', 's1-ipol-gugao', 's1-gugao-signature'],
        [
          outcome(
            'isDrip=false 的范围',
            'isDrip 直接控制的是单点开胶分支；不能把它写成所有提前开胶、到位等待、蘸胶和曲线驱动的统一禁胶开关。空跑有更早的单独返回判断。',
            's1-ipol-dot',
            's1-ipol-advance',
            's1-ipol-lead',
            's1-ipol-first',
          ),
        ],
      ),
      step(
        'tail',
        '断尾、结束与异常',
        '每段按 TearOff1Open/TearOff2Open 调用 Z 升降和延时；全部段后调用 Z 到准备高度并返回 Success。catch 显示异常后返回 Fail，没有统一 finally 关胶、ipolEnd 或安全位清理。',
        ['s1-ipol-tail'],
        [
          outcome(
            '空图案段列表',
            'for 不执行，仍可到尾部 Z 移动与 Success；返回值不能单独证明执行过点胶。单步等待失败则在相应位置提前返回 Alarm。',
            's1-ipol-data',
            's1-ipol-first',
            's1-ipol-tail',
          ),
        ],
      ),
    ],
  ),
];
