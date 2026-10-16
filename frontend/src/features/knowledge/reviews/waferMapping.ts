import { choices, flow, outcome, step } from './builders.ts';

export const waferMappingFlows = [
  choices(
    'wafer-map-search',
    'WaferMap：定位循环与未实现分支',
    '地图搜索跳过过桥点和视觉跳过点；双点定位当前不执行注释中的算法。',
    ['ws-map-search-a', 'ws-map-search-b'],
    [
      step(
        'mode',
        '开启 Standard 单点才进入定位',
        '取得地图点并转换物理位置后，Standard 的 IsTwoPointSearch=true 直接抛异常，下方双点实现全部注释。单点才移动并 AnalyseDie；MultipleSearch、未知模式和关闭位置搜索也抛异常。',
        ['ws-map-search-a', 'ws-map-two-comment', 'ws-map-search-b'],
      ),
      step(
        'preget',
        '预取跳过时推进位置，但回填沿用旧坐标',
        '预取开启、视觉 isSkip 且当前非过桥点时，直接从 WaferMapII 取得并前进到另一条 currentDieInfo；随后 SetPhysicalCoordinate 使用新的 Position 和此前已计算的 currentDieRealPosition。这是代码现有顺序，不能描述为新点已经重新定位。',
        ['ws-map-search-b'],
      ),
      step(
        'loop',
        '处理后检查停止，过桥或跳过就继续',
        '定位处理后 StopSearch；只要 currentDieInfo.IsSpringboard 或 isSkip 就回循环，两者均 false 才 MoveDieToPickCenter 并 true。异常出口在 catch 内另外处理，不能统一画成 false。',
        ['ws-map-search-b'],
      ),
    ],
  ),
  choices(
    'wafer-map-end',
    'WaferMap：无可取芯片与末尾参考点',
    '无可达芯片可以转入参考点缓存，也可以请求换片；找不到路径是异常。',
    ['ws-map-end-a', 'ws-map-end-b', 'ws-map-end-c'],
    [
      step(
        'references',
        '配置末尾取参考点时建立缓存',
        'NoApproachableChipException 且 IsWaferMapPickRefInEnd=true 时新建缓存，复制参考点，筛选出属于当前所选芯片类型集合的点，并保存它们的参考物理坐标。缓存非空就递归 NextDie；这里尚未设置换料和槽 Bad。',
        ['ws-map-end-a', 'ws-map-end-b'],
      ),
      step(
        'change',
        '没有合格缓存，或缓存取完才 false',
        '没有可继续的参考点时，或捕获 PickRefEndException 时，置原始换料和地图换料标记、将槽设 Bad、保存设备参数、调用地图 Unlock，再 false。这些调用中的异常仍可能截断后续操作。',
        ['ws-map-end-b', 'ws-map-end-c'],
      ),
      step(
        'path',
        '找不到路径抛中文异常',
        'NotFoundPathException 转为“晶圆图未找到路径,请重置当前点”的异常；ThreadAbortException 和其余异常向上抛。它们没有在 SearchMapping 里统一转换成换片 false。',
        ['ws-map-end-a', 'ws-map-end-c'],
      ),
    ],
  ),
  choices(
    'wafer-map-cursor',
    'WaferMap：预取、参考缓存与取晶提交',
    '搜索取候选、取晶后推进、修改芯片类型是不同阶段；参考缓存还会改变这些调用的路径。',
    ['ws-map-next-a', 'ws-map-next-b', 'ws-map-remember', 'ws-map-refresh'],
    [
      step(
        'candidate',
        '缓存非 null 时优先读第一项',
        'GetNextPositionInfoAndForwardTo 只要参考缓存非 null 就走缓存分支；计数为 0 抛 PickRefEnd，非空取第 0 项，但此处不删除。缓存为 null 才设步距，按预取配置调用 PreGet，过桥点立即前进；未预取直接取并前进。',
        ['ws-map-next-a', 'ws-map-next-b'],
      ),
      step(
        'remember',
        '记录阶段可能再次推进',
        'RemeberPickedDieInfo 在启用预取时再调用 WaferMapII.GetNextPositionInfoAndForwardTo，并用 dieMarkCenterG0Pos 转換坐标回填 currentDieInfo.Position，然后记录 lastPickedDieInfo。这里没有另以 NeedPickRefDie 避开参考缓存路径。',
        ['ws-map-remember'],
      ),
      step(
        'commit',
        '参考缓存删除与芯片类型更新分开',
        'RefreshPickedDieStatus 在 NeedPickRefDie=true 时删除缓存第 0 项；否则尝试 SetChipType(lastPickedDieInfo.Position)。类型更新异常只弹提示，随后仍调用 AsyncSaveFile。Box、Single、Nine 不走同一状态更新。',
        ['ws-map-refresh', 'w-refresh-mode'],
        [
          outcome(
            '保留地图库的实现边界',
            '这里证明了异步保存方法被调用，尚未核对 AKRS.WM 库内的保存完成、寻路并发和文件一致性机制。与本项目设备参数的 UI Invoke 保存不可混为一谈。',
            'ws-map-refresh',
            'ws-box-save',
            'w-form-ui',
          ),
        ],
      ),
    ],
  ),
  flow(
    'wafer-map-reference',
    'WaferMap：设首参考点与逐段寻路校正',
    '先设行列步距与首参考坐标，再按参考点之间的路径移动；等待循环没有本地停止检查。',
    ['ws-map-ref-set', 'ws-map-find-start', 'ws-map-find-wait'],
    [
      step(
        'first',
        '首参考点坐标与步距单位',
        'SetWaferMapSpacing 将行列步距取负并各乘 1000，构造 ChipOffset。无参 SetReferencePoint1 把实际 G0 的 X/Y 乘 1000 后写首参考点；Point 重载直接使用传入点。两者都拒绝 null 或空参考列表。',
        ['ws-map-spacing', 'ws-map-ref-set', 'ws-map-ref-overload'],
      ),
      step(
        'seek',
        '逐对参考点启动寻路并等待',
        'FindReferencePoint 保存当前地图位置、取得参考列表后，将策略前进到首参考点。首段以首点到首点寻路，后续以前一点到当前点寻路；WaitForAsyncResultBetweenTwoPoints(0, …) 未完成时空循环。未找到路径按结果抛异常；这里没有 StopSearch、Sleep 或本地截止时间。列表只检查 Length，没有先判断 null。',
        ['ws-map-find-start', 'ws-map-find-wait'],
      ),
      step(
        'correct',
        '过桥与参考终点分别回填',
        '路径每一步先移动并匹配；成功时用第 0 个视觉偏移修正位置再移动，失败且为过桥点则用实际位置。非过桥点写参考坐标，过桥点写普通物理坐标；非过桥匹配失败没有在这里被拒绝，仍会到参考坐标写入。',
        ['ws-map-find-move', 'ws-map-find-correct'],
      ),
      step(
        'finish',
        '策略位置与界面光标分别恢复',
        '全部参考点处理后设 bFlag=true，记录最后参考点，将策略 ForwardTo 原 currentPoint，而界面光标 SetCursor(lastRefPoint)。这段没有调用地图保存，也没有说明两种位置是同一个值。',
        ['ws-map-find-finish'],
      ),
    ],
  ),
  choices(
    'wafer-map-start-point',
    'WaferMap：移到起点与路径启动',
    'MoveToStartPoint 从最近可参考位置走到策略当前起点；另一个入口 StartAsyncSeekingPath 受参考缓存影响。以下是不同调用的阅读项，不表示全部依次执行。',
    ['ws-map-start-seek', 'ws-map-start-wait', 'ws-map-async'],
    [
      step(
        'seek',
        '取当前起点，寻找最近可参考点',
        '读取策略当前起点、设置步距、检查参考列表 Length，再 FindNearestReferableCoordinates 并启动两点间寻路。与 FindReferencePoint 一样，等待结果是空循环；NoResource 与其他未找到路径结果分别抛异常，没有本地停止或超时处理。',
        ['ws-map-start-seek', 'ws-map-start-wait'],
      ),
      step(
        'move',
        '先更新光标，再移动和校正',
        '每步先 SetCursor，转换物理坐标并移动、匹配；成功使用第 0 个偏移校正，失败且是过桥点使用实际位置。随后无论匹配是否成功都乘 1000 回填物理坐标；循环直到 Position 等于 targetPosition。',
        ['ws-map-start-move', 'ws-map-start-finish'],
      ),
      step(
        'async',
        '参考缓存非空时不启动普通寻路',
        'StartAsyncSeekingPath 只有 NeedPickRefDie=false 才清策略完成标记并启动普通 ValidAndVoid 寻路；缓存有参考点时跳过这两次调用。StopAsyncSeekingPath 只是委托地图接口。包装方法没有自行等待结束。',
        ['ws-map-async', 'ws-map-next-b'],
      ),
    ],
  ),
  choices(
    'wafer-map-config',
    'WaferMap：配置回填、读取与保存调用',
    '配置按字段依次写入，部分调用请求保存；当前没有原子提交或失败回滚。',
    ['ws-map-config-set', 'ws-map-config-read-a', 'ws-map-config-read-b'],
    [
      step(
        'write',
        '依次写七类配置',
        'SetWaferMapDataConfig 依次写 JumpStep、参考列表、首参考物理坐标、最后访问路径、用户方向、起点、所选芯片类型。SetReferencePoints 会先清原列表，再逐项添加，却捕获异常后不处理；部分添加失败仍可能继续后面的配置。',
        ['ws-map-config-set', 'ws-map-config-reference'],
      ),
      step(
        'read',
        '读取当前地图状态组装配置',
        'GetWaferMapDataConfig 拒绝 null 或空参考列表，取得首参考坐标、复制参考列表、芯片类型和策略当前起点，并把这些字段与跳步、路径、方向组成配置。GetReferencePoint1 捕获异常后统一抛“未设置参考点1物理位置”。',
        ['ws-map-ref-get', 'ws-map-config-read-a', 'ws-map-config-read-b'],
      ),
      step(
        'save',
        '只有部分 setter 显式请求保存',
        '最后路径与 JumpStep 的 setter 各调用 AsyncSaveFile；方向、起点、所选类型和 SetCurrentPoint 只调用对应接口，没有在这些 setter 内显式保存。类型字符串逐项 char.Parse，错误不会在该方法内吞掉。',
        ['ws-map-config-save', 'ws-map-config-direction', 'ws-map-config-types'],
      ),
    ],
  ),
];
