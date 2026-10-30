# 原力控标定计算、配置选择及数据保存导出

两个全新 Framework CLR 宿主各46个不同断言通过。全部执行原ForceCalibrationService与原ForceConfig/ForceCalibrationData、实际SDK单例/JSON和EPPlus；数据是公开设置的数值样本，没有物理标定。64原IL方法含45个仅静态Xtra重载，11源码哈希、16保真源程序集；父5886+新增75=5961冻结绑定。

## 成功计算与原动作调用关系

小力公开样本：角0°的力/增量为10/2、20/4、30/6，角90°增量翻倍；大力100/20、200/40、300/60及90°翻倍。分界100g、初值字典0°→5、90°→15。样本只是验证原计算，不是现场有效标定或实际单位换算验收。

|原方法与输入|实际原结果|
|---|---|
|小力forward 15g、initial10、angle0|增量插值3，结果(3+10)/100=0.13|
|同样小力、angle45/46|0.13/0.16；等距保留第一项，46选择90°|
|同样小力、angle360|选90°，0.16；线性距离不按360环绕|
|大力forward 150g、initial999、angle45/46|0.35/0.75；先按角字典替换调用方初值|
|小力inverse增量1.999/2/3|0/10/15g；多条时低于2返回0|
|inverse增量8、angle0|最后两点向上外推40g|
|inverse增量3、angle90|低于最小增量，用首点比例得到7.5g|

原ForceControlSet两硬件分支均调用forward，GTForceControlSet调用初值/大小PID选择及GetForceModelChange；原Bond.RecordLastBondForce调用inverse。这三条调用方仅只读IL核对，未执行硬件控制或焊后采样。GetSmallForceModelChange在主工程唯一已发现的控制器引用是注释，不据该计算独立通过声称设备使用该分段逻辑。

## 未标定、异常和非有限数

原forward在空关系Aggregate、空初值字典Aggregate、空选中行列表索引处失败，发生于意图显示的“未标定”检查之前；inverse空关系捕获Exception并返回999，空行列表返回0。单行forward直接CaliTableForce/100，忽略增量和初值；单行inverse直接返回力，绕过低于2接触守卫，输入−50仍得到7。

forward选中区间的后一项增量0，即使输入恰等于前一项力也抛错。重复力横坐标forward产生NaN；重复增量横坐标inverse产生NaN，没有转成999。NaN力在大小判断中归大力，forward没有区间命中返回0；NaN角保留第一角。inverse NaN→0、正Infinity外推→Infinity、负Infinity→0。这些非法公开样本暴露原守卫边界，不是有效工艺输入。

小力forward最后检查SmallForceConfigItemList.Last().ForceUpperLimit，配置空会在Last异常。低于标定范围和未排序的30→10端点都会走原AKRSXtraMessageBox警告；公开MainForm.SendUiAction各收集原Action后抛同一fixture InvalidOperationException，因此中断在预定“输入力值超出范围”抛出之前。共2个Action、执行0个，DB Lazy未创建。没有模拟人工OK或运行真实窗口。

inverse catch日志原源码使用ex.ToString方法组而非调用；原IL实际创建Func<string>再调用该delegate的Object.ToString。这里登记静态字符串构造问题，未检验最终日志文件内容或修改源码。

## PID范围与阈值

原GetSmall/GetLargeForceConfigItem先按lower排序并替换公开列表，条目对象保留。范围上下端均inclusive，公共端点先命中低段；低于最小返回首项，高于最大返回最后项，中间空隙返回null。NaN返回null，空列表在索引处失败。

原GetSmallForceModelChange按全列表min/max分三份：配置0~300、initial10时，input50/100/200/300分别0.03/0.091/0.1981/0.2971；各用差值50%、10%、1%后除1000。0、超过上限、初值大于输入拒绝；NaN输入返回默认0，NaN初值传播NaN。原GetForceModelChange直接减lower与changeLower差再除1000，可返回负数，null条目NRE；没有自行模拟PID或调用驱动器。

## 实际JSON与Excel导出

原两个单例实际Save生成隔离Settings/DeviceParams中的ForceConfig.json和ForceCalibrationData.json。标定时间固定为2020-01-02 03:04:05、耗时12.5；独占锁定标定文件再Save，实际SDK SaveGenericObject删除临时文件后把IOException包装成普通Exception、InnerException=null。旧文件字节严格不变；两轮两个JSON文件SHA相同。原ForceCalibrationData.Load替换单例对象，恢复耗时/角字典/两角数据，随后原forward仍得0.13。配置Save执行，但本轮未Load配置，也未验证厂商/织入属性通知。

原ExportCaliData在两个关系列表都空时不创建文件；非空时实际EPPlus生成calibration.xlsx，名为“小力”“大力”的两张表，每表6数据行和6列标题。实际读回角度、指令模拟量、初值、增量、应变片力、标定台力及90°排序，均来自公开真实样本。再次导出到同名已有工作簿遇重复worksheet名InvalidOperationException，没有追加。两轮验证相同单元格/结果，不声明xlsx压缩包时间戳或整体字节一致，也不是外部Excel界面/现场数据验收。

## 验证与保留诊断

初次原生23379a通过37项后，探针对锁定Save错误预期IOException；原SDK实际包装普通Exception，失败输入/产物/原目录全部保留。第二次17e5c9通过38项后，探针byte[].SequenceEqual绑定到System.Memory Span扩展，实际SDK依赖缺System.Numerics.Vector而TypeLoadException；这是探针比较代码边界，不能写成力控生产函数失败。改为明确System.Linq.Enumerable.SequenceEqual<byte>，未换DLL、运行映射或生产源码。

接受的第三版c2ac18 46项通过；9f7d00独立重编译及全新replay宿主再46项通过，emit SHA/标签/结果及两JSON SHA一致。每轮16源码程序集从真实bound/replay加载，162引用含10直接源引用，runtime-map172项。最终IL c36ffb；父流水线89663/3dfcd9通过；预检/冻结/绑定754234通过，无独立session。

未执行物理标定、串口/压力清零、采样、轴/贴片、真实相机/UI/SQL、完整Task/生产循环或MSBuild/部署；无生产C#/工程/私有状态修改与SDK/动作替身。正式1328、旧40专题3817及主阅读器保持冻结。继续力控采样/闭环/实际标定及设备成功链、S2清零正常结果/整调度、Retry/握手与构建运行依赖；16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-force-calibration-test.json)、[审计](native-force-calibration-audit.json)、[进度](native-force-calibration-progress.json)。
