import { flow, outcome, step } from './builders.ts';

export const s1InspectionFlows = [
  flow(
    's1-defect-acquisition',
    '胶检如何取得视觉结果',
    'S1 检测节点调用 DispenseVisionDefect。它先按目标位置启动灯光 Task 并移动，之后再判断空跑；正常模式进入共享的 VisionService，取得结果集合供胶量判定。',
    ['s1-defect-run', 's1-vision-position', 's1-vision-result'],
    [
      step(
        'position',
        '灯光与移动先于空跑判断',
        '目标位置非 null 时，异步查 PR 并设置经映射的灯光，同时调用移到拍照位，再 Task.Wait。目标位置为 null 则跳过这段；DryCycle 随后返回空列表，不返回模拟合格点。',
        ['s1-vision-position', 's1-vision-result'],
      ),
      step(
        'hardware',
        '实际取 S1 相机与轴',
        'GetHardware 收集 S1 点光/环光名称及点胶相机、XYZ 轴名称。正常模式停留后调用 VisionService.VisionDefect；外层没有在这里验证这些硬件对象是否都存在，取硬件过程也可能抛异常。',
        ['s1-vision-hardware', 's1-vision-result'],
        [
          outcome(
            '空跑仍可能触发数量报警',
            '返回空列表后，PostBondEpoxyCheck 仍比较 Count 与配置的 PostBondEpoxyNum。配置期望数量非零时进入报警选择；期望数量为零时循环不执行，可走尾部 Success。',
            's1-vision-result',
            's1-check-input',
            's1-check-success',
          ),
        ],
      ),
      step(
        'service',
        '共享视觉服务的返回边界',
        'VisionService 查找 PR 后，先写 IsDefectPR=true，再检查是否为 null。缺失 PR 因先访问对象可抛异常，不能保证进入后面的提示并返回 null。找到 PR 时加对象锁调用 DoWork；Success 返回 AlgResults，其他结果返回 null。',
        ['s1-vision-service'],
        [
          outcome(
            '生产节点消费异常',
            '视觉服务没有本地 catch；通过 S1 检测节点调用时，try 内异常被转成 Exception，随后仍执行 finally。不能把所有采集异常都写成胶量阈值不合格。',
            's1-vision-service',
            's1-defect-run',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-defect-thresholds',
    '胶量与偏差怎样判定',
    'PostBondEpoxyCheck 先检查集合和数量，再逐点计算面积比、X/Y 偏差。首个不满足条件的点中断循环并进入人工处理；本方法没有把 S1 视觉结果换成独立的 S1 坐标算法。',
    ['s1-check-input', 's1-check-geometry', 's1-check-limits'],
    [
      step(
        'input',
        '集合、数量与结果类型',
        'null 结果直接进入报警；Count 必须等于 (int)PostBondEpoxyNum。每项直接强制转换为 BlobResult，并按索引读取示教中心与面积集合；这里没有另做类型或三个示教集合长度的统一校验。',
        ['s1-check-input', 's1-check-geometry'],
      ),
      step(
        'geometry',
        '坐标与面积使用 S2 对象',
        '结果中心通过 S2 的 BondCameraCoordinateSystem 转换，面积乘 S2 相机比例的平方并保留四位。X 偏差为结果 X 减示教 X 再减 PostBondDistanceX；Y 原式为结果 Y 减示教 Y 再减负的 PostBondDistanceY，即加该距离值。',
        ['s1-check-geometry'],
      ),
      step(
        'limits',
        '圆形也比较面积比',
        '非圆形与圆形分支都用 Round(newArea/oldArea,2) 与 TolerantEpoxyMin/Max 比较；圆形计算的半径用于提示，没有改成半径比。面积通过后才比较 Abs(offsetX)>LimitX 和 Abs(offsetY)>LimitY；这些大小条件相等时不会因该项报警。',
        ['s1-check-area', 's1-check-limits'],
        [
          outcome(
            '只保留第一个异常路径',
            '面积超限或 X/Y 超限均 break；alarmMessage 非空便进入 PostBondCheckHand，不继续累计其余点的报警，也不进入后续导出。',
            's1-check-area',
            's1-check-limits',
          ),
        ],
      ),
      step(
        'export',
        '数据导出与检查结论分开',
        '无报警后，按 S2 配置 IsExportPostBondEpoxyCheckData 决定是否导出 Excel，写当前焊点及平均偏差、面积比。导出 catch 显示失败，但后续仍返回 Success；预点胶传入 null 焊点时，这个导出分支也可能在访问焊点字段时失败。',
        ['s1-check-export', 's1-check-success', 's1-pre-check'],
        [
          outcome(
            '空集合和零期望数',
            '数量相等时，空集合跳过逐点循环；不开导出便直接 Success。开导出则可能因 null 焊点或对空集合 Average 而进入导出 catch，最后同样可返回 Success。',
            's1-check-input',
            's1-check-export',
            's1-check-success',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-defect-operator',
    '胶检报警选择与返工',
    'PostBondCheckHand 找 PR 并调用主界面的报警委托，再把 DialogResult 转成动作返回码。生产检测与预点胶对同一返回码的消费方式不同。',
    ['s1-check-hand', 's1-alarm-ui', 's1-defect-results', 's1-pre-check-tail'],
    [
      step(
        'dialog',
        '主界面同步显示报警',
        'PR 不存在时先抛异常；存在时直接调用 VisionAlarmLockFunc，没有空委托检查。InitAction 将它绑定到 VisionAlarm；该方法加 UiLock，通过 Invoke 显示对话框，记录处理结果并调用 ResetAlarm，再返回选项和结果对象。',
        ['s1-check-hand', 's1-alarm-binding', 's1-alarm-ui'],
        [
          outcome(
            '结果对象没有在这里重算阈值',
            'PostBondCheckHand 只读取 dialogResult，没有用回调带回的 match 再做胶量公式计算。未知 DialogResult 抛“检测未知错误”。',
            's1-check-hand',
          ),
        ],
      ),
      step(
        'ok',
        '确认继续不保证再次检测',
        '对话框的 OK 分支遇到 EpoxyDetectAlg 直接返回 OK，没有在该分支重新执行视觉。PostBondCheckHand 将 OK 映射为 Success；生产检测据此提交焊点步骤。该继续选择不能描述成胶量阈值已经重新通过。',
        ['s1-alarm-ok', 's1-check-hand', 's1-defect-results'],
      ),
      step(
        'other',
        '跳过、终止、重做分别消费',
        'Ignore 映射为 Fail，生产检测禁用焊点后对线程返回 Success；Abort 映射为 Abort，终止按钮和生产检测都可调用 Stop；Retry 映射为 Retry，生产检测尝试 ReDispense。预点胶 DoWork 丢弃检查返回码，不按这里的四种结果分支。',
        [
          's1-alarm-abort',
          's1-alarm-skip',
          's1-alarm-retry',
          's1-check-hand',
          's1-defect-results',
          's1-defect-rework',
          's1-pre-check-tail',
        ],
        [
          outcome(
            '返工仍可能建立失败',
            'ReDispense 先改焊点步骤，再按相同动作名、基板、基岛与步骤名重置消息。消息列表非空时，匹配不到就抛异常；空列表跳过查找和消息重置。这是返工准备的实际边界，不能把 Retry 选项直接画成补胶已成功。',
            's1-defect-rework',
            's1-rework-messages',
          ),
        ],
      ),
    ],
  ),
];
