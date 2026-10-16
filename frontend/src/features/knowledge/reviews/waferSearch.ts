import { choices, flow, outcome, step } from './builders.ts';

export const waferSearchFlows = [
  choices(
    'wafer-search-dispatch',
    '搜索分派、换料标记与停止检查',
    'NextDie 按 Single、Nine、WaferMap、Box 调用不同方法；不存在统一经过同一 StopSearch 节点再发送许可的实现。',
    ['w-next-die', 'w-single-finish', 'w-publish'],
    [
      step(
        'dispatch',
        '四种模式分别调用',
        'Single 调 SearchSingle，Nine 调 SearchNine，WaferMap 调 SearchMapping，Box 调 SearchDieBox；未知模式抛异常。四种方法及共享视觉包装分别展开；PR 算法控制器和底层驱动仍需继续阅读。',
        ['w-next-die'],
      ),
      step(
        'flag',
        '地图的有效换料条件',
        '原始换料标记为 false 就 false；标记为 true 时，Single、Nine、Box 返回 true，WaferMap 还要求 pickingRefDieInfo 为空或计数为 0。地图缓存尚有参考芯片时，原始标记为 true 也不直接换料。',
        ['w-need-change', 'w-change-flags'],
      ),
      step(
        'init',
        'StartInit 与清换料标记不同',
        'StartInit 重置首次搜索、空白次数和 isNeedAheadChangeTablet，再依次调用地图、盒式、Single、Nine 四个初始化方法，没有按当前搜索模式择一。ReSetChangeCarrierSignal 另清原始换料和地图标记；不要把 StartInit 名称解释成已经清空全部状态。',
        ['w-block-init', 'w-change-flags'],
      ),
      step(
        'stop',
        'StopSearch 是检查点',
        'StopSearch 发现 IsStop 时，默认先请求顶针吹气、延时、关吹气并回安全位，再抛停止异常。这是调用处的检查，不是此方法为所有搜索路径建立了统一取消机制；NextDie=true 后供晶线程仍直接准备并发布许可。',
        ['w-stop-search', 'w-before-pick', 'w-publish'],
      ),
    ],
  ),
  choices(
    'wafer-single-search',
    'Single：下一位置、定位与换向',
    'SearchSingle 在定位跳过时循环找下一点；无点与提前结束走 false，正常定位后移到取晶中心并 true。',
    ['w-single-entry', 'w-single-finish'],
    [
      step(
        'position',
        '无下一点直接请求换料',
        '调用 GetNextPosition(isOffset) 后把 isOffset 清 false。位置为空或 isNeedAheadChangeTablet=true 时清提前换片标志、置原始换料标记、将槽设 Bad、经 UI 委托调用设备参数保存并 false；这个提前返回没有经过后面的 StopSearch。它与只负责换向的 AheadReachEnd 方法不同。',
        ['w-single-entry', 'ws-box-save', 'w-form-ui'],
      ),
      step(
        'vision',
        '标准定位与双点模式',
        '开启位置搜索且为 Standard 时，可按双点配置先定位 P1 再 P2；两次都不跳过时平均角度并移动到两中心的平均位置。某次 isSkip 为 true 时返回原当前点；单点配置则只调用 PR1。',
        ['w-single-entry', 'w-single-two', 'w-single-finish'],
      ),
      step(
        'loop',
        '检查停止，再决定跳过重搜',
        'MultipleSearch 与未知定位模式抛异常；关闭位置搜索也直接抛异常。受支持定位执行后 StopSearch，isSkip 为 true 回循环，false 才 MoveDieToPickCenter 并 true；共享 AnalyseDie 另处理框架、墨点、精度和视觉报警，不能把相机中心占位结果视为真实匹配。',
        ['w-single-finish'],
      ),
      step(
        'boundary',
        '蛇形移动有局部扫描上限',
        '首次以实际 G0 位置建立行列步距，并按配置跳行跳列及初始方向决定正负。后续按横向或纵向边界换向，在范围内返回下一点；边界扫描各自最多 retryTimes=50 次，不是所有视觉重试的统一 50 次上限。',
        [
          'w-single-position-first',
          'w-single-position-horizontal',
          'w-single-position-h-end',
          'w-single-position-vertical',
          'w-single-position-v-end',
          'w-single-position-limit',
        ],
      ),
    ],
  ),
  flow(
    'wafer-refresh-map',
    '取晶后的高度等待与地图更新',
    'RefreshMap 先按载具与离线条件检查焊头高度，再按搜索模式更新记录。isDebugMode 参数没有在方法内使用。',
    ['w-refresh-height', 'w-refresh-mode'],
    [
      step(
        'height',
        '非静态且在线才等焊头避让',
        '非 StaticWaffle 且非 Offline 时，用 GetPickPosZ 与实际焊头 Z 比较 RaiseDistance；未满足就 StopSearch、重读高度并继续。这个循环没有显式 Sleep 或本地超时。传 true 不会绕过它。',
        ['w-refresh-height'],
      ),
      step(
        'ejection',
        '晶圆配置请求顶针准备位',
        '高度条件满足且配置为 CarrierWithWaferConfig 时，重启并记录计时，请求 MoveEjectToReadyPosition，之后才进入搜索模式更新。此处没有据该调用另建立成功返回分支。',
        ['w-refresh-height'],
      ),
      step(
        'record',
        '地图、盒式、单点与九点分别更新',
        'WaferMap 记已取芯片并刷新状态；Box 将 CurrentIndex 设为当前槽索引加一、请求保存，再记取晶和刷新；Single 分支为空；Nine 调 ReMoveDieToWaferCameraCenter。不能统一描述为四种模式都更新同一地图字段。',
        ['w-refresh-mode'],
        [
          outcome(
            '保存与动作是独立边界',
            '盒式设备参数保存经 UI Invoke 调 Save，Save 加锁后调用 JSON 写入与备份 helper；地图 AsyncSaveFile 是另一接口。这里没有统一保存事务，停止或前序异常可能中断后续更新。',
            'w-refresh-mode',
            'w-stop-search',
            'ws-box-save',
            'w-form-ui',
            'ws-device-save',
            'ws-map-refresh',
          ),
        ],
      ),
    ],
  ),
];
