import { choices, step } from './builders.ts';

export const waferVisionMotionFlows = [
  choices(
    'wafer-vision-motion',
    '视觉偏移与相机中心移动的三个入口',
    '数组、单结果和移动包装的跳过规则不同；WithThread 名称不表示这段创建了后台线程。',
    ['v-world-array', 'v-world-single', 'v-center-move-array', 'v-center-move-named'],
    [
      step(
        'offset',
        '世界偏移与空结果',
        'MatchResultToWorld 数组重载在离线/空跑返回一个零向量；在线只有非 null 且非空才逐项转换，其他返回 null。单结果重载在离线/空跑返回零向量；GetOffsetWorld 在线用相机中心的世界点减结果世界点，离线则直接返回传入对象。',
        ['v-world-array', 'v-world-single', 'v-world-offset'],
      ),
      step(
        'thread',
        'WithThread 包装没有创建线程',
        '数组移动重载在离线、关闭位置搜索或空跑时直接 return；否则以 results[0] 和 WaferTableRealPosition 做 SelfPosToG0 并调用带 Search 的移动接口。无参重载在同样门控下 true，在线先默认匹配，成功才移动并 true、失败 false。两段都没有 Task/Thread 创建或数量检查。',
        ['v-center-move-array', 'v-center-move-default'],
      ),
      step(
        'named',
        '指定模板的移动入口门控不同',
        'MoveToCameraCenter(template, …) 仅离线/空跑提前 true，没有像 WithThread 那样检查 IsPositionSearch。在线调用指定模板及两个参数，成功转首匹配结果并请求 MoveWaferTableToG0Pos(point,true)，失败 false。不能互换三个包装的跳过语义。',
        ['v-center-move-named'],
      ),
    ],
  ),
  choices(
    'wafer-pick-compensation',
    '取晶中心：模式补偿、位置记忆与回相机',
    '视觉中心与取晶补偿分别计算，软件位置记忆还读取当前控制器坐标。',
    ['ws-pick-center-a', 'ws-pick-center-b', 'v-pick-offset'],
    [
      step(
        'mark',
        'Mark 中心与模式动作',
        'MoveDieToPickCenter 清空白计数、记录匹配角；双点用两中心平均值，单点用 GetDieMarkCenterG0Pos。后者只在离线返回零，空跑仍转换相机坐标。Box 非静态才移动；Nine 先对中再重算九点，其他非 Box 分支保存位置后移动到中心加补偿。',
        ['ws-pick-center-a', 'ws-pick-center-b', 'v-mark-center'],
      ),
      step(
        'offset',
        'GetPickOffset1 不同于 GetPickOffset',
        'GetPickOffset1 离线为零；Box 双点保持零、单点为 RelativeDistanceMarkWithCenter−CenterOffset；非 Box 还加顶针与晶圆相机中心偏差。另一个 GetPickOffset 的 Box 为零、非 Box 只返回该顶针偏差，没有前两项。',
        ['v-pick-offset', 'v-pick-offset-basic'],
      ),
      step(
        'memory',
        '传入位置没有被用于保存',
        'SetCurrentPosition(dieMarkCenterG0Pos) 没有读取参数，而是强转当前料片为 WaferTablet，保存控制器 WaferTableG0Pos 并调用参数保存；SetSingleSearchDirection 仅在晶圆配置时写当前方向并保存。它们没有统一事务或本地异常回滚。',
        ['v-single-position-save', 'ws-box-save'],
      ),
      step(
        'return',
        'Nine 取后减补偿回相机位置',
        'RefreshMap 的 Nine 分支调 ReMoveDieToWaferCameraCenter，直接以实际 G0 位置减 GetPickOffset1 请求移动；不是在这个方法重新识别芯片。另一个带 visionPos 的 AnalyseDie 重载也没有使用该参数，只转调普通重载。',
        ['w-refresh-mode', 'v-camera-return', 'v-analyse-overload'],
      ),
    ],
  ),
];
