// 同步修正交付图、说明卡和离线搜索索引；仅包含已对照当前源码确认的改动。
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { knowledgePath } from './resources.mjs';

const replacements = [
  [
    '节点/ DLL / 传感器 / 实验窗体，最后都落到 MachineState.Stop。',
    '区分报警来源、分级处理与停止请求，沿实际分支理解任务退出。',
  ],
  [
    '节点/ DLL / 传感器 / 实验窗体，最后都落到 MachineState.Stop',
    '区分报警来源、处理分支与停止后的任务退出',
  ],
  ['Run / Pause / Stop', 'Working / Pause / Stop'],
  ['MachineState = Run', '检查、排序与启动任务'],
  ['四个线程、一个全局枚举、两种终值', '四类主任务、一个全局枚举、不同的等待与退出路径'],
  [
    '停机、暂停、急停都只是把全局枚举改成 Stop',
    '普通停止设置 Stop，暂停设置 Pause；急停还先停止各轴运动',
  ],
  ['区别只在谁改、多快改到', 'EmergencyStop 先逐轴 StopMove，再调用 Stop 清理软件状态'],
  ['急停没有独立通道', '急停先停轴，再清理状态'],
  [
    '「最容易踩」急停和普通停止走同一条路，没有独立通道。“急停不生效”的排查方向不是去找急停函数，而是看两件事：MachineState 有没有真的被改成 Stop、线程是不是卡在不再检查信号的地方。',
    '「最容易踩」区分停轴和任务退出：EmergencyStop 先逐轴停止运动，再调用普通 Stop。任务仍需走到状态检查处才能退出，硬件等待或内部循环可能延后退出。',
  ],
  ['线程已建好，等待放行', '待机状态，尚未启动生产'],
  ['状态变回 Run', '恢复为 Working'],
  [
    '「开始」只做一件事：把全局 MachineState 改成 Run',
    '生产启动先执行就绪检查，再设置 Working、初始化动作序列并按配置启动任务',
  ],
  ['这条链不用任何事件总线', '启动检查与生产任务分开'],
  [
    '线程自己转 while (Signal.WaitStart())，没人叫醒它',
    'Start 按配置启动任务；任务运行期间由 Signal.WaitStart() 检查暂停与停止',
  ],
  ['按钮同步改全局枚举，改完就返回', '按钮调用 Machine.Start，包含就绪检查、排序初始化和任务启动'],
  ['整条链路没有一个 await', '入口返回不等于任务完成'],
  [
    '硬件调用是阻塞的，所以 UI 卡住和轴卡住看起来一样',
    '生产任务内的硬件等待与 UI 线程阻塞应分别排查',
  ],
  [
    '「怎么跑」全是顺序代码，没有事件总线。Program.Main 一行行往下走，任何一步失败就 return：磁盘不足静默退出、加密狗失败释放互斥体后退出——两种情况都不弹提示。',
    '「怎么跑」程序初始化与生产启动分开。Main 的磁盘检查失败或启用的授权检测失败会提前返回；非离线硬件初始化有异常捕获和报警，捕获后没有在该处直接退出。',
  ],
  [
    '「最容易踩」启动失败常常没有任何窗口。程序没起来时先查这三处：磁盘容量、加密狗、InitAllHardware 是否抛异常——它外面没有 try/catch。',
    '「最容易踩」先区分软件未启动、硬件初始化报警和生产启动被拦截。InitAllHardware 位于 try/catch 内；生产启动还要经过回零、任务状态、安全门和运行环境检查。',
  ],
  [
    'GetHardware(&quot;BondZ&quot;) 里是中文常量，拼错在运行期才炸',
    'GetHardware(&quot;BondZ&quot;) 按固定名称查硬件，名称不匹配会影响运行',
  ],
  [
    'GetHardware("BondZ") 里是中文常量，拼错在运行期才炸',
    'GetHardware("BondZ") 按固定名称查硬件，名称不匹配会影响运行',
  ],
  ['点胶向固晶要料', '固晶侧向晶圆侧发送需料信号'],
  ['一轮里只有两次真正的视觉交互', '本图合并展示两类视觉对象'],
  [
    '识别 Die 与基板位，输出像素坐标与补偿量',
    '图中概括 Die 与基板位；实际视觉次数受配方、检测与重试影响',
  ],
  ['报警与停机：四条来源，一条出口', '报警与停止：来源、分级与退出条件'],
  [
    '「它是什么」把散落在 04、11、16、32 里的报警与停机事实拼成一张：四条来路 → 一个弹窗装配点 → 一条停机出口。',
    '「它是什么」汇总节点返回、平台异常、传感器与调试入口，并区分报警展示、处理选择和停止后的任务退出。',
  ],
  [
    '「怎么跑」节点返回值、DLL 异常、传感器扫描池、实验窗体，最后都汇成同一件事：把全局状态改成 Stop，然后由某个 WaitStart 发现并退出。',
    '「怎么跑」是否停止由所属入口、报警级别和返回值处理分支决定。进入 Stop 后，任务在再次检查停止状态时退出；Retry、忽略或未捕获异常应分别阅读。',
  ],
  [
    '「最容易踩」报警弹窗本身要投递到 UI 线程，报警风暴会拖慢界面；停机也不是立即的，最多要等一个 20 ms 的空转周期。',
    '「最容易踩」20 ms 是暂停时的轮询间隔，不是停机完成上限。硬件等待、弹窗和内部循环可能延后任务退出，Stop 状态不证明所有任务均已退出。',
  ],
  ['停机只有一条出口', '停止请求与任务退出分开'],
  [
    '不管从哪来，最后都是把 MachineState 改成 Stop',
    '报警不统一转成 Stop，需按返回值、级别和所属入口判断',
  ],
  [
    '没有独立的急停总线，也没有 CancellationToken',
    '急停先停轴再调用 Stop；任务没有统一的取消令牌退出流程',
  ],
  ['全局枚举，唯一停机开关', '停止状态，不代表任务已退出'],
  ['操作员确认 / 复位', '停止 / 急停入口'],
  ['改回 Run 才继续', '急停先停轴，再调用 Stop'],
];
const root = knowledgePath('archify/manuals');
for (const name of await readdir(root)) {
  if (!name.endsWith('.html')) continue;
  const file = resolve(root, name);
  let html = await readFile(file, 'utf8');
  for (const [before, after] of replacements) html = html.split(before).join(after);
  // 图中可见状态名、可访问标签与导出的 SVG 保持一致，稳定节点 ID 不变。
  if (name === '00-项目总览-停机语义.html')
    html = html
      .replace(/data-node-tag="Run"/g, 'data-node-tag="Working"')
      .replace(/>Run<| · Run</g, (s) => s.replace('Run', 'Working'));
  if (name === '01-启动流程与主界面.html') html = html.replace(/改成 Run/g, '检查并启动任务');
  if (name === '91-报警与停机.html')
    html = html
      .replace(/data-edge-label="复位"/g, 'data-edge-label="停止清理"')
      .replace(/>复位</g, '>停止清理<');
  // 作为产品图解打开时隐藏独立文档包的导航；独立打开与导出继续保留原能力。
  if (!html.includes('id="arks-manual-reader"'))
    html = html.replace(
      '</head>',
      '<style id="arks-manual-reader">html[data-reader="true"] #atlas-nav,html[data-reader="true"] .header,html[data-reader="true"] .cards{display:none!important}</style><script>if(new URLSearchParams(location.search).get("reader")==="1")document.documentElement.setAttribute("data-reader","true");</script></head>',
    );
  await writeFile(file, html);
}
console.log('已同步图解、说明卡、离线目录与搜索中的已核实修正。');
