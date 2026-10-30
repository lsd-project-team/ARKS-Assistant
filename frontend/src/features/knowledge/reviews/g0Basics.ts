import { choices, outcome, step } from './builders.ts';

export const g0Relations = choices(
  'g0-relations',
  '坐标关系',
  '这一节回答：坐标挂在哪一层，各自保存什么？',
  [
    'g0-catalog',
    'g0-create',
    'g0-product',
    'g0-matter',
    'g0-cam-ds',
    'g0-cam-bond',
    'g0-cam-up',
    'g0-cam-wafer',
  ],
  [
    step(
      'reference',
      'G0 是共同参考',
      'G0 是坐标链的根参考名称。点胶、固晶、输送和晶圆台各有自己的局部坐标；转换让它们描述同一个位置。',
      ['g0-create', 'g0-forward', 'g0-ds-convert', 'g0-bond-convert'],
      [
        outcome(
          '图中连线',
          '连线表示标定或示教建立的典型上层关系。设备实际加载的父级由 UpperName 查找并绑定；这张图不代替现场坐标配置。',
          'g0-catalog',
          'g0-transport-teach',
          'g0-bond-base',
          'g0-wafer-base',
        ),
      ],
    ),
    step(
      'objects',
      '坐标对象保存什么',
      'Name 标识坐标，UpperName 保存上层名称，UpperCoordinateSystem 是内存中的上层引用。Distance 表示平移，Degree 表示旋转；Type 选择普通数学变换或 VM 标定变换。',
      ['g0-fields'],
      [
        outcome(
          '两种组织方式',
          'GeneralCoordinateSystem 可以沿父链逐级变换；DependentCoordinateSystem 用于相机等从属坐标，还需要调用者提供拍照时的上层位置。',
          'g0-forward',
          'g0-dependent',
        ),
      ],
    ),
    step(
      'product',
      '产品坐标逐层展开',
      '载具以 TransportCoordinateSystem 为上层，再把自己的坐标传给基板、模块和焊点。每个对象保存相对上层的位置与角度，最后可沿同一父链转换到 G0。',
      ['g0-product', 'g0-substrate', 'g0-module', 'g0-bp', 'g0-matter'],
      [
        outcome(
          '对象归属',
          'TuService 直接 new 普通坐标对象并赋给物料，再用 ElementCoordinate 初始化；这些产品坐标没有在该方法中加入设备坐标目录。',
          'g0-matter',
        ),
      ],
    ),
    step(
      'null',
      '零偏移辅助坐标',
      '它是按需创建的普通坐标，以 G0 为上层，用零点和零角度初始化。顶针等单轴接口借它进行位置转换；它是一个坐标对象，不是空引用。',
      ['g0-null', 'g0-eject'],
      [
        outcome(
          '创建前提',
          '这个辅助入口调用同一个创建方法。设备目录必须能正确建立 G0 和所需子坐标；缺少根时的首次创建行为见“加载与保存”。',
          'g0-null',
          'g0-create',
        ),
      ],
    ),
  ],
);

