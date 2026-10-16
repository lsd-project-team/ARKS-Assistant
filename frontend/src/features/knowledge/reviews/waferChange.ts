import { choices, outcome, step } from './builders.ts';

export const waferChangeFlows = [
  choices(
    'wafer-change-paths',
    '自动换料选择哪条路径',
    'ChangeTabletAuto 分为空跑、启用料仓升降、无料仓升降。返回 true 不能统一解释为已经完成一次机械换片。',
    ['w-change-dry', 'w-change-static', 'w-change-layer', 'w-change-manual-gate'],
    [
      step(
        'dry',
        'DryCycle 忽略后处理返回值',
        '空跑时若当前为 WaferTablet，就把槽状态设 Good 并 InitTabletInfo；随后调用 ChangeSucceedOperation，但不判断它的 bool 返回，直接 true。若该调用抛异常，仍向上传播。',
        ['w-change-dry'],
      ),
      step(
        'static',
        '料仓模式下的 StaticWaffle',
        '当前是 StaticAdapter 才检查是否存在所需芯片槽；索引小于 0 时进入静态换料向导。未满足这组条件时可以直接落到公共 Operation，并不保证先执行一次换片。',
        ['w-change-static', 'w-change-operation'],
      ),
      step(
        'layer',
        '非静态料仓路径先选层',
        '已有层先保存当前料片，再 JudgeNeedChipAtLayer。未找到时 OK 请求放回、移动至料仓标记位并提示补料，之后重新选层；Cancel 抛异常。当前适配器与目标名称一致可直接进 Operation。',
        ['w-change-layer', 'w-place-layer'],
      ),
      step(
        'same',
        '同层、异层与无料仓判断',
        '同层且 PreviousNeedChipName 为空时才检查传感器；无料清对象和层号、保存并重新选层，有料请求夹持及扩晶。异层请求放回再取出，此调用方未消费这两个调用的返回值。无料仓则根据现有料片名称、槽状态与传感器决定直接后处理或进入 ChangeMap。',
        ['w-change-operation', 'w-change-manual-gate'],
      ),
    ],
  ),
  choices(
    'wafer-change-retries',
    '换料后处理 false 的三个重试点',
    '不同标签代表不同恢复范围：公共 Operation 不重新选层，静态向导和无料仓 ChangeMap 会重新进入界面。',
    ['w-change-static', 'w-change-operation', 'w-change-map', 'w-change-manual-operation'],
    [
      step(
        'operation',
        '料仓公共 Operation',
        'ChangeSucceedOperation 为 false 时 goto Operation，直接再调用同一后处理；不是重新选层或重新机械取放。这个局部循环没有显式延时、次数上限或 Stop 条件。true 才返回 true。',
        ['w-change-operation'],
      ),
      step(
        'static',
        'RetryChangeStaticAdapter',
        '向导结果 Abort 返回 false，其他非 OK 结果重开向导；OK 后处理 false 也重开向导。后处理 true 才返回 true，异常没有在 ChangeTabletAuto 本层捕获。',
        ['w-change-static'],
      ),
      step(
        'manual',
        '无料仓的 ChangeMap',
        'StaticWaffle 显式 ShowDialog；其他载具构造 FrmChangeTabletTeach 后读取结果。Abort 返回 false，其他非 OK 回 ChangeMap；后处理 false 也回 ChangeMap，重新进行换料交互。',
        ['w-change-map', 'w-change-manual-operation'],
        [
          outcome(
            '构造函数会进入向导',
            'FrmChangeTabletTeach 构造函数调用 InitControl；经确认、移除旧料、保存 NullTablet 与新料传感器检查后，InitControl 自己 ShowDialog。不能只看调用者没有 ShowDialog 就断言没有展示界面。',
            'w-teach-constructor',
            'w-teach-entry',
            'w-teach-remove',
            'w-teach-show',
          ),
        ],
      ),
      step(
        'ui',
        '主窗体的 UI 委托是 Invoke',
        'MainForm 构造时把 PostAction 加到 SendUiAction；PostAction 调用 Invoke(action)。这里不是 Task.Run 式的后台换料通知；仍需考虑主窗体和委托是否已正确建立。',
        ['w-form-ui'],
      ),
    ],
  ),
];
