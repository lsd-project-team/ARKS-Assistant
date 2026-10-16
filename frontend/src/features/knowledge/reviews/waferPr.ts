import { choices, flow, outcome, step } from './builders.ts';

export const waferPrFlows = [
  flow(
    'wafer-pr-camera',
    'PR 相机入口：灯光、采图与返回枚举',
    'PREntity.DoWork 在对象锁内设置采图条件并调用 Excute；失败来源与最终返回枚举需分别看。',
    ['v-pr-light', 'v-pr-call', 'v-pr-snapshot'],
    [
      step(
        'light',
        '可选设置硬件与采图条件',
        '传入 PRHardware 才 SetHardware；isSetLight=true 时按启用灯光设置亮度，等 15 ms，再设置曝光、增益和 Gamma/10。后三个 setter 返回 false 只记错误日志，未据此提前返回 Fail；此处没有全局 StopSearch。',
        ['v-pr-light', 'v-pr-camera-settings'],
      ),
      step(
        'snap',
        '采图为空时返回 None',
        'Excute 先把 result 设 None，在 using 中 SnapShot；bmp=null 则记错误和描述并 return，最终 DoWork 返回 None。另一个 Photograph(cameraName) 则设置相机名后拍照，为 null 时直接抛“采图失败”，不是同一种失败出口。',
        ['v-pr-call', 'v-pr-snapshot', 'v-pr-photograph'],
      ),
      step(
        'find',
        '算法 FindModel 后才处理保存和枚举',
        '有图就克隆，按 IsFlash/触发方式可创建关闭光源任务，随后在 lock(this) 内设图、FindModel 并赋 AlgResults。灯光任务没有在这一段等待；算法执行的 bool 与后续设置的 ExcuteResult 是两层结果。',
        ['v-pr-flash', 'v-pr-find'],
      ),
    ],
  ),
  choices(
    'wafer-pr-result-image',
    'PR 保存与展示：结果被异常截断的位置',
    '保存回调、结果枚举和展示顺序相互影响；Success 不证明保存已落盘。',
    ['v-pr-save-success', 'v-pr-save-fail', 'v-pr-post'],
    [
      step(
        'save',
        '保存回调先于 Success/Fail 赋值',
        'FindModel 成功时按 IsSaveImage 调保存原图回调，并先调用 IsSaveLocateImage() 再判断 postImage，满足才保存结果图；之后才赋 Success。失败时可先保存失败图，再赋 Fail。try 内回调或结果读取异常被记录，没有在 catch 补赋枚举，因此 result 可保留先前的 None。',
        ['v-pr-save-success', 'v-pr-save-success-end', 'v-pr-save-fail', 'v-pr-save-catch'],
      ),
      step(
        'post',
        'Success 展示也读取第 0 项',
        'DoWork 调 Excute 后释放 bmpClone。仅 Success 时创建展示对象并直接取 AlgResults[0].OutPutImg1，未检查数量；postImage=true 才选择广播通道，无接收通道就 Dispose 展示图。该展示代码在 Excute 的保存 catch 之外，异常可向上抛。',
        ['v-pr-call', 'v-pr-post', 'v-pr-post-finish'],
      ),
      step(
        'owner',
        '不同重载的展示图所有权不同',
        '相机重载直接引用第 0 项的输出图；Bitmap 重载则克隆该图用于展示。不能把无接收通道时的 Dispose 统一解释为只释放独立展示副本；也不能据 Task.Run 或保存回调证明文件完成写入。',
        ['v-pr-post', 'v-pr-post-finish', 'v-pr-bitmap-post', 'v-pr-bitmap-save'],
      ),
    ],
  ),
  flow(
    'wafer-pr-bitmap',
    'PR 已有图片入口：输入释放与九点复用',
    'DoWork(Bitmap) 使用传入图片执行算法，正常尾部会释放它；调用方要按实际所有权理解复用。',
    ['v-pr-bitmap-entry', 'v-pr-bitmap-dispose'],
    [
      step(
        'input',
        '空图片 Fail，有图先克隆并执行',
        '对象锁内 bmp=null 时直接 Fail；有图先写 OriginalBmp 克隆并另建 bitmapClone，再把传入 bmp 交给 Alg.SetImage、FindModel 和 AlgResults。这里没有与相机重载相同的 using 和保存 catch 范围。',
        ['v-pr-bitmap-entry'],
      ),
      step(
        'save',
        '保存克隆的后台任务不阻塞返回',
        '开启 IsSaveImage 时，成功和失败分别 Task.Run 保存 bitmapClone，任务里锁图片、建目录、Save、Dispose，异常被吞；没有在此等待任务。成功赋 Success、失败赋 Fail，随后显式 Dispose 传入 bmp，再处理成功展示。',
        ['v-pr-bitmap-save', 'v-pr-bitmap-save-fail', 'v-pr-bitmap-dispose'],
      ),
      step(
        'nine',
        'Nine 复用图片与被调用方法的释放冲突',
        'CalculateDiesPosition 对九个候选传同一 Bitmap；DetectInkDot 对 Exist=true 的候选调用这个重载。因此第一处执行正常完成后图片已释放，后续存在候选仍可能收到同一对象。这里展示调用关系导致的风险，不把九次调用写成必然全部完成，也不修改生产实现。',
        ['ws-nine-calculate-ink', 'ws-nine-ink', 'v-pr-bitmap-dispose'],
        [
          outcome(
            '存在标记回写是另一问题',
            'SingleDieInfo 为值类型，DetectInkDot 仍只修改形参副本；即使图片执行成功，这次赋值也不会写回九点缓存。两个边界不能合并为一个已经生效的自动过滤步骤。',
            'ws-nine-ink',
            'ws-nine-struct',
          ),
        ],
      ),
    ],
  ),
];
