import type { SourceGuide } from '../sourceGuides';
import { choices, outcome, step } from './builders.ts';

export const toolCalibrationGuide: SourceGuide = {
  id: 'tool-calibration-source-review',
  topic: 'tool-calibration',
  diagrams: ['tool-calibration-process'],
  title: '建议阅读顺序',
  flows: [
    choices(
      'tc-entry',
      '入口与组合状态',
      '先区分正在使用的独立入口，以及尚未启用的一键组合。',
      ['tc-main-entry', 'tc-page-init', 'tc-page-combined'],
      [
        step(
          'overview',
          '三个独立校准入口',
          '主页面“三点一线”菜单打开校准窗口；当前分别使用吸嘴、单顶针和取片偏移按钮。它们有不同的准备、采样与保存路径，不能理解为点击任意一个就执行全部校准。',
          ['tc-main-entry', 'tc-page-init', 'tc-page-nozzle', 'tc-page-ejection', 'tc-page-pick'],
        ),
        step(
          'combined',
          '一键组合当前未启用',
          '一键全部校准的按钮已隐藏并禁用，原有的处理过程也整体停用，只作为历史记录保留。历史上它是顶针、吸嘴、准备取片、取片偏移这样的顺序；这里只说明它当前的停用状态，不把这条历史顺序当作可以执行的流程。',
          ['tc-page-init', 'tc-page-combined'],
        ),
        step(
          'selection',
          '选择配置与当前硬件分开',
          '列表来自针库、吸嘴架和物料配置，默认吸嘴使用当前工具名，物料选择会同步顶针名称。列表文本代表所选配置，不能单凭选择就推定硬件已经换到对应吸嘴或顶针。',
          ['tc-page-init', 'tc-page-selection', 'tc-nozzle-prepare', 'tc-ejection-prepare'],
        ),
      ],
    ),
    choices(
      'tc-center',
      '吸嘴中心示教',
      '圆嘴、矩形嘴与重新制作中心 PR 是不同的示教路径。',
      ['tc-center-steps', 'tc-center-finish', 'tc-center-search', 'tc-nozzle-pr'],
      [
        step(
          'two-positions',
          '两次对齐建立中心',
          '第一步保存当前 G0 的上视位置、对齐角和机械 XY，再按当前转角的正负旋转 180°。第二步圆嘴用两次机械 XY 之差的一半写吸嘴偏移；矩形嘴写的是角点偏移，两点的均值连同当前 Z 转为旋转中心。',
          ['tc-center-steps'],
        ),
        step(
          'search',
          '辅助搜索有移动范围门控',
          '辅助搜索按形状使用圆或矩形模板，没有结果时可以重试或取消。结果换算成机械目标后，X 或 Y 任一方向的差值超过 3mm 就拒绝移动；模板编辑另有单独的保存动作。',
          ['tc-center-search'],
        ),
        step(
          'states',
          '状态与中心 PR 分别建立',
          '中心示教完成后会记下工具已对齐；矩形嘴还会使几何示教失效。自动校准的准备环节检查高度、中心、几何三项配置状态。重新制作中心 PR 的一步窗口会换嘴、移动和定位，成功时更新上视中心；它没有替代这三项初始示教。',
          ['tc-center-steps', 'tc-nozzle-states', 'tc-nozzle-pr-gate', 'tc-nozzle-pr'],
        ),
      ],
    ),
    choices(
      'tc-height',
      '吸嘴高度示教',
      '高度偏移相对 BMC 参考计算，测量结果与外层完成标记分别确认。',
      ['tc-height-move', 'tc-height-measure', 'tc-height-finish'],
      [
        step(
          'prepare',
          '换嘴后到 BMC 上方',
          '非离线时先请求换成所选吸嘴，失败就退出初始化移动；成功后移动到 BMC 搜索机械位置的 Z+8mm 处。界面说明写的是约 5mm，图谱按实际执行的 8mm 说明。',
          ['tc-height-move'],
        ),
        step(
          'methods',
          '手动、TD 与真空三种来源',
          '手动方式用当前 Z 减 BMC 参考值。TD 或真空方式使用测高功能，只有测量结果为成功才更新“测得高度减 BMC 参考”；其他结果保留原有偏移，不会自动写成新的高度。',
          ['tc-height-measure'],
        ),
        step(
          'service',
          '重测与取消保留实际结果',
          '测高以当前 Z 为搜索起点向负方向搜索，超时设为 10 秒，每次执行前停留 1 秒。失败可以重测；取消后按该次未成功的结果返回。测高装置内部如何反馈，仍取决于它所在的驱动库。',
          ['tc-height-service'],
        ),
        step(
          'completion',
          '完成标记不能证明测量成功',
          '窗口上的“完成”在测量处理结束后，仍会把吸嘴高度标记为可用、执行保存并给出成功结果；离线提前退出、手动轴缺失时取消，或自动测高失败，也可能走到这一段。因此要把高度值是否已更新，与窗口是否显示完成分开看。',
          ['tc-height-measure', 'tc-height-finish'],
        ),
      ],
    ),
    choices(
      'tc-nozzle',
      '吸嘴自动校准',
      '当前自动校准只执行 XY 中心校准，其中的自动测高环节没有启用。',
      ['tc-nozzle-prepare', 'tc-nozzle-auto'],
      [
        step(
          'prepare',
          '准备检查与重教取消',
          '先检查吸嘴存在及三项示教状态，随后可选重做 PR，最后检查 PR 和上视中心。重教被取消时按未通过处理；重教后如果被拒绝开始，会先到安全位。准备环节本身不一定会换嘴，换嘴发生在进入重教窗口等实际执行的位置。',
          ['tc-nozzle-prepare', 'tc-nozzle-pr-gate'],
        ),
        step(
          'first',
          '第一次定位立即写中心',
          '按吸嘴对齐角换算转角，在保存的上视位置定位；失败按异常处理，成功则把像素结果换算成 G0 坐标，并立即更新吸嘴的上视中心。这次更新发生在第二次定位之前。',
          ['tc-nozzle-auto'],
        ),
        step(
          'second',
          '旋转后修正 XY 再定位',
          '按当前角度的正负旋转 180°，用已有的吸嘴旋转偏移修正机械 XY。第二次共同视觉定位传入空位置，实际使用移动后得到的实位；这里虽然带有 Z 方向安全的标记，空位置分支也不会因此再补一次拍照位移动。',
          ['tc-nozzle-auto', 'tc-common-vision'],
        ),
        step(
          'write',
          '两次 G0 结果半差写偏移',
          '第二次定位成功后，用两次 G0 结果之差的一半更新吸嘴偏移的 X、Y，然后到安全位并保存。自动测高环节当前整体停用；第二次失败不会撤回第一次写入的中心，也不会执行这段成功后的收尾保存。',
          ['tc-nozzle-auto'],
        ),
      ],
    ),
    choices(
      'tc-ejection',
      '单顶针与重教',
      '晶圆相机与 Bond 相机分别采集；重教后不会再自动接一遍同样校准。',
      ['tc-ejection-prepare', 'tc-ejection-auto', 'tc-ejection-teach'],
      [
        step(
          'prepare',
          '检查配置并整理工作区域',
          '先排除翻转硬件配 Bond 相机的组合，检查槽位、示教、PR 和校准位置；归还吸嘴后关真空、归还顶针、晶圆台到准备位、检查料片，并把顶针台移到工作位。这一准备没有明确切换到所选顶针槽。',
          ['tc-ejection-prepare'],
        ),
        step(
          'wafer',
          '晶圆相机写世界结果首点',
          '自动校准先使 Bond 到安全位，再把顶针 Z 与晶圆相机 Z 移到各自的校准位置。匹配成功后取世界坐标结果的首点，写入顶针中心相对相机的偏差；匹配失败按异常处理。',
          ['tc-ejection-auto'],
        ),
        step(
          'bond',
          'Bond 相机使用另一种转换',
          'Bond 相机分支另外请求归还吸嘴，移动顶针校准 Z 并做共同视觉定位；以机械原点 (0,0) 和 Bond 相机标定求出 XY，写入偏差并把 Z 置零。不能把它与晶圆相机的首点换算当成同一套算法。',
          ['tc-ejection-auto'],
        ),
        step(
          'teach',
          '重教先在加载时准备',
          '选择重做模板会打开一步示教窗口，返回后就直接结束本次按钮处理。当前窗口的打开提示不再做判断，始终允许打开；真正的准备动作在窗口加载时执行，会按相机选择去安全位或归还吸嘴，再整理晶圆台、检查料片并切换顶针。',
          ['tc-page-ejection', 'tc-ejection-teach-gate', 'tc-ejection-teach-load'],
        ),
        step(
          'teach-result',
          '重教同时记录高度和状态',
          '晶圆相机分支取世界坐标结果；Bond 相机分支先把像素换算成 G0 坐标，再减去当前 G0 位置求偏差。成功后记录相机拍照位、相机 Z、顶针 Z 和 PR 示教状态，归还顶针并给出成功结果。手动换针按槽名查找并切换当前序号；槽位按同名关联顶针配置。',
          ['tc-ejection-teach', 'tc-ejection-change', 'tc-ejection-slot'],
        ),
      ],
    ),
    choices(
      'tc-batch',
      '全部顶针旧接口',
      '保留现有能力与失效边界，不能把旧的整组校准入口说成当前可用的一键成功流程。',
      ['tc-ejection-list', 'tc-batch-prepare', 'tc-batch-old'],
      [
        step(
          'list',
          '列表来自当前针库',
          '列表按当前针库、以及顶针配置是否存在来收集槽位，再做筛选和去重；槽位按自己的名称查找同名顶针配置。整组准备的环节逐项检查示教状态、PR 和校准位置，再整理工作区域；准备是否完成，与整组是否执行完成分别判断。',
          ['tc-ejection-list', 'tc-batch-prepare', 'tc-ejection-slot'],
        ),
        step(
          'loop',
          '末轮仍访问下一项',
          '旧的整组校准已被标记为废弃，但仍从列表第一项开始，按相机逐项定位，每轮末尾都会去取下一项来切换顶针。列表为空时第一项就会失败，最后一轮也会超出范围；出错后按异常返回。',
          ['tc-batch-old'],
        ),
        step(
          'state',
          '当前没有统一收尾保存',
          '旧做法里的收尾清理、归还顶针和保存都已停用；在主程序里也找不到实际执行它的位置。实验用的重复校准另有自己的一套准备环节，不能因此认为主页面上的“一键组合”已经启用。',
          ['tc-batch-old', 'tc-batch-experiment', 'tc-page-combined'],
        ),
      ],
    ),
    choices(
      'tc-pick',
      '取片偏移校准',
      '先看准备结果能否阻断后续动作，再区分单点、两点和重新取片。',
      ['tc-page-pick', 'tc-pick-prepare', 'tc-pick-core'],
      [
        step(
          'selection',
          '物料、吸嘴与 P1 模板',
          '页面检查所选物料及其绑定的吸嘴，可选重教物料的上视模板；重教被取消或被拒绝开始时会直接结束。准备环节另外检查 P1 点的 PR，并请求更换吸嘴；这些检查不能用最后的成功提示代替。',
          ['tc-page-pick', 'tc-pick-prepare'],
        ),
        step(
          'ready',
          '准备早退没有透传结果',
          '准备环节检查供晶是否就绪，成功后缓存状态、复位信号、设置要料物料与信号并完成初始化。就绪检查不通过时，只是这一步准备提前结束，页面随后仍会启动校准任务；窗口加载时会清掉就绪缓存。',
          ['tc-pick-prepare', 'tc-page-pick', 'tc-page-close'],
        ),
        step(
          'source',
          '晶圆与翻转取片分开',
          '按物料是否使用翻转台来选择取片辅助方式，不使用翻转台时直接给出失败结果。普通路径会检查取片动作的结果；翻转辅助在对应位置没有做同样的判断，后面又按漏晶检测处理，两种成功结果的依据不能混为一谈。',
          ['tc-pick-core', 'tc-pick-wafer', 'tc-pick-flip'],
        ),
        step(
          'single',
          '单点成功或重取',
          '移动到叠加吸嘴高度偏移后的实际拍照位，按视觉角度加吸嘴对齐角换算转角。单点定位成功时把结果换算成 G0 坐标作为物料中心；需要重试时先去安全位，再回到取片入口，其他结果按原样退出。',
          ['tc-pick-core'],
        ),
        step(
          'double',
          '两点分支保留现有差异',
          '当前两点分支没有先采 P1 点，第一点位置仍是初始值；按 P2 点的位置移动，却把 P1 点的位置和模板交给辅助定位，再用两点的中点求中心。这里不补画实际没有执行的第一点采样。',
          ['tc-pick-core'],
        ),
        step(
          'write',
          '累加偏移后抛料保存',
          '取片偏移累加“吸嘴上视中心减本轮物料中心”，随后抛料、去安全位并保存物料配置。上视辅助的重取还会刷新图片、要料、抛料并置上重取标记；它不是只在原位置重新拍照。',
          ['tc-pick-core', 'tc-uplook-retry'],
          [
            outcome(
              '中途异常',
              '后续抛料或移动失败时，不会统一撤回已经累加的偏移值；界面的收尾只恢复按钮状态，只有结果为成功才提示校准完成。',
              'tc-pick-core',
              'tc-page-pick',
            ),
          ],
        ),
      ],
    ),
    choices(
      'tc-results',
      '保存取消与工具',
      '把数值何时写入、何时保存、窗口怎样返回，与实际工具状态分开阅读。',
      ['tc-center-finish', 'tc-height-finish', 'tc-ejection-finally', 'tc-pick-core'],
      [
        step(
          'persistence',
          '各入口保存时点不同',
          '示教窗口、吸嘴自动校准、单顶针自动校准和取片偏移没有统一的保存事务。下表集中列出各自实际的保存时点；“保存”只表示执行了存储动作，不能据此认为失败时已经回滚，也不能说明现场精度已经合格。',
          [
            'tc-center-finish',
            'tc-height-finish',
            'tc-nozzle-pr-finish',
            'tc-nozzle-auto',
            'tc-ejection-finally',
            'tc-ejection-teach-finish',
            'tc-batch-old',
            'tc-pick-core',
          ],
        ),
        step(
          'tools',
          '人工确认的返回边界',
          '换嘴按自动换嘴架或人工确认分成两种做法：人工取消时按未通过处理，确认后写入当前工具名并打开真空。还嘴的两个手工分支在取消之后仍可能更新槽位状态并按成功处理，所以准备环节拿到成功结果，不等于工具已经实际归位并核实。',
          ['tc-change-tool', 'tc-return-tool'],
        ),
        step(
          'cancel',
          '关闭不等于撤销全部动作',
          '中心、高度和 PR 示教的取消都没有统一的数值还原；顶针窗口关闭会归还顶针并到安全位，吸嘴 PR 窗口关闭会到安全位。主校准窗口关闭时会发出停止请求，但没有在这里等待全部后台任务结束。',
          [
            'tc-center-finish',
            'tc-height-finish',
            'tc-nozzle-pr-close',
            'tc-ejection-close',
            'tc-page-close',
          ],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '覆盖当前独立校准、示教、尚未启用的组合，以及旧的整组顶针校准；没有执行设备动作，也没有验证标定精度。公共坐标、视觉及安全运动在对应图谱阅读，实际换嘴工艺和生产取片在所属图谱继续展开。',
      refs: ['tc-page-combined', 'tc-nozzle-auto', 'tc-batch-old', 'tc-pick-core'],
    },
  ],
};
