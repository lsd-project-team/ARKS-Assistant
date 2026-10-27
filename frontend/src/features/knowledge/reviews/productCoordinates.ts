import type { SourceGuide } from '../sourceGuides';
import { choices, flow, outcome, step } from './builders.ts';

export const productCoordinatesGuide: SourceGuide = {
  id: 'product-coordinates-review',
  topic: 'product-coordinates',
  diagrams: ['product-coordinate-lifecycle'],
  title: '建议阅读顺序',
  flows: [
    choices(
      'product-hierarchy',
      '对象与父级',
      '载具、基板、模块和焊点各有自己的局部坐标；父级引用把它们连接到设备坐标。',
      ['pc-root', 'pc-substrate', 'pc-module', 'pc-bond', 'pc-create'],
      [
        step(
          'chain',
          '从载具连接到焊点',
          '载具坐标以 TransportCoordinateSystem 为父级；基板引用载具，模块引用基板，焊点引用模块。创建每层对象时，新建普通坐标并装入该层的 ElementCoordinate。',
          ['pc-root', 'pc-substrate', 'pc-module', 'pc-bond', 'pc-create'],
        ),
        step(
          'construct',
          '创建实例再注入工艺',
          '载具先建立坐标和普通或异形子对象，再按配置修改焊点加工状态，最后分别注入 S2、S1 步骤。带工位参数的构造在 Init 完成后才添加对应工位偏移。',
          ['pc-init', 'pc-modify'],
          [
            outcome(
              '配置异常',
              'ModifyMatter 捕获异常后清空 OtherConfig 信息并保存产品配置，未重新抛出。不能把继续构造解释为屏蔽数据全部正确。',
              'pc-modify',
            ),
          ],
        ),
        step(
          'inherit',
          '父级变化如何传到子级',
          '子坐标保留父坐标对象引用。后续把局部点转换为 G0 时，沿父链逐层读取当前值；不需要预先给每个焊点复制一份绝对位置。正反转换公式统一见 G0 坐标系。',
          ['pc-create', 'g0-forward'],
        ),
        step(
          'refresh',
          '刷新会重建坐标与状态',
          'Refresh 重建载具坐标，再刷新现有基板、模块和焊点的坐标；随后清视觉、清测高，复位 S1/S2 偏移标志。这条路径不会重新按 Count 创建整套子对象。',
          ['pc-refresh', 'pc-sub-refresh', 'pc-module-refresh', 'pc-bond-refresh'],
        ),
      ],
    ),
    choices(
      'product-expansion',
      '实例展开与顺序',
      '先区分实例的物理位置、行列标记和加工序号，再看普通矩阵与异形配置。',
      ['pc-matrix', 'pc-sub-matrix', 'pc-order', 'pc-row', 'pc-irregular'],
      [
        step(
          'single',
          '单个对象与默认元素',
          '基板或模块未启用多实例时，Count、行数和列数都改为 1，并清空原元素列表、补一个默认坐标。列表为空时也会补一个默认元素；这不保证任意 Count 都有足够的元素。',
          ['pc-matrix', 'pc-sub-matrix'],
        ),
        step(
          'matrix',
          '按间距生成坐标',
          '启用间距输入时，以首点为基准，X 加列间距×列号，Y 加行间距×行号；Z 保留首点值，新元素角度设为 0。实例循环仍取 Count，矩阵模式再计算行列标记。',
          ['pc-matrix', 'pc-sub-matrix'],
          [
            outcome(
              '数量约束',
              '创建对象直接读取 ElementCoordinates[index−1]，此处没有统一核对 Count、行列乘积与元素数量；不一致可能越界。',
              'pc-matrix',
              'pc-substrate',
              'pc-module',
            ),
          ],
        ),
        step(
          'order',
          '蛇形改变加工序号',
          '基板和模块的 WorkIndex 另由 GetIndex 计算，组合八种起始方向与 Normal/Snake 分支。它不会改写前一步生成的物理坐标。',
          ['pc-order', 'pc-substrate', 'pc-module'],
          [
            outcome(
              '按当前实现阅读',
              'RowAndColumn 的 Snake 奇偶分支实际得到相同列值；GetIndex 的 RightDownToUp 蛇形分支也未区分奇偶结果。不能把所有方向都解释成理想蛇形反转。',
              'pc-row',
              'pc-order',
            ),
          ],
        ),
        step(
          'irregular',
          '异形结构按子列表展开',
          '异形载具从 DownConfigs 创建基板，基板再创建模块，模块再创建焊点。每个对象使用自己的名称与 ElementCoordinate，WorkIndex 取当前列表序号。普通焊点则按 SingleBpPositionConfigList 创建。',
          ['pc-irregular', 'pc-sub-irregular', 'pc-module-bonds', 'pc-bond'],
        ),
      ],
    ),
    choices(
      'product-locate',
      '定位参考点与角度',
      '新旧参考点、匹配角、两点角和拟圆是不同计算分支，按配置选用。',
      ['pc-old', 'pc-new', 'pc-angle', 'pc-update'],
      [
        step(
          'components',
          'X 和 Y 分别选点',
          '旧点取示教位置，新点取识别结果。X、Y 各自按 UseX/UseY 和已配置点数累加平均；一个分量未启用任何点时保持 0，两种计算返回的 Z 都为 0。',
          ['pc-old', 'pc-new'],
        ),
        step(
          'match-angle',
          '匹配角取平均再转换',
          'CalculateUpdateAngle 按 UseAngle 累加匹配角并平均，再乘 π/180。UpdateEntity 对它取负并扣除父链角度；第四个匹配角实际仍由第三点的 UseAngle 控制。',
          ['pc-angle', 'pc-update'],
        ),
        step(
          'two-point',
          '两点角度有独立公式',
          '启用两点算角且定位点数至少为二时，先分别用 atan2 求新旧两点方向，再用 atan(新方向−旧方向) 扣除父链角度。这里保留源码中的额外 atan，不能直接当作标准方向角差。',
          ['pc-update'],
        ),
        step(
          'circle',
          '拟圆只使用前三点',
          '三点或四点定位启用拟圆时，以前三个示教点和结果点的圆心替换新旧参考点；第四点不参与圆心计算。角度仍使用前面选出的计算分支。',
          ['pc-update'],
        ),
      ],
    ),
    flow(
      'product-update',
      '结果写回与后续目标',
      '已有定位结果进入 UpdateEntity 后，先计算，再检查与写回当前坐标；末尾才设置定位标志。',
      ['pc-update', 'g0-update', 'g0-forward'],
      [
        step(
          'overview',
          '从结果到后续目标',
          '先清空四张结果图片，计算新旧参考点与角度，然后调用当前对象的 UpdateCoordinateSystem。调用失败时，不能把此前的图片清理视为已回滚。',
          ['pc-update'],
        ),
        step(
          'limits',
          '差值和角度先过限值',
          '坐标更新先把新旧参考点各做一次当前坐标的正向变换，再求差。任一 XYZ 差值绝对值大于 10，或角度绝对值大于 0.2，都会抛异常；这里按源码数值展示，长度单位需跟随参数来源。',
          ['g0-update'],
          [
            outcome(
              '异常出口',
              '限值检查位于本次 Distance/Degree 写入之前。UpdateEntity 不会执行末尾的 IsVisioned=true，但也未在入口统一清除原有标志。',
              'pc-update',
              'g0-update',
            ),
          ],
        ),
        step(
          'write',
          '写当前坐标后置标志',
          '检查通过后，按修正角旋转更新当前坐标的 XY，累加 Degree 与 Z 差值；正常返回后置 IsVisioned=true。这里没有保存产品配置，也没有执行机械运动。',
          ['g0-update', 'pc-update'],
        ),
        step(
          'consume',
          '后续转换使用新父链',
          '后续焊点局部点转 G0 时，会读到父级更新后的位姿。S1、S2 对工具、设备及焊后补偿的叠加，继续在 G0 的生产应用中阅读；坐标计算完成与轴到位属于不同阶段。',
          ['g0-forward', 'g0-s1', 'g0-s2'],
          [
            outcome(
              'S1 双点距离分支',
              '距离检查返回 Retry 时重读首点，Abort 时停机返回；返回 None 时先屏蔽物料，仍继续更新坐标。三、四点调用也分别在对应定位完成且实体未 Fail 时写回。',
              'pc-s1-locate',
            ),
          ],
        ),
      ],
    ),
    choices(
      'product-offsets',
      '工位偏移与焊点补偿',
      '载具整体偏移、分段移动和焊点局部补偿由不同对象管理。',
      ['pc-offsets', 'pc-divide', 'pc-compensate'],
      [
        step(
          'stations',
          'S1 与 S2 各有偏移标志',
          '设置工位偏移时，先检查对应标志；未设置才给载具 Distance 加该工位偏移并置标志。S1、S2 标志彼此独立，设置 S2 不会自动撤销 S1；Refresh 会复位两者。',
          ['pc-offsets', 'pc-refresh'],
        ),
        step(
          'divide',
          '分段通过载具 X 推进',
          '分段模式为 Divide 时，正向传输给载具坐标 X 加 DistanceToRight，反向操作减去相同值；未启用 Divide 则不改该值。子级继续通过父链体现这次位移。',
          ['pc-divide', 'g0-forward'],
        ),
        step(
          'bond',
          '点胶与固晶各取对应补偿',
          '普通焊点的固晶位置和角度取 BondPosOffset、RotaryPosition，点胶取 DispensePosOffset、DispenseRotaryPosition；普通配置为 null 时改用异形配置的对应字段。它们与载具工位偏移分别读取。',
          ['pc-compensate'],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖产品层级、普通与异形展开、定位计算和写回、工位偏移及焊点补偿。图文说明当前静态实现；公共坐标转换见 G0，视觉采集和报警另见视觉专题，设备实际定位与运动未在这里运行。',
      refs: ['pc-init', 'pc-update', 'pc-compensate', 'g0-forward'],
    },
  ],
};
