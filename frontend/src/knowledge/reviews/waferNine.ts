import { choices, flow, outcome, step } from './builders.ts';

export const waferNineFlows = [
  choices(
    'wafer-nine-selection',
    'Nine：邻点优先级与备用行',
    '九点搜索按当前行、方向、空白计数和已标记邻点选择下一颗；结束有两种不同出口。',
    ['ws-nine-entry', 'ws-nine-buffer', 'ws-nine-catch'],
    [
      step(
        'first',
        '首次与向上邻点',
        '首次从九点中心位置开始，将 nextDie.Exist 清 false 后进入 AnalyseDies；后续若 UpDie 存在，先标记下一行，再选 UpDie，记录 turnUpRowNum 并将当前行号减一。',
        ['ws-nine-entry'],
      ),
      step(
        'priority',
        '空白阈值与方向决定候选顺序',
        '空白次数达到 RecurLimit−40（当前为 10）时，左到右依次检查 RightCenter、RightUp、Down、RightDown、LeftDown；右到左镜像检查 LeftCenter、LeftUp、Down、LeftDown、RightDown。跨向下行时按行号决定是否反向。阈值以下选择当前方向的水平邻点，再更新备用点。',
        [
          'ws-nine-threshold',
          'ws-nine-right-a',
          'ws-nine-right-b',
          'ws-nine-left-a',
          'ws-nine-left-b',
          'ws-nine-continue',
          'ws-nine-limit',
        ],
      ),
      step(
        'buffer',
        '没有邻点时依次消耗三个备用点',
        '依次检查 NextRowStartDie、tDie、BiggestRowStartDie；先清备用点的 Exist，再把它的值复制给 nextDie，恢复行号和方向、清空白计数并继续分析。三者均不存在时 StartInitNine 后返回 false；这条分支没有在这里设置换料标记或槽 Bad。',
        ['ws-nine-buffer', 'ws-nine-init', 'ws-nine-struct'],
      ),
      step(
        'end',
        'PickRefEnd 的 false 会标记换料',
        '捕获 PickRefEndException 时置原始换料标记、清 RecurCount、把当前槽设 Bad、调用设备参数 Save，然后 false；其他异常继续抛出。不能将所有 Nine=false 都画成已经请求换料。',
        ['ws-nine-catch'],
      ),
    ],
  ),
  choices(
    'wafer-nine-analysis',
    'Nine：已知芯片、重新识别与递归上限',
    'AnalyseDies 入口先检查停止，再区分范围与存在标记；缓存命中和重新识别的路径不同。',
    ['ws-nine-analyse-known', 'ws-nine-analyse-center', 'ws-nine-analyse-outside'],
    [
      step(
        'known',
        '范围内且 Exist=true 使用缓存',
        'StopSearch 后判断 nextDie 是否在范围内。已知存在时直接清递归计数、复制 currentDie 和 MatchResult，再 MoveDieToPickCenter 并 true；此分支没有在 AnalyseDies 内重新调用 MatchResult。取晶中心方法的 Nine 分支随后会对中并再次 CalculateDiesPosition。',
        ['ws-nine-analyse-known', 'ws-pick-center-a', 'ws-pick-center-b'],
      ),
      step(
        'center',
        '未知存在时重新计算九点',
        'CalculateDiesPosition 后若 CenterDie 存在，取中心；中心不在范围内就 NextDie 重搜，否则清递归计数、保存匹配结果、移动并 true。未找到中心时，RecurCount 严格大于 RecurLimit 才提示并抛 PickRefEnd；否则空白和递归计数各加一后递归 NextDie。',
        ['ws-nine-analyse-center', 'ws-nine-limit'],
      ),
      step(
        'outside',
        '越界也经过计数再重搜',
        'nextDie 越界时同样以 RecurCount > RecurLimit 判断结束；未超过就递增两种计数并 NextDie。RecurLimit 当前为 50，比较符是 >，成功路径还会清计数，不能写成整个搜索最多尝试 50 次。',
        ['ws-nine-analyse-outside', 'ws-nine-limit'],
      ),
      step(
        'reset',
        '初始化没有清全部计数',
        'StartInitNine 恢复左到右方向和两个行号，清三个备用点及 nextDie 的存在标记，重置九点坐标；没有在这个方法内重置 RecurCount。公共 StartInit 另重置首次搜索、空白计数和提前结束标志。',
        ['ws-nine-init', 'w-block-init'],
      ),
    ],
  ),
  flow(
    'wafer-nine-geometry',
    'Nine：理论网格、识别归位与墨点检测',
    '先建立九个理论位置，再把视觉结果分配到最近位置；当前墨点处理存在没有回写存在标记的边界。',
    ['ws-nine-reset-a', 'ws-nine-calculate-a', 'ws-nine-ink'],
    [
      step(
        'grid',
        '实际位置与行列步距构成九点',
        '先将九点 Exist 全清 false，以当前实际 G0 位置为中心，加减 CarrierRowSpacing 与 CarrierColSpacing 建立周围八点，再按搜索方向重排邻点含义。这段没有套用 Single 的跳行跳列倍数。',
        ['ws-nine-reset-a', 'ws-nine-reset-b', 'ws-nine-orientation-a', 'ws-nine-orientation-b'],
      ),
      step(
        'assign',
        '范围内的匹配结果按最近距离归位',
        'MatchResult 成功后，将每个结果转换为实际位置减视觉偏移；范围内的结果计算到九个理论位置的距离，按最小值归入对应格。代码按固定 if/else 顺序处理距离相等；没有在此加入距离上限或每格唯一性检查，后续结果可覆盖先前格。',
        ['ws-nine-calculate-a', 'ws-nine-calculate-b', 'ws-nine-calculate-c', 'ws-nine-distance'],
      ),
      step(
        'ink',
        '检测执行，但 Exist 修改没有回写',
        '启用 InkDot 时查找 PR 模板、设置灯光、拍照并对九点逐个调用 DetectInkDot；找不到模板抛异常。检测使用 MatchResult 设定位姿；结果为“墨点”或算法失败时把参数 Exist 清 false。SingleDieInfo 是 struct，而参数没有 ref/out 或返回写回，因此这次赋值只修改参数副本，不能说明缓存中的芯片已被过滤。',
        ['ws-nine-calculate-ink', 'ws-nine-ink', 'ws-nine-struct'],
        [
          outcome(
            '检测结果还有读取前提',
            '成功分支直接读取 results[0]，没有先检查数量。九点复用同一 Bitmap，而 PR 的 Bitmap 重载正常结束会释放传入图像，后续存在候选可能收到已释放对象；外层尾部 Dispose 没有 finally 包住全部检测。',
            'ws-nine-ink',
            'ws-nine-calculate-ink',
            'v-pr-bitmap-dispose',
          ),
        ],
      ),
    ],
  ),
  choices(
    'wafer-nine-markers',
    'Nine：下一行与转向备用点如何记录',
    '三个标记保存候选芯片的值、行号与方向，供后续无邻点路径选择；不是另一个独立生产线程。',
    ['ws-nine-mark-down', 'ws-nine-mark-t-a', 'ws-nine-mark-negative'],
    [
      step(
        'row',
        '下一行优先 Down，再看两个下角',
        'MarkNextRowDie 优先 Down；没有 Down 时，左到右优先 RightDown 再 LeftDown，右到左优先 LeftDown 再 RightDown。记录下一行号和相反行方向；BiggestRowStartDie 只在尚未存在或当前行满足它的行号条件时更新。',
        ['ws-nine-mark-down', 'ws-nine-mark-corner-a', 'ws-nine-mark-corner-b'],
      ),
      step(
        'turn',
        'MarkTDie 按行号与当前方向取下角',
        '左到右且不在 turnUpRowNum−1 时保存 RightDown，处在该行则保存 LeftDown 并反向；右到左镜像处理。候选不存在就不写这个备用点。',
        ['ws-nine-mark-t-a', 'ws-nine-mark-t-b'],
      ),
      step(
        'negative',
        '反向水平备用点',
        'MarkNagativeDirTDie 在左到右且右中点存在时保存右中点和右到左方向；右到左则保存左中点和左到右方向，行号维持当前行。备用点后续是否使用由 SearchNine 的候选优先级决定。',
        ['ws-nine-mark-negative', 'ws-nine-buffer'],
      ),
    ],
  ),
];
