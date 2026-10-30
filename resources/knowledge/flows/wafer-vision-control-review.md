# 原视觉分析与供晶控制验证

原AnalyseDie、GetOffsetWorld及两个匹配分派包装接入后，39个原方法与3属性的118项受控断言通过。Single、Mapping、Box在匹配中Stop后经StopSearch拦截取料；Nine成功路径仍可在Stop状态调用最终XY并发许可。相机中心绑定原表达式；采集、重复定位、标定变换和驱动SDK仍为替身，非设备验收。

## 证据与范围
- 测试：wafer-vision-control-test.json；118项断言、42段原始方法/属性、23份来源哈希、3个原信号绑定。
- 完整原AnalyseDie(bool,out bool,string)、GetOffsetWorld、无参MatchResult和MatchFrameResult已执行；CameraCenterPixel另外逐字绑定原表达式(1224,1024,0)。
- .NET 10.0.11受控编译执行，不是原Framework完整工程构建。
- MatchResult(string,bool,bool)采集流程仍为脚本替身；ToRequiredAccuracy、BlobResult、AheadReachEnd、实际标定变换、计数存储、UI、驱动及I/O为替身。

## 验证结果
- 成功匹配取首结果；frame失败保留旧偏移，关闭frame清零。GetOffsetWorld在线先变换匹配和相机中心再相减；离线返回输入对象。
- 墨点自动/人工跳过及计数部分写入、重复定位重试、空晶阈值和提前换料均覆盖。匹配失败的Retry表示提前换料；OK/Cancel重新分析。
- 重复定位失败非Retry返回skip，包括脚本Abort值；这不证明真实界面提供该按钮。
- 依赖异常、缺失模板、null/空匹配数组以及Box非短路范围求值均有明确断言。
- 四模式正常完整供晶均通过；Single/Mapping/Box匹配中Stop后停止检查触发安全处理且不发许可，Nine匹配中Stop仍可最终XY并发许可。
- AnalyseDie的Cancel重试本身不重新检查Stop。

## 未完成项
完整视觉采集包装、真实SDK/图像生命周期、原生UI、并发启动、原工程构建、配置/DLL与现场设备验收仍待完成；29组模块保持部分复核。
