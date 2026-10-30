import type { SourceGuide } from '../sourceGuides';
import { choices, outcome, step } from './builders.ts';

export const publicVisionGuide: SourceGuide = {
  id: 'public-vision-review',
  topic: 'public-vision',
  diagrams: ['public-vision-process'],
  initialFlows: { 'public-vision': 'pv-acquisition', 'public-vision-process': 'pv-acquisition' },
  title: '建议阅读顺序',
  flows: [
    choices(
      'pv-templates',
      '模板与初始化',
      '配方引用收集、方案载入与初始化标志分别判断，不能只看成功标志。',
      ['pv-collect', 'pv-init', 'pv-prinit'],
      [
        step(
          'names',
          '从当前配置收集模板名',
          '收集当前料片、顶针、焊后检测、吸嘴及产品定位模板，再加入 IPTCenterCircle。产品定位按普通或异形配置展开；LocateConfig.GetPrNames 目前只收 P1–P3，未收 P4，不能当作全部视觉引用的完整检查。',
          ['pv-collect', 'pv-locate-names'],
        ),
        step(
          'load',
          '后台关闭旧方案再加载',
          'InitPR 返回后台 Task，先关闭旧方案、创建新方案，再逐名查找并初始化算法。模板仓库为空时尝试从备份恢复配置；名称为空跳过，未找到只记录日志。',
          ['pv-init'],
        ),
        step(
          'algorithm',
          '产品方案与默认方案',
          'InitVmProcedure 优先读取产品同名 .prc，不存在则用算法类型的默认 .prc。方法内部捕获初始化异常并记日志，没有把这类异常重新抛到 InitPR。',
          ['pv-prinit'],
        ),
        step(
          'ready',
          '成功标志的实际含义',
          'InitPR 末尾置 PrInitSuccess=true，但找到模板不等于算法已有效初始化，入口也未先复位旧标志。外层异常会弹窗、记日志并重新抛出；LoadDispensePr 当前实现全被注释，不能画成已复制出 S1 专用模板。',
          ['pv-init', 'pv-prinit', 'pv-copy'],
        ),
      ],
    ),
    choices(
      'pv-acquisition',
      '采图与定位',
      '物料域准备目标与处理失败，控制器安排移动和硬件，PR 实体执行采图与算法。',
      ['pv-s1-point', 'pv-s2-point', 'pv-prwork'],
      [
        step(
          'overview',
          '一个定位点怎样走完',
          '按当前物料与 P1–P4 类型取得位置、模板和对焦配置，转换成工位拍照目标。自动定位得到结果后换算并存入当前点；结果为空时转人工处理，具体返回另见失败处理。',
          ['pv-point-info', 'pv-s1-point', 'pv-s2-point', 'pv-save-info'],
        ),
        step(
          'hardware',
          '移动与设置灯光并行',
          'S1/S2 有目标点时，先启动灯光任务并移动，随后等待灯光任务。S1 使用点胶灯标定映射，S2 使用 Bond 硬件；可选对焦在这之后执行。PRHardware 绑定相机、XYZ 和灯名。',
          ['pv-s1-camera', 'pv-s2-camera', 'pv-setlight'],
          [
            outcome(
              '两种设置接口',
              'SetLight 设置曝光、增益或伽马失败会抛异常；DoWork 的 isSetLight 分支则对设置失败记日志后继续。不能把它们视为同一个失败契约。',
              'pv-setlight',
              'pv-prwork',
            ),
          ],
        ),
        step(
          'capture',
          '采图后执行算法',
          'DoWork 在锁内执行，按开关设灯和相机参数。Excute 采灰度图，空图记日志并保持 None；非空则复制图、设置算法输入、FindModel 并取 AlgResults。闪光模式可异步关灯，发起关灯不表示已等待完成。',
          ['pv-prwork', 'pv-prcapture'],
          [
            outcome(
              '图像与算法边界',
              '算法执行、保存结果图片和向界面发送图片是不同环节。源码有保存与界面广播分支，不能因公共服务里的旧存图调用被注释，就认为底层完全不存图。',
              'pv-prwork',
              'pv-prcapture',
            ),
          ],
        ),
        step(
          'modes',
          '空跑与自动重试',
          'DryCycle 返回新建匹配结果，不执行本次真实定位，但移动、灯光或对焦可能此前已发生。Bond 相机按 VisionRetryTimesLimit 重试，每次等待 DownLookVisionDelay；S1 单次调用没有同一自动重试循环。',
          ['pv-s1-camera', 'pv-s2-camera'],
          [
            outcome(
              '周围搜索',
              '启用 IsAroundLocate 且首次结果为空时，物料域按 +X、−X、+Y、−Y 尝试周围拍照位，找到结果即停止。这与相机内部重试次数是两层机制。',
              'pv-s1-point',
              'pv-s2-point',
            ),
          ],
        ),
      ],
    ),
    choices(
      'pv-results',
      '结果与距离检查',
      '定位坐标、缺陷结果和两点距离检查各有自己的成功含义。',
      ['pv-service', 'pv-defect', 'pv-distance', 'pv-backside'],
      [
        step(
          'match',
          '普通定位返回一个结果',
          'VisionService.Vision 找不到模板时报警并返回 null；DoWork 非 Success 也返回 null。成功的 MatchResult 只复制中心 X/Y 和角度，其他算法结果直接返回，不统一附带图像或完整原结果属性。',
          ['pv-service'],
        ),
        step(
          'defect',
          '缺陷返回列表后再判定',
          'VisionDefect 在执行成功时返回 AlgResults，调用者继续解释每个结果。它在 null 判断前就写 IsDefectPR=true，缺失模板可能先触发空引用；不能画成必然经过“未找到模板”的报警返回。',
          ['pv-defect'],
        ),
        step(
          'backside',
          '崩边检测的 true 表示什么',
          'BacksideCrackDetect 用已有匹配值设置位置修正后执行模板：首结果 IsSuccess=true 表示检出崩边；执行不成功也按崩边返回 true，正常未检出返回 false。离线/空跑直接 false，缺模板抛异常。',
          ['pv-backside'],
        ),
        step(
          'distance',
          '比较两点之间的距离',
          'DistanceCheck 比较示教与结果的两点距离。未启用直接 OK；超容差时返回“手动对点、忽略、跳过、停止”对应的 Retry、Ignore、None、Abort。只有通过路径写两组距离记录。',
          ['pv-distance'],
        ),
        step(
          'distance-branches',
          'S1 与 S2 的跳过不同',
          'S1 的 Retry 回首点并转人工定位，None 禁用对象后仍更新坐标；S2 的 Retry 重识别两点再检查，None 禁用后直接 true，不执行该次坐标更新。两者 Abort 都停机返回，Ignore 继续各自更新路径。',
          ['pc-s1-locate', 'pv-s2-locate'],
        ),
      ],
    ),
    choices(
      'pv-objects',
      '产品各层怎样调用',
      '四层产品复用物料定位方法，但动作门控、标志与返回值仍有区别。',
      [
        'pv-s1-entry-tu',
        'pv-s1-entry-sub',
        'pv-s1-entry-module',
        'pv-s1-entry-bp',
        'pv-s2-entry-tu',
        'pv-s2-entry-sub',
        'pv-s2-entry-module',
        'pv-s2-entry-bp',
      ],
      [
        step(
          'entries',
          '四层对象进入同一物料接口',
          'S1 的载具、基板、模块和焊点动作分别把当前对象交给 System1MatterVision；S2 四层动作交给 System2ObjectVision，再转 System2MatterVision。每层读取自己的定位配置，不能只定位载具就视为全部层级都已定位。',
          [
            'pv-s1-entry-tu',
            'pv-s1-entry-sub',
            'pv-s1-entry-module',
            'pv-s1-entry-bp',
            'pv-s2-entry-tu',
            'pv-s2-entry-sub',
            'pv-s2-entry-module',
            'pv-s2-entry-bp',
            'pv-s2-wrapper',
          ],
        ),
        step(
          'gates',
          '开关、状态与已定位门控',
          'S2 四层 IsDoWork 检查定位开启、加工状态和 IsVisioned；载具、基板和模块另看下层工艺是否完成，基板还要求 EntityState.Process。载具 Divide 跳过整体定位；S1 相对焊点可直接跳过对应点胶定位。',
          [
            'pv-s2-entry-tu',
            'pv-s2-entry-sub',
            'pv-s2-entry-module',
            'pv-s2-entry-bp',
            'pv-s1-entry-bp',
          ],
        ),
        step(
          'returns',
          '动作成功不等于识别成功',
          '上述动作直接调用内部 bool 方法而未检查返回值时，仍可走到末尾 Success。S2 离线会置 IsVisioned 后直接返回，S1 离线分支置标志后没有统一直接返回；域内关闭定位又会直接置标志并 true。',
          [
            'pv-s1-entry-tu',
            'pv-s1-entry-sub',
            'pv-s1-entry-module',
            'pv-s1-entry-bp',
            'pv-s2-entry-tu',
            'pv-s2-entry-sub',
            'pv-s2-entry-module',
            'pv-s2-entry-bp',
            'pv-s2-locate',
            'pc-s1-locate',
          ],
        ),
        step(
          'save',
          '当前点与整个对象分别完成',
          '匹配结果经工位转换得到 G0 点和局部点，选择 P1–P4 结果对象。SaveInfo 写匹配值、点位和成功/更新标志；物料域达到设定点数后才更新产品坐标。坐标计算与限值规则统一见产品坐标专题。',
          ['pv-point-info', 'pv-s1-point', 'pv-s2-point', 'pv-save-info', 'pc-update'],
        ),
      ],
    ),
    choices(
      'pv-identity',
      '身份识别与墨点',
      '身份识别、占位墨点动作和 Nine 的实际墨点检测是三条不同路径。',
      ['pv-id-s1', 'pv-id-s2', 'pv-ink-empty', 'pv-ink-nine'],
      [
        step(
          'identity',
          '身份识别写入编码',
          'S1/S2 关闭识别时直接 Success；启用后按身份配置执行 CodeResult 识别。正常或人工成功后写 IsIdentity 和 IdentityCode；Ignore 禁用对象却返回 Success，Abort 停机返回 Abort，不能把所有 Success 都理解成已取得编码。',
          ['pv-id-s1', 'pv-id-s2'],
        ),
        step(
          'placeholder',
          '墨点动作节点尚未执行检测',
          'CheckInkDotActionNode.DoWork 当前直接返回 Success，后面的墨点采图与判断都在注释中。该节点的成功不证明进行过墨点识别。',
          ['pv-ink-empty'],
        ),
        step(
          'nine',
          'Nine 使用真实图像逐颗检测',
          'Nine 搜索启用墨点时，设灯采一张图，再处理九个候选中 Exist=true 的晶粒。按该颗匹配值设置修正、运行 DoWork(bmp)；检出墨点或执行不成功都置 Exist=false，模板缺失抛异常。',
          ['pv-ink-nine', 'pv-pr-bitmap'],
        ),
      ],
    ),
    choices(
      'pv-alarm',
      '失败处理与修改模板',
      '对话按钮只返回处理结果，物料、身份和其他检测调用者再决定后续动作。',
      ['pv-ui-alarm', 'pv-alarm-ok', 'pv-alarm-edit', 'pv-alarm-buttons'],
      [
        step(
          'dialog',
          '报警串行回传给调用者',
          'VisionAlarm 在 UiLock 内同步打开窗体，读取 DialogResult 与 BaseAlgResult，随后保存报警记录并复位报警。窗体后台可以持续采图或执行模板预览；预览中的结果不等于调用者已接受。',
          ['pv-ui-alarm', 'pv-alarm-preview'],
        ),
        step(
          'ok',
          '普通 OK 会再次尝试',
          '点击 OK 先禁止预览并等待当前工作结束；普通分支重新 DoWork，失败则留在对话中允许继续尝试，成功复制结果后返回 OK。无模板、双模板、晶圆线程和胶检可直接 OK，不统一产生新的匹配结果。',
          ['pv-alarm-ok'],
        ),
        step(
          'buttons',
          '跳过、停止与重试',
          'Skip 返回 Ignore；Abort 主动 Stop 并返回 Abort；ReDispense 返回 Retry，按钮可能显示补胶、下一颗或提前换料，含义取决于当前视觉场景。物料定位的 Ignore 会禁用并 false，身份识别却可禁用并 Success。',
          [
            'pv-alarm-buttons',
            'pv-alarm-load',
            'pv-s1-point',
            'pv-s2-point',
            'pv-id-s1',
            'pv-id-s2',
          ],
        ),
        step(
          'edit',
          '修改模板后的保存与继续',
          '编辑先禁止预览、等待完成并 Pause，再按硬件打开模板编辑器。点胶灯值进出时映射与反映射，随后保存模板仓库、Continue 并允许预览；此入口没有统一 finally 保证异常后恢复。',
          ['pv-alarm-edit'],
          [
            outcome(
              '其他包装入口',
              'AdjustAction 有自己的异常捕获，并在末尾重新读取 PREntity.AlgResult。不能把它与物料定位、缺陷接口和报警对话的回传值合成一个通用返回契约。',
              'pv-adjust',
            ),
          ],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖模板初始化、相机硬件与采图、普通/缺陷结果、产品四层调用、身份与墨点、人工处理。算法模块和驱动依赖现场 SDK 与配置；本专题没有运行实际视觉或轴运动。G0 转换和产品坐标写回分别链接到公共专题。',
      refs: ['pv-init', 'pv-prwork', 'pv-service', 'pv-s2-wrapper', 'pv-alarm-ok'],
    },
  ],
};