export const g0General = choices(
  'g0-general',
  '普通转换',
  '先看一层的旋转和平移，再区分整条父链与只变换一层的接口。',
  ['g0-math', 'g0-back', 'g0-forward', 'g0-inverse', 'g0-degree'],
  [
    step(
      'forward',
      '本地位置转换到上层',
      '普通坐标先在 XY 平面按 Degree 旋转，再加 Distance；Z 只加自身的 Z 偏移。SelfPosToG0 收集有上层引用的节点，从当前层向根依次调用这个变换。',
      ['g0-math', 'g0-forward'],
      [
        outcome(
          '根节点不再应用一次',
          '遍历遇到没有上层引用的对象就结束，该对象不加入变换列表；所以函数依据父链终止，不是看到名称 G0 才停止。',
          'g0-forward',
        ),
      ],
    ),
    step(
      'inverse',
      'G0 位置转换回本地',
      '一层逆变换先减平移，再反向旋转，Z 减去偏移。G0PosToSelf 收集与正向相同的父链，但从靠近根的一层向当前层逆序执行。',
      ['g0-back', 'g0-inverse'],
    ),
    step(
      'units',
      '角度累积与接口范围',
      'Degree 直接进入 Sin 和 Cos，使用弧度。DegreeInG0 累加父链中各层的 Degree；S1 点胶和 S2 固晶在使用 T 轴角度前，再乘 180/π 转成度。',
      ['g0-math', 'g0-degree', 'g0-s1', 'g0-s2'],
      [
        outcome(
          '一层与整链',
          'ForwardConvertCoordinate / BackConvertCoordinate 只处理当前层；SelfPosToG0 / G0PosToSelf 才组织父链。BondModule 的一些转换直接调用一层接口，不能按方法名假定都会遍历全部上层。',
          'g0-forward',
          'g0-inverse',
          'g0-bond-convert',
        ),
        outcome(
          '长度单位',
          '普通变换直接计算传入数值，没有自动换算 mm、μm 或像素；输入点与 Distance 必须使用相容单位，像素应先经过相机标定。',
          'g0-math',
          'g0-tool',
        ),
      ],
    ),
    step(
      'example',
      '用一个点核对转换顺序',
      '假设局部坐标直接挂在 G0 下，Degree = π/2，Distance = (100, 50, 3)，本地点为 (10, 0, 2)。旋转得到 (0, 10, 2)，再平移得到 G0 点 (100, 60, 5)。',
      ['g0-math', 'g0-forward'],
      [
        outcome(
          '反向核对',
          '从 (100, 60, 5) 先减 Distance 得到 (0, 10, 2)，再旋转 −π/2，回到 (10, 0, 2)。这里是说明算法的假设数值，不是设备标定参数。',
          'g0-back',
          'g0-inverse',
        ),
      ],
    ),
  ],
);

export const g0Camera = choices(
  'g0-camera',
  '相机转换',
  '相机结果从像素开始，必须同时知道标定关系和拍照时的机械位置。',
  ['g0-dependent', 'g0-tool', 'g0-calfile', 'g0-ds-convert'],
  [
    step(
      'inputs',
      '像素与拍照位置一起参与',
      '从属坐标的 SelfPosToG0 接收两个点：相机中的像素点，以及拍照时在直接上层坐标中的位置。它先转换像素，再加上层位置，最后调用直接父级的一层正向变换。',
      ['g0-dependent'],
      [
        outcome(
          '位置来源',
          '点胶接口使用 MatchResult 的 CenterX / CenterY；调用者未传 visionPos 时，才读取当前轴位置。传入的位置要对应这次拍照，不能随意用图像处理结束后的新位置替代。',
          'g0-ds-convert',
        ),
      ],
    ),
    step(
      'calibration',
      'VM 把像素变为物理坐标',
      'VM 正向变换首次使用时按坐标名称导入 .iwcal，随后复用对象中的转换工具。工具设置变换方向、输入 XY 并运行，输出转换后的 XY；Base 层另以输入 Z 加 Distance.Z。',
      ['g0-math', 'g0-calfile', 'g0-tool'],
      [
        outcome(
          '不是完整三维标定',
          '当前调用使用二维标定工具；Z 的处理是额外的加法，不表示标定文件解算了三维相机模型。',
          'g0-math',
          'g0-tool',
        ),
      ],
    ),
    step(
      'modes',
      '相机模式怎样影响结果',
      'RealisticCoordinateSystem 直接返回标定后的目标点。其余三种已列模式都先转换固定像素中心 (1224, 1024)，再用“中心结果减目标结果”作为 XY 偏移。',
      ['g0-tool'],
      [
        outcome(
          '模式名称不改变当前公式',
          'AxisAndCameraIsTogether、CameraStaticUp、CameraStaticDown 在这个重载中使用相同的减法；未知模式返回 null。固定中心是否适配实际图像尺寸，要与所用相机和标定数据一起核对。',
          'g0-tool',
        ),
      ],
    ),
    step(
      'parent',
      '从上层位置得到 G0 点',
      '像素转换结果与拍照位置相加后，从属坐标只执行直接父级的 ForwardConvertCoordinate；它没有继续调用父级的 SelfPosToG0。当前相机标定把父级设为点胶、Bond 或晶圆台坐标。',
      ['g0-dependent', 'g0-cam-ds', 'g0-cam-bond', 'g0-cam-up', 'g0-cam-wafer'],
      [
        outcome(
          '父级增加层数时',
          '不能把这个从属接口当作任意深度的通用坐标链；修改层级后，要重新核对直接父级是否已把结果带到预期参考中。',
          'g0-dependent',
        ),
      ],
    ),
  ],
);
