# ZX2200 光源控制与亮度标定复核

对应原清单 09.01–09.04。读取主程序实际编译源码与 PR 工程调用；trunk 保持只读。以下记录静态调用与数值边界，没有执行运动、发光、拍照或实际灰度标定。

## 硬件与入口

主菜单 barBtnLightCalib 的 ItemClick 创建 FrmLightnessCalibTeach 并 Show；Designer 注册该事件。主界面的 BtLampRegulation 创建集中调光 UcLampRegulation，模组示教使用 UcGuideMove 中的两组 UcLight。

点胶 VisionModule 的点光和环光分别绑定“点胶三色点光/环光-红、绿、蓝”；DispenseVisionController.GetLights 固定顺序为点光红绿蓝、环光红绿蓝。BondModule 的 BOND 相机绑定“邦头三色点光/环光-红、绿、蓝”；GetHardware 在三色模式使用六路，其他模式只用红点和红环。

上视相机只有“上视点光”和“上视环光”两个硬件对象；UcGuideMove 和集中面板把同一个名称传给对应 RGB 三个参数，不能按三个参数推断三路独立灯。晶圆相机使用三色点光及“下视环光”；GetPrHardware 的三色和单色列表不同，StaticWaffle 分支改用 Bond 相机和灯。集中面板晶圆环光却传入“晶圆点光环光”两次和“晶圆环光蓝光”，与模块注册名不同，实际是否别名取决于外部硬件配置。

BondZ 标定相机的 GetHardwareZWithXY 使用点胶 VisionModule 的光源；该方法与 GetHardware 共用 hardware 缓存，首次建立后不会按另一相机重新创建。IPTModule 本身没有单独的相机/光源声明，不能凭工位名称新增一组 RGB。

依据：UcMainSystem.cs:1102–1127、1837–1841；UcMainSystem.designer.cs:1643–1647；UcLampRegulation.cs:25–59；UcGuideMove.cs:178–311；VisionModule.cs:21–51；BondModule.cs:104–239；UpLookModule.cs:25–37、80–98；WaferTableModule.cs:127–151；WaferTableController.cs:1248–1313、1837–1904；IPTModule.cs 全类。

## 手动调光与模板保存

UcLight 的滑块与数字框上限都是 100，ChangeIntensity 以整数 intensity×255/100 调硬件。选颜色时直接给选中通道原始值 90、其他通道 0；索引 7 也设白色。ChangeAllIntensity 按颜色组合设置通道，Customize 没有分支，末尾重复 Yellow 分支不可达。

滑块事件只在 TimeSpan.Milliseconds>10 时把值传给数字框，检查的是毫秒分量而非总毫秒；注释中的 100ms 不是实际门控。数字框事件先用旧滑块值调用 ChangeAllIntensity，再更新滑块。TbLight_MouseUp 虽有另一条发送路径，当前 Designer 未注册 MouseUp；CorrectLightColorTypeAndIntensity 当前也未见调用，不能描述为进入面板自动同步了硬件状态。Init 全空禁用，部分缺失只锁颜色选择；发令入口另依赖红通道存在。

集中面板的关闭按钮逐个调用八个控件 CloseLight，每组先发百分比 10 再发 0，最终意图归零；同名三参数可能重复发同一对象。这里没有写入视觉模板或 LightCalibratePara 的调用。

实际 FrmPREditor 通过 PRLightList 绑定硬件和模板强度，滑块直接发送原始整数，数字框显示随之更新；模板保存按钮才把可见/使用状态和强度写回 PRLightList 并在保存流程成功、确认后调用 VisionEntityRepository.Save。窗口关闭也调用仓库 Save，但不能因此推断所有未保存滑块值都已写回模板。UcPRLight 存在另一套百分比控制实现；当前编辑器 Designer 只见字段声明，不把它当作本路径实际创建的控件。

依据：UcLight.cs:67–154、207–322、329–425；UcLight.Designer.cs:62–120；UcLampRegulation.cs:49–59；FrmPREditor.cs:417–486、491–522、552–576；UcPRLight.cs 及编辑器 Designer 引用检索。

## 采集主链

两步示教分别提示点胶与 Bond 相机在白纸上方对焦，下一步保存点胶轴位置，Done 保存 Bond 机械位置并 Task.Run(LightnessCalibration)。Done 没有保存任务句柄、禁用重复发起或等待结果；Cancel 直接 Close，不向后台任务发取消信号。

正常主链先移动到两处机械位置，再把两相机曝光设 4000、Gamma 设 1、Gain 设 0，关闭十二路光。依次标定红、蓝、绿环光以及红、蓝、绿点光，将六组返回值逐个写到参数属性，全部正常返回后调用 Save。此处未消费移动或相机设置 bool，也没有统一 finally 恢复进入前的相机参数/灯光；中途异常可留下部分新表。

