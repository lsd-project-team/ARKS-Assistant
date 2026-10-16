# 原主窗口合成截图与客户区裁切复现

四个独立进程各47项通过，共188项；33项阶段绑定通过。原窗口HWND的PrintWindow能够捕获SDK文档界面，解决此前整窗体DrawToBitmap只显示灰色的取证缺口。同时复现布局问题：96 DPI下文档最小尺寸1920×999，大于主窗体客户区1536×793；TU、Wafer下部和右侧内容被裁切。原Program.Main字体、皮肤的公开设置比较中结果一致。合成截图取证通过，客户区布局验收未通过，未修复生产界面。410新增＋18295＝18705，507复用；整体目标未完成。

|每轮实际结果|bound默认|replay默认|bound原程序样式|replay原程序样式|
|---|---|---|---|---|
|运行检查／退出码|47／0|47／0|47／0|47／0|
|真实MainForm构造／Load|2／2|2／2|2／2|2／2|
|原MainDocument QueryControl实例|1|1|1|1|
|原生完整窗口尺寸|1552×832|1552×832|1552×832|1552×832|
|客户区尺寸／DPI|1536×793／96|1536×793／96|1536×793／96|1536×793／96|
|文档MinimumSize／实际Bounds|1920×999|1920×999|1920×999|1920×999|
|文档AutoScroll|false|false|false|false|
|原HWND合成图／DrawToBitmap图|3／4|3／4|3／4|3／4|
|SDK刷新写原HtmlText／UI异常|实际发生／0|实际发生／0|实际发生／0|实际发生／0|
|客户区裁切|已复现|已复现|已复现|已复现|

下图是原主窗体HWND输出，包含真实SDK文档；下方TU、Wafer被窗口边缘截断。不是物理桌面截图。

![原程序字体及皮肤设置下的主窗体裁切](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-mainform-layout/bound-program-style/native-document.png)

每轮先运行原NormalWork且AllAxisReset=false的复位门控，原Load禁用Tile并保留MF、后台线程及文档为null，公开Dispose。之后在离线Stop状态运行原MainForm构造和Load，真实DataLoad、ChangeData及离线Modbus入口执行；MF由原Load设置，SendUiAction保持原PostAction／this.Invoke。公开配方夹具MainFormLayout有两步骤／焊点，不是完整生产作业。

调用原SDK公开ActivateContainer(PageGroup)后原UcMainSystem已实例化一次；继续ActivateDocument并泵消息，原SDK刷新实际写入主窗体标题。激活首页，再返回同一文档，QueryControl仍1次。文档真实父级为DevExpress DocumentContainer，FindForm为本轮实际MainForm。原MdiClient的托管Controls集合为空，原Form.DrawToBitmap遗漏此SDK表面；PrintWindow对原HWND、flags=2、GetWindowRect尺寸输出完整合成图，不依赖重画界面或替换SDK。

原Designer以MinimumSize和Size设置2194×1284、AutoScaleDimensions为8×18。实际字体缩放为7×14，得到round(2194×7/8)=1920、round(1284×14/18)=999，与实际控件和原IL一致。最小宽度超出客户区384，高度超出206；文档从客户区y=23开始，因此内容底端1022超过客户区793。没有修改Bounds、MinimumSize、DPI或显示器尺寸。该证据说明当前96 DPI／客户区配置下确有裁切，不能推断所有设备屏幕配置都裁切。

原程序样式轮明确只复制Program.Main中公开的Tahoma字体、BonusSkins注册、窗体皮肤启用、Office2010Blue、EnableVisualStyles及CompatibleTextRendering设置。没有执行原Program.Main、异常注册、Harmony补丁、版本检查、加密或任何设备启动。SDK字体属性相互关联，最终三个默认字体getter均为Tahoma9Bold；原MainForm自身仍Tahoma10Regular。默认模式UcMainSystem字体9Regular，样式模式9Bold，内部控件坐标会不同。同一模式的bound／replay完整布局相等，跨模式分别验收实测外框和裁切，不把两个主题内部布局强行归一。

返回首页时原文档托管Visible仍true、Bounds仍1920×999，但原SDK移动其原生RECT至(-1536,-770)，返回文档后恢复(0,23)。因此Visible getter不能单独证明当前文档呈现。原异步Splash关闭导致仅bound原程序样式的before-activation快照还有一个SplashScreen1；20份原始布局全部保留，对比例外精确限于这一个已识别窗体，不删除原记录。

28张实际PNG具有12个独立SHA，12个代表均通过view_image实际查看；保留全部原始图。每模式原生文档／返回图和bound／replay字节一致，首页合成图一致；四张完整子控件图底部状态时钟不同，未修改图像字节、裁图或归一化。PNG尺寸、SHA组和代表查看记录独立存于visual-review.json。

每轮公开ThreadFlag在Load前false，使原监控实际创建后0循环结束并Join；之后true仅允许原SDK刷新。两次公开Dispose避免触发生产Environment.Exit，原FormClosed退出链未执行。私有STA桌面只用于这些原窗体，输入桌面Default不变，wrapper Join及CloseDesktop实测完成；没有物理点击。未捕获原SDK基础刷新线程句柄，不能宣称其优雅停机；本轮也不替代前轮正常监控启动和真实退出证据。

执行前绑定360声明／242源文件、263原IL／9程序集，每轮16源码资源程序集路径和SHA一致。每轮28个Settings文件包括10可解析JSON、17原仓库空文件、1Wafer时间备份；默认bound／replay8个可解析JSON原始字节一致，另5日期路径只按明确原构造来源比较；样式轮27个非备份文件与同模式及默认对应项语义一致，时间备份各自绑定。本轮没有DataSave、图像消费者、SQL初始化／写入、业务Task、VM、硬件、Machine.Start或完整MSBuild执行。

保留一个默认46项初步进程，随后新增原Designer最小尺寸检查并扩展公开样式比较，当前四轮才计入188。四份只读校验器初稿分别误假设首页Visible=false、首页原生RECT布局、所有快照仅MainForm、两个主题内部坐标相同；按原始记录修正校验器，初稿完整保留，未因此重跑已接受CLR进程。

证据：[台账](native-mainform-layout-test.json)、[审计](native-mainform-layout-audit.json)、[进度](native-mainform-layout-progress.json)。16项目、29组、1436个C#文件、13项任务保持，29组仍partial，旧正式1328独立。下一步需对目标设备客户区和DPI制定布局适配并实测；继续原Program.Main完整入口、在线告警、已识别统计SQL、成功VM与设备、完整MSBuild／LC／Fody及部署。整体目标未完成。
