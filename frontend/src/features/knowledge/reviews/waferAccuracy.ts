import { choices, step } from './builders.ts';

export const waferAccuracyFlows = [
  choices(
    'wafer-vision-accuracy',
    '多次定位：精度判断、移动与局部次数',
    'AnalyseDie 的多次定位门与 ToRequiredAccuracy 的局部循环不同；两层人工重试都可重新开始。',
    ['v-analyse-accuracy', 'v-accuracy-match', 'v-accuracy-limit'],
    [
      step(
        'gate',
        '仅有效定位且非过桥点进入',
        'IsTimesLocation=true 且非过桥点时调用 ToRequiredAccuracy；false 就弹 Ignore/Retry。Ignore 设 isSkip 并清空白计数，Retry 回 RetryTimesLocation 再调用；随后返回 helper 的 MatchResult，而非原首匹配结果。',
        ['v-analyse-accuracy'],
      ),
      step(
        'precision',
        '每次重新使用默认芯片模板',
        'helper 从 repeatSearchNum=1 开始，每轮调无参 MatchResult，即 DieMatchName，并将结果转世界偏移。首结果的角度绝对值、X/Y 偏移绝对值都 <= 对应目标才 true；没有把 AnalyseDie 的 matchTemplateName 传入 helper。',
        ['v-accuracy-match', 'v-match-defaults'],
      ),
      step(
        'limit',
        '达到局部次数时 false，未达到先对中',
        '精度不合格且 repeatSearchNum >= MaxLocationTimes 时 false/CameraCenterPixel，否则移动到相机中心，次数加一并以 <= MaxLocationTimes 继续。do/while 至少执行一次；视觉失败的 Retry 会重置次数，外层多次定位 Retry 也重新调用，因此不是全局重试上限。',
        ['v-accuracy-limit', 'v-accuracy-choice-a', 'v-accuracy-choice-b', 'v-analyse-accuracy'],
      ),
    ],
  ),
  choices(
    'wafer-vision-accuracy-alarm',
    '多次定位失败：文字与实际返回差异',
    '未找到芯片时弹出的四个选择并不都按界面文字安全回退。',
    ['v-accuracy-choice-a', 'v-accuracy-choice-b'],
    [
      step(
        'retry',
        'Retry 从次数 1 重新拍照',
        'Retry 跳到 RetryCommand，再设 repeatSearchNum=1 并重新 MatchResult；没有在此设置统一截止时间或直接观察机器停止，停止检查取决于后续调用是否进入其检查点。',
        ['v-accuracy-match', 'v-accuracy-choice-a', 'v-match-wafer-wait', 'v-match-bond-wait'],
      ),
      step(
        'ok',
        'OK 仍读取失败结果第 0 项',
        '界面文字是“忽略定位结果，直接取片”，注释说相机中心；实际却 return(true, result.matchResults[0])。MatchResult 的正常失败返回 false/null，因此这条 OK 会访问 null，不能画成已实现的相机中心回退。',
        ['v-accuracy-choice-a', 'v-accuracy-choice-b', 'v-match-fail', 'v-match-missing'],
      ),
      step(
        'skip',
        'Ignore 返回 false，外层还有选择',
        'Ignore 返回 false/CameraCenterPixel；AnalyseDie 接到 false 后还会弹“未达到目标精度”的 Ignore/Retry，第二次 Ignore 才置 isSkip，第二次 Retry 再做 helper。这里不能合并成一次点击就固定结束搜索。',
        ['v-accuracy-choice-b', 'v-analyse-accuracy'],
      ),
      step(
        'abort',
        'Abort 直接抛异常',
        'Abort 抛“拍照并定位到晶圆相机中心失败, 晶圆线程停止”异常；这个 helper 没有在抛出前直接调用设备 Stop 或统一回零。其余异常也未在这里转换为 false。',
        ['v-accuracy-choice-b'],
      ),
    ],
  ),
];