每组固定 Bond 强度点 0、64、128、192、255；每点设置 Bond 光后等待 500ms，拍 Bond 图像并计算平均灰度。接着在点胶侧做固定 8 次二分比较，每次设置 mid、等待 500ms、拍图并保留当前已测候选中的最小灰度差；low=mid 或 high=mid，不是 mid±1。LightControlStep=20 虽传入，实际匹配方法未使用 step。两端点不会由这八个 mid 自动穷举，且没有误差合格阈值或单调性验证。正常结束才把这一对灯设零。

灰度使用 8bpp Bitmap 转 Halcon 图像，在固定矩形 row 612–1836、column 512–1536 上计算 Intensity.Mean。转换异常仅给 image=null，后续没有对应空值检查；图像尺寸、格式和 ROI 是否适合实际相机需现场确认。LightnessRatio 是独立方法，按步长取样后求两组平均灰度之比，主采集链未调用，不替代六张映射表。

Save 的参数路径由 ZX2200PathConfig.LightCalibratePara 指向设备目录的 LightCalibratePara.json。这里证明保存调用与配置路径；基类/外部设备落盘持久性没有执行验收。

依据：FrmLightnessCalibTeach.cs:192–295、361–414、423–576、593–597；Designer.cs:183–217、265–274；ZX2200PathConfig.cs:240；LightCalibrationPara.cs:24–30。

## 补全、正反向与缓存

首次 GetDispenseIntensity 或 GetBondIntensity 都先 EnsureMappingsInitialized，再检查输入是否在 0–255。InitFullMappingDictionaries 遍历六种 LightType，为每类生成 256 项正向和反向字典，全部结束才将 _isFullMapInited 置 true。六张原始表是 Bond/Dispense 整数配对列表，属性写入没有缓存失效逻辑，Save 本身也不是重建字典。

正向 Bond→Dispense：0 强制返回 0；空表的原始正向算法返回输入；非空表按现有列表首尾作边界夹取，内部相邻点线性插值并 Math.Round，没有先排序。采集会按固定 Bond 点顺序建立列表，但外部写入的列表顺序不能由方法名保证。

反向 Dispense→Bond：0 给 0；其余按原始样点的 dispense 排序，首尾夹取或分段线性插值，内部结果 Math.Round 后限制 0–255。GenerateDispenseToBondFullDict 的 bondToDispense 形参实际未消费，依据仍是原始列表；任一空表会在 sortedMap[0] 访问失败，即便此次只想转换另一路或输入已越界，也可能在预初始化阶段失败。

ValidateAndFixMappings 遍历正向再反向的结果并输出不一致警告；有问题时仍按原始样点重建同一反向插值表，没有证明整数舍入或多对一映射可严格逆还原。_isFullMapInited 已 true 后，重新采集替换六张原表没有显式清缓存；后续转换会继续优先取现有字典。

依据：LightCalibrationPara.cs:18–30、32–122、127–218、225–271、318–355。

## 视觉应用与返回边界

ApplyLightMapping 按灯硬件名称匹配点胶六路并调用 GetDispenseIntensity；循环按 lights.Count 索引 originalIntensities，正向遇未知名称不追加，输出可缩短。反向方法对相同六类名称调用 GetBondIntensity，未知名称原样追加。两者都不按 IsUse 重新配对硬件列表，也没有统一校验列表长度与空硬件。

普通点胶定位与胶量检测在 visionPosition 非 null 时启动设灯任务：获取固定六路点胶灯、提取模板中 IsUse 的强度、正向映射，再给 PREntity.SetLight；与移轴并行，随后 task.Wait 才进入后续视觉。若强度列表不是六路同序，可能错位或越界。位置为 null 时跳过该预设块；DryCycle 检查在此块之后，不能描述为空跑完全不调光或不移轴。

PREntity.SetLight 优先采用传入 lights/intensities，按位置逐个 SetIntensity，然后设置曝光、增益与 Gamma/10；内部锁只保护该段，不代表所有调光入口串行。异常统一转抛“设置灯光和相机参数失败”。正常 BondCameraVision 用模板强度直接 SetLight，没有在该处反向转换。

报警编辑在 PRHardware 非 null 时锁 entity；若进入时相机为点胶，先把模板中的已用强度正向换算并写回对象，再 SetHardware、打开编辑器。编辑器关闭后，若此时仍为点胶相机，反向换算并再写回；两个判断使用各自时点的 Camera。最后仓库 Save、设备 Continue、恢复 isAllowWork。没有统一 try/finally 保证异常后反向恢复或继续；编辑过程中仓库也可先保存点胶侧数值。

依据：LightCalibrationPara.cs:364–451；DispenseVisionController.cs:123–245、252–263；PREntity.cs:101–159；System2Controller.Vision.cs:159–219；FrmVisionAlarm.cs:426–498。
