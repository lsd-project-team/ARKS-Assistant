import type { SourceGuide } from '../sourceGuides';
import { choices, outcome, step } from './builders.ts';

export const cameraCalibrationGuide: SourceGuide = {
  id: 'camera-calibration-review',
  topic: 'camera-calibration',
  diagrams: ['camera-calibration-process'],
  title: '建议阅读顺序',
  flows: [
    choices(
      'cc-dispatch',
      '自动标定入口',
      '先按工位区分入口，再沿 S2 主链阅读；点胶不是 S2 自动标定中的一个子步骤。',
      ['cc-entry', 'cc-main'],
      [
        step(
          'overview',
          '从工位入口看执行顺序',
          '主菜单先调用回零，再按当前工位排队后台任务：S1 调点胶标定，其他工位调 S2 自动标定。菜单没有判断回零返回值，也没有等待后台任务或接收点胶标定的 bool。',
          ['cc-entry', 'cc-main'],
        ),
        step(
          'confirm',
          '必做确认与失败退出',
          'S2 先清结果列表，确认清洁与 Touchdown 后做 Bond 相机；更换 BMC 吸嘴后依次做焊头偏移、上视相机。工具确认取消，或已检查的子任务返回 false，都会退出；此前动作与保存不会统一撤回。',
          ['cc-main'],
        ),
        step(
          'optional',
          '只有同标记对齐可跳过',
          'Bond/上视同标记对齐提示选择 OK 才执行，Cancel 只跳过此步。随后仍标定上视机械位置；工具确认后，再做晶圆两标记间距与晶圆 N 点。不能把此处 Cancel 解释为整套标定结束。',
          ['cc-main', 'cc-same-mark'],
        ),
        step(
          'finish',
          '走到末尾再显示汇总',
          '只有主链走到末尾，才调用标定参数 Save 并向界面派发结果窗口。后台任务已发起、某个子任务 true、进入结果窗口，是不同的完成位置；保存与最终复核的关系在后面单独说明。',
          ['cc-main', 'cc-result-window'],
        ),
      ],
    ),
    choices(
      'cc-cameras',
      '点胶与 Bond 采点',
      '采点位置、点数与所用模板按实际循环读取，不按旧注释中的“9点”推定。',
      ['cc-dispense', 'cc-bond-start', 'cc-bond-sampling', 'cc-grid'],
      [
        step(
          'grid',
          '点阵怎样从中心展开',
          'GeneratePointList 以给定中心、行列和间距居中生成点阵，外层遍历行、内层遍历列；双间距重载分别使用 X/Y 间距。采集的物理 XY 使用相对标定中心的差值。',
          ['cc-grid', 'cc-dispense', 'cc-bond-sampling'],
        ),
        step(
          'dispense',
          '点胶：九点后继续测高',
          '收回测高气缸后，按 3×3 点阵移动，用固定名称“点胶标定模板”采图；任一点非 Success 就 false。采样后建立相机变换，再去探针测高，成功才记录实位/高度、回安全位、保存参数并收回气缸。',
          ['cc-dispense'],
          [
            outcome(
              '后段失败',
              '测高失败可能发生在坐标文件更新之后；方法没有统一 finally 把气缸、位置和文件都恢复到调用前。',
              'cc-dispense',
            ),
          ],
        ),
        step(
          'bond',
          'Bond：测高再采三十点',
          '先 BMC 测高，成功立即写测高结果并保存设备参数，再记录相机 Z 偏移、定位与对中。采 6×5 点，X/Y 间距为源码中的 0.1/0.05，使用 BmcPRName；末段还会回中心再定位。',
          ['cc-bond-start', 'cc-bond-sampling', 'cc-bond-finish'],
          [
            outcome(
              '对中返回值',
              '前后两次 LocateAndMoveToTargetPixel 的 bool 都未在此接收，提示超限不一定使该任务 false。',
              'cc-bond-start',
              'cc-bond-finish',
            ),
          ],
        ),
        step(
          'transforms',
          'VM 与 Halcon 是两套输出',
          '从属坐标 Init 使用物理点和像素点生成 VM 标定；NPointTrans 另把两组 XY 传给 Halcon，求矩阵并分解比例、角度、平移和斜切。G0 专题解释这些坐标怎样被后续调用，保存时序见“保存与复核”。',
          ['cc-dispense', 'cc-bond-sampling', 'cc-fit', 'g0-savecal'],
        ),
      ],
    ),
    choices(
      'cc-uplook',
      '上视坐标与位置',
      '上视像素变换、焊头旋转中心和上视机械拍照位分别建立。',
      ['cc-uplook-sampling', 'cc-uplook-center', 'cc-uplook-position'],
      [
        step(
          'sampling',
          '上视相机的三十点变换',
          '对中后以 6×5 点采集上视模板结果，创建父级为 BondCoordinateSystem 的上视从属坐标，模式明确为 CameraStaticDown；随后另求 Halcon 矩阵。',
          ['cc-uplook-sampling'],
        ),
        step(
          'rotation',
          '五角度拟合像素旋转中心',
          '按 −180、−90、0、90、180 旋转并记录像素点，拟圆后移到圆心，再更新 GlassUpLookVisionMachinePos。整机子任务末段的 XY bondOffset 修正已被注释；参数保存发生在放回标定片之前。',
          ['cc-uplook-center'],
          [
            outcome(
              '放回标定片',
              '末段使用 Distance 模式调用 BondAction，未检查它的 bool，仍可写结果列表并 true。不能只看子任务返回推定实物已成功放回。',
              'cc-uplook-place',
            ),
          ],
        ),
        step(
          'position',
          '机械拍照位用 Bond 相机确定',
          'StartUpLookMachinePosTask 实际使用 WaferLeftPRName 和 Bond 坐标对中，记录 UpLookMarkMachinePos 并加入结果列表；方法内没有独立 Save。它与上视像素坐标标定是两个步骤。',
          ['cc-uplook-position'],
        ),
      ],
    ),
    choices(
      'cc-wafer',
      '晶圆相机与晶圆台',
      '先用 Bond 相机求两标记间距，再用晶圆相机建立 N 点变换和晶圆台到 G0 的关系。',
      ['cc-wafer-distance', 'cc-wafer-sampling', 'cc-wafer-general'],
      [
        step(
          'distance',
          '左右标记建立物理间距',
          '晶圆台到准备位后，Bond 相机分别对中左右标记，更新对应机械实位，并以右点减左点写 WaferTableMarksDistance。目标像素校验的 bool 在这些调用点没有被接收。',
          ['cc-wafer-distance'],
        ),
        step(
          'sampling',
          '晶圆相机采二十五点',
          '移开 Bond，移动晶圆台与相机 Z，以 5×5 点采集 WaferPRName 结果。晶圆相机从属坐标的父级是 WaferTableCoordinateSystem，模式为 CameraStaticUp；VM 生成与 Halcon 矩阵计算分别执行。',
          ['cc-wafer-sampling'],
        ),
        step(
          'general',
          '再建立晶圆台到 G0 的关系',
          '回中心并重识别右标记后，以右标记实位−两标记间距+焊头相机偏移求焊头旋转中心，保存标定参数。再创建晶圆台普通坐标，把该中心经 Bond 坐标正向变换后与晶圆台实位配对初始化，保存并刷新目录。',
          ['cc-wafer-general'],
          [
            outcome(
              '末段收尾',
              '之后才移开 Bond、抬 Z、把晶圆相机 Z 置零并加入结果列表；末段失败不表示先前文件没有写过。',
              'cc-wafer-general',
            ),
          ],
        ),
      ],
    ),
    choices(
      'cc-offset',
      '焊头偏移与旋转',
      '这里说明 StartBondToCamCalibTask1 的实际修正和复核，不把循环名称当作收敛保证。',
      ['cc-offset-prepare', 'cc-offset-rotate', 'cc-offset-base', 'cc-offset-review'],
      [
        step(
          'prepare',
          '定位标定片并取放到 BMC',
          '初定位用“小标定片模板”，后续像素校验用 GlassPRName。按现有偏移求取放位置，以 Distance 模式取放标定片，再对焦并读取对角标记；部分取放返回值未作为后续采点门控。',
          ['cc-offset-prepare'],
        ),
        step(
          'rotate',
          '两轮角度修正与重试',
          '每次做两轮 0/−180 取放与双点定位，以中心之差的一半修正 XY 偏移。任一分量绝对值超过 0.003 时增加 count 并重试；count==2 时，本轮计算后直接进入后段，不再按该阈值拒绝。',
          ['cc-offset-rotate'],
        ),
        step(
          'base',
          '建立 Bond 普通坐标',
          '用源码固定 G0 参照点 (200,−300,100)，与 BMC 位置、当前偏移和测高结果组成的机械点配对，初始化 BondCoordinateSystem。坐标 Save/Refresh 在最终复核之前已执行；这些固定数值不是供现场直接套用的标定建议。',
          ['cc-offset-base'],
        ),
        step(
          'review',
          '最终复核没有持续修正',
          '两角度复核比较玻璃与 BMC 中心差，源码检查的是带符号分量 <=0.004，没有取绝对值。step 初值为 0，即使未满足容差也会在 step==0 时退出，随后再次取片并 true。',
          ['cc-offset-review'],
          [
            outcome(
              '同标记的另一路修正',
              '可选同标记方法以 Bond/上视结果求对齐点，写 XY 偏移及 BondCamUpLookCamMachinePos；它不在本地独立 Save，也不是这段旋转重试的替代版本。',
              'cc-same-mark',
            ),
          ],
        ),
      ],
    ),
    choices(
      'cc-persistence',
      '保存与复核',
      '把设备参数、坐标目录、标定文件与结果显示分开，才能理解中途失败留下了什么。',
      [
        'cc-dispense',
        'cc-bond-start',
        'cc-bond-sampling',
        'cc-uplook-sampling',
        'cc-wafer-general',
        'cc-main',
      ],
      [
        step(
          'order',
          '先写入还是先完成复核',
          '下表按实际任务列出写入时点。主链没有统一事务：后续 false、异常或结果窗口取消，都不会自动撤回此前已发出的保存调用。',
          [
            'cc-dispense',
            'cc-bond-start',
            'cc-bond-sampling',
            'cc-uplook-center',
            'cc-wafer-general',
            'cc-offset-base',
            'cc-result-window',
          ],
        ),
        step(
          'files',
          '参数与转换文件各归其主',
          '标定运行参数的文件配置为设备目录 CalibratePara.json，Save 实现继承自外部 Singleton；这里证明调用顺序，未实测该库的序列化和持久性。坐标 JSON 与 .iwcal 的生成和刷新统一在 G0 专题解释。',
          ['cc-parameter-path', 'cc-path', 'g0-catalog', 'g0-savecal'],
        ),
        step(
          'window',
          '结果窗口不负责回滚',
          'FrmCalibResult 绑定像素比例和转换结果两个列表。OK 与 Cancel 都只是关闭窗口并通知父窗体，没有在这里另行应用、保存或回滚参数。独立包装方法即使没有接收内部 false，也可能继续显示该窗口。',
          ['cc-result-window', 'cc-only-offset'],
        ),
      ],
    ),
    choices(
      'cc-common',
      '对中与自动对焦',
      '公共服务的返回、命令发出与到位等待分别理解；不同相机枚举不保证都有完整实现。',
      ['cc-center', 'cc-pixel', 'cc-focus', 'cc-focus-body'],
      [
        step(
          'center',
          '按坐标名计算对中位移',
          'MoveToCamCenter 为四种相机选轴和坐标名。服务用从属坐标的一层正向转换求像素偏移，加轴命令位置后发 AbsoluteMove；该服务本地没有另一个显式 Wait 调用。这不是完整父链的 G0 转换。',
          ['cc-center', 'cc-center-service'],
        ),
        step(
          'pixel',
          '固定目标像素与严格容差',
          '目标固定为 (1224,1024)。每轮先定位并移动，再重新定位求 X/Y 偏差；两分量都严格小于容差才 true，最多 maxRetry 轮，最终超限提示并 false。底层定位异常继续抛出，多处标定调用并未接收 bool。',
          ['cc-pixel', 'cc-controller-locate', 'cc-bond-start'],
        ),
        step(
          'focus',
          '对焦枚举的实际实现',
          'CalibController 只有 Bond、UpLook 分支调用对焦，而且两者都传 BondCamera 与焊头 Z，参数顺序为 endPos、startPos；Dispense、Wafer 分支为空。不能按 UpLook 名称推定使用了上视物理相机。',
          ['cc-focus'],
          [
            outcome(
              '空辅助接口',
              'MoveWaferAndEjectorZ 当前没有运动语句，直接 true；不能把它画成已执行两个 Z 轴动作。',
              'cc-focus',
            ),
          ],
        ),
        step(
          'search',
          '清晰度粗扫与细调',
          '引用工程先粗扫并选最高评分位置，再按清晰度变化变向、减半脉冲，进入六轮式细调。该实现没有统一超时、范围有效性检查或本地显式到位等待；真实相机、清晰度算子与轴驱动结果仍需运行环境。',
          ['cc-focus-body', 'cc-sharpness'],
        ),
      ],
    ),
    choices(
      'cc-single',
      '独立方法的差异',
      'Only 方法与自动主链子任务不等价；以下作为源码中的独立能力阅读。',
      [
        'cc-only-cameras',
        'cc-only-uplook-a',
        'cc-only-uplook-b',
        'cc-only-wafer',
        'cc-only-offset',
      ],
      [
        step(
          'cameras',
          '单独相机方法不都更新 VM',
          'OnlyDispenseCameraCalib 主要生成比例/转换报告；OnlyBondCameraCalib 使用 0.4/0.3 间距采 30 点并写内存矩阵；OnlyWaferCameraCaib 采 25 点后显示报告。它们没有自动子任务中完整的 VM 坐标建立与保存链。',
          ['cc-only-cameras', 'cc-only-wafer'],
        ),
        step(
          'uplook',
          '独立上视还有取放片分支',
          '独立上视方法先取放标定片并逐点处理 Retry/Abort/Ignore。视觉 Ignore 可用默认匹配值继续；放片失败后的 Ignore 仍到该分支末尾 return。后续采 30 点、做像素与物理拟圆，实际减去 XY bondOffset 并保存。',
          ['cc-only-uplook-a', 'cc-only-uplook-b'],
          [
            outcome(
              '与整机上视不同',
              '整机上视的 XY 修正被注释，独立方法则执行；其末尾调用上视机械位方法也未检查 bool。不能将两个入口共用一条无条件流程。',
              'cc-uplook-center',
              'cc-only-uplook-b',
            ),
          ],
        ),
        step(
          'offset',
          '包装层没有统一成功判断',
          'OnlyBondToCameraOffsetCaib 调偏移任务后不接收 bool，仍添加偏移结果并显示窗口。主菜单当前直接引用 S1/S2 主入口；未定位到直接引用的 Only 方法不放入必经生产链。',
          ['cc-only-offset', 'cc-entry'],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖主入口、四类相机与机械坐标标定、焊头偏移、旋转复核、公共对中对焦及独立方法差异。源码数值用于解释实现；本页没有执行设备、生成现场标定参数或验证硬件精度。公共坐标转换与视觉采图分别链接到已有专题。',
      refs: ['cc-entry', 'cc-main', 'cc-focus', 'cc-offset-review'],
    },
  ],
};
