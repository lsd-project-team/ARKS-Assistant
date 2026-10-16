import { choices, outcome, step } from './builders.ts';

export const waferPreparationFlows = [
  choices(
    'wafer-prepare-carrier',
    '换料后处理：料片类型与运行模式',
    'ChangeSucceedOperation 每次先 Block.StartInit，再按料片及运行模式处理；它既可能返回 false，也可能抛异常。',
    ['w-prepare-entry', 'w-prepare-adapter', 'w-prepare-end'],
    [
      step(
        'static',
        '静态适配器选择可用槽',
        'StaticWaffle 下，当前适配器需存在于仓库，再遍历 MaxUseWaffle 范围；配置存在、名称等于需求且槽 Good 时设置当前配置及槽状态，清换料标记并 true。未找到会走末尾提示和 false。',
        ['w-prepare-static', 'w-prepare-final'],
      ),
      step(
        'wafer',
        '晶圆料片先准备公共环境',
        'WaferTablet 需名称存在、名称等于需求且槽 Good；随后请求晶圆相机工作位，设置当前载具并 ChangeEjection，再判断自动、手动及搜索模式。不能把这些调用的存在写成运动或换顶针已成功。',
        ['w-prepare-entry'],
      ),
      step(
        'adapter',
        '普通适配器与未支持模式',
        '普通 Adapter 遍历可用槽后，请求相机工作位、设置配置和槽、清换料标记并 true。晶圆 ManualAtStart 当前直接抛“先手动模式待开发”，其他不支持的运行或搜索模式也抛异常。',
        ['w-prepare-adapter', 'w-prepare-end'],
      ),
    ],
  ),
  choices(
    'wafer-automatic-map',
    '自动地图：参考点定位与初始化',
    'Automatic + WaferMap 下，已经准备与尚未准备走两条路径。首次参考点匹配失败会重复搜索或要求操作员重新教点。',
    ['w-auto-map', 'w-auto-map-teach'],
    [
      step(
        'load',
        '未准备时加载地图并匹配',
        '未准备时 LoadMap(name,true)，移动到参考点，复制中心和临时位置，在 Retry 中递增次数并 MatchResult。LoadMap 通过 UI 委托执行，当前实现先删除已有目标文件，再查找复制源并打开；不要把它理解成无副作用的读取。',
        ['w-auto-map', 'w-load-map', 'w-form-ui'],
      ),
      step(
        'match',
        '匹配成功后保存与启动寻路',
        '按 IsAroundLocate 选择参考中心，将 ReferencePosition 写入当前载具配置，移到该点并保存 CarrierConfigRepository，再设 P1、查参考芯片、移到起点、StartAsyncSeekingPath、InitMapInfo 并清换料标记。启动异步寻路不证明寻路此时已完成。',
        ['w-auto-map'],
      ),
      step(
        'confirm',
        '起点确认晚于提交',
        '启用起点确认时，OK 继续，Abort 抛异常；此前已经保存参数并清标记，没有这里的取消回滚。已经准备的路径直接清标记、清 IsNewTablet 并保存，不重复上述首次初始化。',
        ['w-auto-map', 'w-auto-map-teach'],
      ),
      step(
        'retry',
        '周边搜索与操作员教点',
        '启用周边定位时按次数尝试中心的 Y−、Y+、X−、X+，再回中心并打开位置教点；OK 更新中心，Abort 抛异常，之后回 Retry。未启用周边定位也通过教点交互回 Retry。',
        ['w-auto-map-around', 'w-auto-map-teach'],
      ),
    ],
  ),
  choices(
    'wafer-prepare-search-modes',
    '单点、九点与手动地图准备',
    '这些是互斥的模式比较。范围检查、是否新料、匹配结果和 IsNeedChange 决定清标记或继续教点。',
    ['w-auto-single', 'w-auto-nine', 'w-manual-map', 'w-manual-single', 'w-manual-nine'],
    [
      step(
        'single',
        '自动 Single 只按新料触发教点',
        '越界先 InitTabletInfo 并保存，再到当前点；DryCycle 清换料标记。普通路径只在 IsNewTablet 时进入位置教点，不以本处匹配失败触发；NeedChange 下 Abort 抛异常，其他结果重开，完成则清新料并保存。旧料直接清标记。',
        ['w-auto-single'],
      ),
      step(
        'nine',
        '自动 Nine 同时检查匹配',
        '越界初始化并保存，移动当前点后 MatchResult；新料或匹配失败才进入教点。NeedChange 下 Abort 抛异常，其他重开；教点完成清新料并保存，旧料且匹配成功直接清标记。',
        ['w-auto-nine'],
      ),
      step(
        'map',
        '手动 WaferMap',
        '越界初始化后移动当前点，尚未准备则进入 FrmChangeWaferMapTeach；仍需换料时 Abort 抛异常，否则回 ChangeMap。准备完成清新料并保存；已准备直接清换料标记、清新料并保存。',
        ['w-manual-map'],
      ),
      step(
        'manual',
        '手动 Single 与 Nine',
        '两种模式越界都先初始化、保存和移到当前点，随后进入位置教点。是否重开由 IsNeedChange 判断，NeedChange 且 Abort 抛异常；完成时清 IsNewTablet 并保存。不能把对话框 OK 单独当作全部地图准备完成。',
        ['w-manual-single', 'w-manual-nine'],
        [
          outcome(
            '后处理返回范围',
            '晶圆所支持模式结束后返回 true，但不支持的模式先抛异常。末尾未找到合适料片时提示“晶圆线程将中止”并 false；这个 bool 的消费方式依赖具体换料路径。',
            'w-prepare-end',
            'w-prepare-final',
            'w-change-dry',
            'w-change-operation',
            'w-change-manual-operation',
          ),
        ],
      ),
    ],
  ),
];
