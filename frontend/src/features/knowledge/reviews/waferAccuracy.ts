import { choices, step } from './builders.ts';

export const waferAccuracyFlows = [
  choices(
    'wafer-vision-accuracy',
    '多次定位：精度判断、移动与局部次数',
    '整颗芯片定位时的多次定位门槛，与精度循环内的局部重试是两层机制；两层的人工重试都可以重新开始。',
    ['v-analyse-accuracy', 'v-accuracy-match', 'v-accuracy-limit'],
    [
      step(
        'gate',
        '仅有效定位且非过桥点进入',
        '启用多次定位且当前点不是过桥点时，才进入精度循环；未启用就弹出忽略或重试的选择。选择忽略会置跳过标记并清空白计数，选择重试则回到定位重试入口重新进入精度循环；这里返回的是精度循环最后一次匹配的结果，不是最初那一拍的结果。',
        ['v-analyse-accuracy'],
      ),
      step(
        'precision',
        '每次重新使用默认芯片模板',
        '精度循环从重试次数 1 开始，每轮都用默认芯片模板重新拍照定位，并把结果换算成世界坐标偏移。只有第一个结果的角度和 X、Y 偏移绝对值都不超过各自目标值时，才算达到精度；整颗芯片定位所带的模板名称没有传进这个循环，两者用的模板可能不同。',
        ['v-accuracy-match', 'v-match-defaults'],
      ),
      step(
        'limit',
        '达到局部次数时判为失败，未达到先对中',
        '精度不合格且重试次数已达定位次数上限时，本轮按未达到精度结束，并给出相机中心坐标；未达上限就先移到相机中心，次数加一后继续，直到不超过上限。循环至少执行一次。视觉失败后的重试会把次数清零，外层的多次定位重试也会重新进入，所以这个上限不是全局重试次数上限。',
        ['v-accuracy-limit', 'v-accuracy-choice-a', 'v-accuracy-choice-b', 'v-analyse-accuracy'],
      ),
    ],
  ),
  choices(
    'wafer-vision-accuracy-alarm',
    '多次定位失败：文字与实际返回差异',
    '未找到芯片时弹出的四个选择，并不都按界面文字安全地结束本轮定位。',
    ['v-accuracy-choice-a', 'v-accuracy-choice-b'],
    [
      step(
        'retry',
        '重试从次数 1 重新拍照',
        '选择重试会跳过当前结果，把重试次数重置为 1，然后重新拍照定位；这里没有设定统一截止时间，也不直接观察设备是否已经停止。停止与否取决于后续调用有没有走到停止检查点。',
        ['v-accuracy-match', 'v-accuracy-choice-a', 'v-match-wafer-wait', 'v-match-bond-wait'],
      ),
      step(
        'ok',
        '确认仍读取失败结果第 1 项',
        '界面文字写的是“忽略定位结果，直接取片”，注释也说取相机中心；实际做法却是按成功返回结果列表的第 0 项。而正常找不到芯片时这份列表是空的，所以这条确认会读到空内容，不能当成已经实现的相机中心回退。',
        ['v-accuracy-choice-a', 'v-accuracy-choice-b', 'v-match-fail', 'v-match-missing'],
      ),
      step(
        'skip',
        '忽略时判为失败，外层还有选择',
        '选择忽略时，本轮按未达到精度结束并给出相机中心坐标；整颗芯片定位收到这个结果后，还会再弹一次“未达到目标精度”的忽略或重试选择。要到第二次选择忽略才置跳过标记，选择重试则再进一次精度循环，因此不能合并成点一次就固定结束搜索。',
        ['v-accuracy-choice-b', 'v-analyse-accuracy'],
      ),
      step(
        'abort',
        '中止直接抛异常',
        '选择中止会抛出“拍照并定位到晶圆相机中心失败，晶圆线程停止”的异常；这个精度循环在抛出前没有直接停止设备，也没有统一回零。其他异常同样没有在这里转成未达到精度的结果。',
        ['v-accuracy-choice-b'],
      ),
    ],
  ),
];
