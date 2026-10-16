import { choices, outcome, step } from './builders.ts';

export const waferVisionFlows = [
  choices(
    'wafer-vision-entry',
    '视觉入口：空跑、模板、真空与避让',
    'MatchResult 的跳过入口与在线入口不同；等待超时日志不等于返回失败。',
    ['v-match-entry', 'v-match-wafer-wait', 'v-match-bond-wait'],
    [
      step(
        'skip',
        '离线或空跑直接给相机中心',
        'IsOffLineWork 或 IsDryCycle 时直接 true，并返回包含 CameraCenterPixel 的单元素数组，跳过模板、真空、等待和 PR 执行；中心值为 (1224,1024,0)。这不是实际采图成功。',
        ['v-match-entry', 'v-camera-center'],
      ),
      step(
        'prepare',
        '在线先查模板、处理对称补偿和真空',
        '模板不存在时提示并 false/null。对称模板先把 SymmetricCenter 转为偏移并加到当前实际位置；随后按 IsMatchWithVacuum 和三种料片配置开关对应真空，再等 DelayPhoto。没有在这里检查真空传感器的结果。',
        [
          'v-match-entry',
          'v-match-vacuum-on',
          'v-match-vacuum-off',
          'v-vacuum-rule',
          'v-match-missing',
        ],
      ),
      step(
        'wafer',
        '晶圆相机：超过八秒只记录并重启计时',
        'isCheckBondPos=true 且 SearchCamera=WaferCamera 时，等待 IsNotAllowWaferCameraAction 变 false；超过 8000 ms 只记日志并 Restart，原报警退出代码被注释。循环调用 StopSearch，没有本地 Sleep 或总体截止时间。',
        ['v-match-wafer-wait'],
      ),
      step(
        'bond',
        '其他相机：等到位标记，再检查实际位置',
        '其他相机路径循环 StopSearch，未收到 IsBondArriveSearchPos 就 Sleep(10)。标记为 true 后还检查 Bond 模组是否在配置位置；不在则抛异常，在才继续。isCheckBondPos=false 绕过这两种等待，但没有绕过模板、真空或 PR 调用。',
        ['v-match-bond-wait'],
      ),
    ],
  ),
  choices(
    'wafer-vision-result',
    '视觉返回：结果数量、失败清理与存图',
    'MatchResult 根据 PR 返回枚举转换 bool；没有给所有失败和异常设置同一个清理出口。',
    ['v-match-results', 'v-match-fail', 'v-match-missing'],
    [
      step(
        'success',
        'PR Success 后复制结果数组',
        'PR 返回 Success 后按 AlgResults.Count 创建数组，逐项强转 MatchResult，再 true。Block 没有另检查数量；PR Success 的展示分支本身也直接读取 AlgResults[0]。空列表或类型不符可能先抛异常，不能画成普通“未找到”false。',
        ['v-match-results', 'v-pr-post'],
      ),
      step(
        'image',
        '这里的 isSaveImg 是同步保存',
        'isSaveImg=true 时循环内创建 C://搜晶相机存图，并直接 Save 输出图片，文件名按秒生成。没有在 Block 这段创建后台任务或捕获保存异常；与 PR 内部的异步存原图或保存回调是不同路径。',
        ['v-match-results', 'v-pr-bitmap-save', 'v-pr-save-success'],
      ),
      step(
        'fail',
        'PR 非 Success 才进入这段失败处理',
        '非 Success 时仅 CarrierWithWaferConfig 显式关闭顶针台真空，两种 Waffle 的关闭语句被注释；对称模板再以当前实际位置减偏移请求移动，最后 false/null。这里不是方法级 finally，前序异常不保证执行这些调用。',
        ['v-match-fail'],
      ),
      step(
        'frame',
        '框架匹配是第二次调用',
        'AnalyseDie 先匹配芯片；启用框架时另调 DieFrameName，只有两次 bool 都成功才置 isOK=true，并用首结果的世界坐标差写 FrameOffset。禁用框架才清 FrameOffset，启用但失败的分支没有清它；两次首结果读取都没有本地数量检查。',
        ['v-analyse-frame', 'v-match-defaults'],
      ),
    ],
  ),
  choices(
    'wafer-vision-ink',
    '共享墨点检测：数量规则与跳过决定',
    'AnalyseDie 使用 BlobResult 的 bool 作跳过依据；它与 Nine 的值参数检测不是同一个实现。',
    ['v-analyse-ink', 'v-blob-entry', 'v-blob-number'],
    [
      step(
        'detect',
        '只在定位有效且非过桥点时检查',
        'isOK=true、IsInkDotSearch=true 且非过桥点才对首匹配结果调用 BlobResult。BlobResult 离线或空跑直接 false；在线查模板、设光、拍照、设定位姿并 DoWork(Bitmap)。模板不存在提示后 false，不能按名称解释为一定拒绝该芯片。',
        ['v-analyse-ink', 'v-blob-entry', 'v-blob-missing'],
      ),
      step(
        'number',
        '启用数量检查时，区间内返回 false',
        '算法成功且首结果 IsSuccess=true 时，若开启 IsCheckBlobNum，将首结果强转 BlobResult；Num 在包含上下边界的区间内返回 false，区间外才 true。未开数量检查则 true；首结果 IsSuccess=false 返回 false，PR 执行非 Success 则当墨点返回 true。',
        ['v-blob-number', 'v-blob-fail'],
        [
          outcome(
            '这里也依赖首结果和图片所有权',
            '没有检查 AlgResults 的数量或转换类型；PR 的 Bitmap 重载正常尾部释放传入图片，Block 又在各正常分支 Dispose，没有 finally 覆盖异常。这与 Nine 复用同一图片的风险需分别理解。',
            'v-blob-number',
            'v-blob-fail',
            'v-pr-bitmap-dispose',
          ),
        ],
      ),
      step(
        'choice',
        '自动跳过与人工三个选项',
        'BlobResult=true 时，IsBlobAutoSkip 直接设 isSkip；否则增加定位错误计数并弹框。OK 不跳过，Ignore 跳过，Abort 抛异常；跳过才增加 InkDot 和 Total、清空白计数并返回相机中心。未跳过仍可进入多次定位。',
        ['v-analyse-ink', 'v-analyse-ink-count'],
      ),
    ],
  ),
  choices(
    'wafer-vision-blank',
    '空晶：自动跳过、换向与视觉报警',
    '空白计数、过桥标记、提前换行功能和操作员返回枚举共同决定恢复入口。',
    ['v-analyse-blank', 'v-analyse-choice-a', 'v-analyse-choice-b'],
    [
      step(
        'auto',
        '未到阈值自动跳过',
        '定位或框架门失败后，若允许空晶自动跳过且 countBlankNum+1 小于上限，计数加一、isSkip=true，再返回相机中心。禁用自动跳过或达到上限才进入另一分支；过桥点在该分支清计数并跳过，不弹普通视觉报警。',
        ['v-analyse-blank', 'v-analyse-empty-end'],
      ),
      step(
        'ahead',
        'Single 的提前换向不是提前换片标记',
        '开启 IsAheadReachEnd 和空晶自动跳过且模式为 Single 时，在 countBlankNum+1 等于上限处调用 AheadReachEnd，计数加一后重新 AnalyseDie；之后仍小于上限乘三时继续跳过。AheadReachEnd 改方向、行列步距符号并移到相邻行或列，没有设置 isNeedAheadChangeTablet。',
        ['v-analyse-blank', 'v-single-ahead-a', 'v-single-ahead-b'],
      ),
      step(
        'retry',
        'OK 与 Cancel 重新定位',
        '进入 VisionAlarmFunc 后，OK 还以非 Box 且当前点越界为条件重新选点；表达式用 &，两侧都会求值。范围有效的 OK 和 Cancel 都回 RetryAnalyseDie，返回的人工 matchResult 没有在这个 switch 内直接用作定位结果。',
        ['v-analyse-choice-a', 'v-analyse-choice-b'],
      ),
      step(
        'change',
        'Retry 表示提前更换，Ignore 才普通跳过',
        'Abort 抛停止异常；Retry 设置 isSkip 和 isNeedAheadChangeTablet；Ignore 清空白计数并设 isSkip，再返回相机中心。提前换片标记在 SearchSingle 的下一轮入口消费并清除、设置换料和槽 Bad；地图与 Box 的搜索入口没有这个消费条件。',
        ['v-analyse-choice-b', 'w-single-entry', 'ws-map-search-a', 'ws-box-search-a'],
      ),
    ],
  ),
];
