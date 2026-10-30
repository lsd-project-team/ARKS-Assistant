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
          '全部校准按钮被隐藏并禁用，处理体也全部注释。历史代码的顺序是顶针、吸嘴、准备取片、取片偏移；这里只保留其实现状态，不把这条历史顺序画成当前可执行流程。',
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
          '第一步保存当前 G0 上视位置、对齐角和机械 XY，再按当前 T 的正负旋转 180°。第二步圆嘴以两次机械 XY 半差写吸嘴偏移；矩形嘴写角点偏移，两点均值连同当前 Z 转为旋转中心。',
          ['tc-center-steps'],
        ),
        step(
          'search',
          '辅助搜索有移动范围门控',
          '辅助搜索按形状使用圆或矩形模板，空结果可重试或取消。结果转成机械目标后，X 或 Y 任一差值超过 3mm 就拒绝移动；模板编辑另有自己的保存调用。',
          ['tc-center-search'],
        ),
        step(
          'states',
          '状态与中心 PR 分别建立',
          '中心示教设置 ToolAlignment；矩形嘴还会使几何示教失效。自动校准准备检查高度、中心、几何三个配置状态。重新制作中心 PR 的一步窗口会换嘴、移动和定位，成功更新上视中心；它没有替代这三项初始示教。',
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
          '非离线先请求换成所选吸嘴，失败就退出初始化移动；成功后到 BMC 搜索机械位置的 Z+8mm。界面说明写约 5mm，图谱按实际执行的 8mm 说明。',
          ['tc-height-move'],
        ),
        step(
          'methods',
          '手动、TD 与真空三种来源',
          '手动模式用当前 Z 减 BMC 参考值。TD 或真空模式调用测高接口，只有返回 Success 才更新“测得高度−BMC 参考”；其他返回保留原偏移，不自动写成新高度。',
          ['tc-height-measure'],
        ),
        step(
          'service',
          '重测与取消保留实际结果',
          '测高调用以当前 Z 为搜索起点，向负方向搜索，参数超时为 10 秒，每次执行前停留 1 秒。失败可重测；取消后返回该次非成功结果。测高实体内部反馈仍由引用库实现。',
          ['tc-height-service'],
        ),
        step(
          'completion',
          '完成标记不能证明测量成功',
          '外层“完成”在 DoneAction 返回后仍设置 ToolHeight 可用、保存并返回 OK；离线早退、手动轴缺失时取消或自动测高失败，也可能走到这段。因此要区分高度值更新与窗口显示完成。',
          ['tc-height-measure', 'tc-height-finish'],
        ),
      ],
    ),
    choices(
      'tc-nozzle',
      '吸嘴自动校准',
      '当前自动方法执行 XY 中心校准，方法中的自动测高区没有启用。',
      ['tc-nozzle-prepare', 'tc-nozzle-auto'],
      [
        step(
          'prepare',
          '准备检查与重教取消',
          '先检查吸嘴存在及三个示教状态，再可选重做 PR，最后检查 PR 和上视中心。重教取消会返回 false；重教后拒绝开始会去安全位。准备方法没有无条件换嘴，换嘴发生在进入重教窗口等实际调用处。',
          ['tc-nozzle-prepare', 'tc-nozzle-pr-gate'],
        ),
        step(
          'first',
          '第一次定位立即写中心',
          '按吸嘴对齐角转 T，在保存的上视位置定位；失败返回 Exception，成功把像素结果转 G0 并立即更新吸嘴上视中心。这个对象写入发生在第二次定位之前。',
          ['tc-nozzle-auto'],
        ),
        step(
          'second',
          '旋转后修正 XY 再定位',
          '按当前角度正负旋转 180°，利用已有吸嘴旋转偏移修正机械 XY。第二次共同视觉传入空位置，使用移动后的实位；虽然 isZSafe 为 true，但空位置分支不会因此再执行拍照位移动。',
          ['tc-nozzle-auto', 'tc-common-vision'],
        ),
        step(
          'write',
          '两次 G0 结果半差写偏移',
          '第二次成功后，以两次 G0 结果差的一半更新 NozzleOffset.X/Y，再到安全位并保存。自动测高区全部是注释；第二次失败不会撤回第一次中心写入，也不会执行这段成功尾部保存。',
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
          '先排除翻转硬件配 Bond 相机的组合，检查槽、示教、PR 和校准位置；归还吸嘴后关真空、归还顶针、晶圆台到准备位、检查料片并将顶针台移工作位。此准备没有显式切换到所选顶针槽。',
          ['tc-ejection-prepare'],
        ),
        step(
          'wafer',
          '晶圆相机写世界结果首点',
          '自动方法先使 Bond 到安全位，再把顶针 Z 与晶圆相机 Z 移到各自校准位置。Block 匹配成功后取世界结果的首点，写顶针中心相对相机的偏差；匹配失败返回 Exception。',
          ['tc-ejection-auto'],
        ),
        step(
          'bond',
          'Bond 相机使用另一种转换',
          'Bond 分支另请求归还吸嘴，移动顶针校准 Z 并共同视觉定位；以机械原点 (0,0) 和 Bond 相机标定求 XY，写偏差并令 Z=0。不能把它与晶圆相机的世界首点当作同一算法。',
          ['tc-ejection-auto'],
        ),
        step(
          'teach',
          '重教先在 Load 中准备',
          '选择重做模板会打开一步示教窗，返回后直接结束本次按钮处理。IsShowDialog 当前只返回 true，准备动作在 Load；会按相机选择安全位或归还吸嘴，再整理晶圆台、检查料片并切换顶针。',
          ['tc-page-ejection', 'tc-ejection-teach-gate', 'tc-ejection-teach-load'],
        ),
        step(
          'teach-result',
          '重教同时记录高度和状态',
          '晶圆分支取世界结果；Bond 分支用像素转 G0 减当前 G0 求偏差。成功后记录相机拍照位/相机 Z、顶针 Z 和 PR 示教状态，归还顶针并返回 OK。手动换针按槽名查找并切换 Index；槽对象按同名关联顶针配置。',
          ['tc-ejection-teach', 'tc-ejection-change', 'tc-ejection-slot'],
        ),
      ],
    ),
    choices(
      'tc-batch',
      '全部顶针旧接口',
      '保留现有能力与失效边界，不能把旧接口包装成当前一键成功流程。',
      ['tc-ejection-list', 'tc-batch-prepare', 'tc-batch-old'],
      [
        step(
          'list',
          '列表来自当前针库',
          '列表按当前针库及顶针配置存在性收集槽，再 Filter、Distinct；槽对象按自己的 Name 查同名顶针配置。全部准备方法逐项检查示教状态、PR 和校准位置，再整理工作区域，准备完成与全部执行完成分别判断。',
          ['tc-ejection-list', 'tc-batch-prepare', 'tc-ejection-slot'],
        ),
        step(
          'loop',
          '末轮仍访问下一项',
          '旧全部校准方法标为 Obsolete，先访问列表第 0 项，再按相机逐项定位，每轮末尾都访问 i+1 切换顶针。空表在第 0 项失败，最后一轮也会越界；捕获后返回 Exception。',
          ['tc-batch-old'],
        ),
        step(
          'state',
          '当前没有统一收尾保存',
          '旧方法的 finally、归还顶针和保存都已注释；当前主工程直接调用检索只定位到声明。实验重复校准另调用另一套准备方法，不能据此推定主页面“一键组合”已启用。',
          ['tc-batch-old', 'tc-batch-experiment', 'tc-page-combined'],
        ),
      ],
    ),
    choices(
      'tc-pick',
      '取片偏移校准',
      '先看准备返回能否阻断，再区分单点、两点和重新取片。',
      ['tc-page-pick', 'tc-pick-prepare', 'tc-pick-core'],
      [
        step(
          'selection',
          '物料、吸嘴与 P1 模板',
          '页面检查所选物料及其绑定吸嘴，可选重教物料上视模板；重教取消或拒绝开始直接返回。准备方法另检查 P1 PR，并请求更换吸嘴；这些检查不由最后的成功弹窗代替。',
          ['tc-page-pick', 'tc-pick-prepare'],
        ),
        step(
          'ready',
          '准备早退没有透传结果',
          '准备检查供晶就绪，成功后缓存状态、复位信号、设置要料物料/信号并初始化。CheckIsReady 返回 false 时只退出这个 void 方法，页面随后仍会启动校准任务；窗口加载时会清就绪缓存。',
          ['tc-pick-prepare', 'tc-page-pick', 'tc-page-close'],
        ),
        step(
          'source',
          '晶圆与翻转取片分开',
          '按物料是否使用翻转台选择取片辅助，false 则返回 Fail。普通路径会检查 PickAction 返回值；翻转辅助在对应位置未同样门控该值，后续又按漏晶检测处理，不能把两种 true 的依据混同。',
          ['tc-pick-core', 'tc-pick-wafer', 'tc-pick-flip'],
        ),
        step(
          'single',
          '单点成功或重取',
          '到加上吸嘴高度偏移的实际拍照位，按视觉角+吸嘴对齐角转 T。单点定位成功把结果转 G0 作为物料中心；Retry 去安全位后回到取片入口，其他结果原样退出。',
          ['tc-pick-core'],
        ),
        step(
          'double',
          '两点分支保留现有差异',
          '当前两点分支没有先采 P1，p1Pos 仍为初值；按 P2 位置移动，却将 P1 位置和模板传入辅助定位，再用 (p1Pos+p2Pos)/2 求中心。这里不补画源码没有执行的第一点采样。',
          ['tc-pick-core'],
        ),
        step(
          'write',
          '累加偏移后抛料保存',
          '取片偏移累加“吸嘴上视中心−本轮物料中心”，随后抛料、去安全位并保存物料配置。上视辅助的重取还会刷新图、要料、抛料和置重取标志；它不是只在原位置重新拍照。',
          ['tc-pick-core', 'tc-uplook-retry'],
          [
            outcome(
              '中途异常',
              '后续抛料或移动失败不统一撤回已累加的对象值；界面 finally 只恢复按钮状态，只有 Success 才提示校准完成。',
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
      '把对象写入、保存调用、窗口返回和实际工具状态分开阅读。',
      ['tc-center-finish', 'tc-height-finish', 'tc-ejection-finally', 'tc-pick-core'],
      [
        step(
          'persistence',
          '各入口保存时点不同',
          '示教窗体、吸嘴自动、单顶针自动和取片偏移没有统一事务。下表集中列出实际保存入口；“保存”表示代码调用存储接口，不能据此推定失败分支已回滚或现场精度已合格。',
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
          '换嘴按自动架或人工确认分派，人工取消返回 false，确认后写当前工具名并开真空。还嘴的两个手工分支在 Cancel 后仍可能更新槽状态并返回 true，因此准备方法收到 true 不等于工具实际归位已核实。',
          ['tc-change-tool', 'tc-return-tool'],
        ),
        step(
          'cancel',
          '关闭不等于撤销全部动作',
          '中心、高度和 PR 示教的取消没有统一对象快照恢复；顶针窗关闭会归还顶针并到安全位，吸嘴 PR 窗关闭到安全位。主校准窗口关闭调用 Stop，没有在此等待全部后台任务结束。',
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
      text: '覆盖当前独立校准、示教、未启用组合和旧全部顶针接口；没有执行设备动作或验证标定精度。公共坐标、视觉及安全运动在对应专题阅读，实际换嘴工艺和生产取片在所属专题继续展开。',
      refs: ['tc-page-combined', 'tc-nozzle-auto', 'tc-batch-old', 'tc-pick-core'],
    },
  ],
};
