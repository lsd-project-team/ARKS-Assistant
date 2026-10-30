import { choices, outcome, step } from './builders.ts';

export const g0Registry = choices(
  'g0-registry',
  '加载与保存',
  '设备坐标目录、坐标对象和磁盘文件有各自的生命周期。',
  ['g0-catalog', 'g0-create', 'g0-path'],
  [
    step(
      'load',
      '首次访问时加载目录',
      'GetInstance 在单例为空时读取坐标 JSON。读取结果为 null 时新建空目录，然后执行 Init；它不会在加载阶段自动补齐全部设备坐标。',
      ['g0-catalog'],
      [
        outcome(
          '父级绑定',
          'Init 对名称不是 G0 的对象，按 UpperName 在目录中查找父对象并赋值。',
          'g0-catalog',
        ),
      ],
    ),
    step(
      'create',
      '创建或替换一个坐标',
      '先按 upperName 找上层。有上层时，删除目录中的同名项，按参数创建普通或从属对象，加入列表并保存。这里是替换对象，不是原地更新旧对象。',
      ['g0-create'],
      [
        outcome(
          '上层是 G0，但目录里没有它',
          '本次只创建、保存并返回 G0，随后直接退出；请求的子坐标还没有创建。调用者若接着按子名称查找，可能仍得到 null。',
          'g0-create',
        ),
        outcome('其他上层缺失', '直接抛出“上层坐标系丢失”，不继续建立子坐标。', 'g0-create'),
      ],
    ),
    step(
      'storage',
      '参数与标定文件分别保存',
      'MachineCoordinateSystem.Save 把目录交给 JSON helper。文件位于程序目录的 Settings → DeviceParams → MachineCoordinateSystem 文件夹：JSON 保存坐标参数，“坐标名.iwcal”保存相机标定结果。',
      ['g0-catalog', 'g0-path', 'g0-savecal'],
      [
        outcome(
          '保存范围',
          'Save 本身没有同时重做标定、刷新单例或重建产品坐标。内存父引用和转换工具标记为 JsonIgnore，加载后分别重新绑定或按需载入。',
          'g0-catalog',
          'g0-fields',
          'g0-calfile',
        ),
      ],
    ),
    step(
      'refresh',
      '刷新只清空单例入口',
      'Refresh 把静态 instance 设为 null，下一次 GetInstance 才重新加载。已经被其他对象持有的旧坐标引用不会因此自动替换；替换同名坐标后，已有子对象也可能仍引用旧父对象。',
      ['g0-catalog', 'g0-create'],
      [
        outcome(
          '产品对象也需留意',
          '产品坐标持有创建时传入的父对象。设备坐标重建后，需要核对产品对象何时重新创建或重新绑定，不能把刷新单例等同于所有调用者已更新。',
          'g0-matter',
          'g0-product',
        ),
      ],
    ),
    step(
      'lookup',
      '查找与删除接口的实际行为',
      'Find 按名称返回列表中的匹配项，未找到时可返回 null。DeleteCoordinateSystem 当前只调用 Save 并返回 false，没有从列表中删除任何坐标。',
      ['g0-create'],
    ),
  ],
);

export const g0Calibration = choices(
  'g0-calibration',
  '标定与修正',
  '初始化、定位修正和人工偏移是三种不同操作，保存和生效时点也要分别看。',
  ['g0-init', 'g0-update', 'g0-offset-ui', 'g0-savecal'],
  [
    step(
      'initial',
      '建立位置与角度',
      '点对点 Init 清空采点列表，设置 Distance = 上层点 − 本地点，并写入 Degree 和相机模式。ElementCoordinate 重载则复制其中的位置和角度；两者本身都不保存设备目录。',
      ['g0-init'],
      [
        outcome(
          '按代码理解初始化',
          '点对点重载直接计算两个点的差，没有根据传入角度重新求解平移。ElementCoordinate 的位置也直接作为平移使用。',
          'g0-init',
        ),
      ],
    ),
    step(
      'samples',
      '多点标定并写出文件',
      '列表重载保存物理点和像素点，调用 TransformTool.Save。工具逐项构造图像点与世界点，运行 N 点标定并导出对应坐标名的 .iwcal。',
      ['g0-init', 'g0-savecal'],
      [
        outcome(
          '点数检查属于不同接口',
          '另一个 CalcTransMatrix 方法检查两组数量相等且点数为 4～32；列表 Init 实际调用的 Save 没有这些本地检查，不能把前者的保护套用到后者。',
          'g0-matrix',
          'g0-savecal',
        ),
      ],
    ),
    step(
      'correct',
      '根据定位结果修正坐标',
      'UpdateCoordinateSystem 先把旧点和新点转换到上层，计算差值。通过阈值后，以新点为中心修正 XY 原点，累加 Degree，并把 Z 差加到原偏移。',
      ['g0-update'],
      [
        outcome(
          '修正门槛',
          '任一方向的平移差绝对值大于 10，或角度绝对值大于 0.2 弧度时抛异常。该方法没有调用目录 Save；是否持久化取决于后续调用。',
          'g0-update',
        ),
      ],
    ),
    step(
      'manual',
      '人工输入与追加偏移',
      '设备坐标窗口的保存操作直接覆盖 Distance 和 Degree，再保存目录。InitOffSet 则把传入的位置和角度加到现值；两者不能互换理解为“增加偏移”。',
      ['g0-offset-ui', 'g0-init'],
      [
        outcome(
          '入口范围',
          '窗口只列出普通坐标对象。写入角度时直接取控件数值，没有在这个处理函数内做度与弧度换算。',
          'g0-offset-ui',
          'g0-offset-load',
        ),
      ],
    ),
    step(
      'effect',
      '标定结果怎样被后续读取',
      '相机标定入口通常先建立从属坐标，调用列表 Init 写出标定文件，再 Save 和 Refresh 设备目录。新的坐标对象在首次转换时按名称载入工具。',
      ['g0-cam-ds', 'g0-cam-bond', 'g0-cam-up', 'g0-cam-wafer', 'g0-calfile', 'g0-math'],
      [
        outcome(
          '旧工具缓存',
          '列表 Init 不会在这里清空已有 CCalibTransTool；若外部仍持有旧坐标对象，它可能继续使用此前载入的工具。设备目录刷新与调用方引用更新需要一起核对。',
          'g0-init',
          'g0-math',
          'g0-catalog',
        ),
      ],
    ),
  ],
);
