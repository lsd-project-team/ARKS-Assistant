# 吸嘴对准：辅助视觉搜索与运动门控

更新：2026-09-28。范围为trunk中的FrmToolAlignmentTeach辅助搜索、PR调用、坐标转换及移动/对焦入口。仅源码追踪，不执行设备。

## 工作流摘要（先于任何绘图）

编辑模板按圆形/非圆形选择共享名称“圆搜索”或“矩形搜索”；不存在则创建Calibration PREntity，打开编辑器后无条件调用视觉库Save。

点击搜索先确认模板存在，再UpLookCameraVision(null,name,true)：本调用不传拍照位置，因此包装内不会先移动到拍照位。包装按VisionRetryTimesLimit有限尝试，调用VisionService.Vision；全部为空后，界面再询问Retry/Cancel，Retry从头再次执行该包装。识别非空后，使用当前G0位置加上上视相机坐标转换结果，再转机械坐标；分别检查X、Y位移绝对值是否大于3，超出则返回，否则调用MoveBondXY。

MoveBondXY为void；WaitSingleStep拒绝时直接return，调用界面没有运动成功返回值。识别非空、距离检查通过、发起移动与实际运动完成是不同层次。



## 完整调用链与源码入口

以下链接指向带行号原文与文件SHA-256；阅读器每段还提供实际源码文件链接。

1. [模板编辑](vision-teaching-source.html#template)：固定名称查找/创建，再编辑、保存。默认PREntity创建XldModelAlg；不能凭“圆搜索”名称推断最终算法配置。[默认算法](vision-teaching-source.html#default-alg)。
2. [搜索入口](vision-teaching-source.html#search)：模板不存在即结束。传入null拍照位置，不在包装内预移动。识别耗尽空值尝试后才弹人工Retry/Cancel；人工Retry重启整轮。
3. [上视包装](vision-teaching-source.html#uplook)：调用当前Matter、配置延时与VisionService。重试参数与整数计数器比较；0不尝试，2.5会尝试3次。异常不转换为空结果，不进入同一空值重试路径。DryCycle跳过识别，返回[默认中心1224/1024](vision-teaching-source.html#default-match)，仍进入后续换算，不能据此断言真实设备一定移动或一定不移动。
4. [硬件绑定](vision-teaching-source.html#hardware)→[识别服务](vision-teaching-source.html#vision-service)→[PR执行](vision-teaching-source.html#pr-work)：绑定相机/轴/光源；配置光源、曝光等并执行采集。曝光等设置失败可仅记录后继续。
5. [抓图与算法](vision-teaching-source.html#pr-execute)：SnapShot为空返回非成功；Alg.SetImage→FindModel→MatchResults。保存回调与结果赋值在后面的try内，FindModel不在该catch范围内；保存异常可能使结果保留None。按配置保存图像，并按postImage分派图像或释放。外部相机/算法SDK内部不作推断。
6. [坐标组成](vision-teaching-source.html#coordinate)：取换算时当前G0，加上上视标定ForwardConvertCoordinate中心结果，再转机械坐标。Search强转MatchResult，其他非空结果类型会抛异常。
7. [距离门控](vision-teaching-source.html#search)：X或Y绝对位移大于3则终止。不是欧氏总距离，3/3仍通过；本地没有显式有限数检查，NaN可穿过这一层，不能据此断言驱动执行。
8. [单步门控](vision-teaching-source.html#xy-step)：WaitSingleStep为false直接返回，无成功状态交还Search。
9. [XY运动](vision-teaching-source.html#xy-motion)：OffLineWork或轴未就绪返回；[就绪](vision-teaching-source.html#axis-ready)涉及X/Y/Z对象；[软限位](vision-teaching-source.html#softlimit)通过后分别下发X/Y并WaitAxesArrival。下发返回值在此处未判定；外部到位等待的超时/异常契约仍待补。Search没有完成回执，不能把按钮返回当物理到位证明。

## 独立自动对焦分支

[按钮](vision-teaching-source.html#focus-button)实际传BondCamera，上述搜索为UpLook，两者不能合并成同一相机链路。[选择与范围](vision-teaching-source.html#focus-select)依据相机枚举取配置Z中心及±3范围。[后台包装](vision-teaching-source.html#focus-task)禁用按钮，启动未等待的Task；捕获异常弹消息，finally恢复UI。

[实际算法](vision-teaching-source.html#focus-alg)：先到nLimit，分步粗搜并计算[外部SDK清晰度](vision-teaching-source.html#sharpness)，回到粗搜最佳点；细搜以分数变化决定继续、反向和缩小步长，达到第6轮下降分支才退出。该方法中细搜没有显式位置边界、总采样数/超时或取消检查；一直提高的分数不触发该退出分支。退出处虽注释“返回峰值”，没有对应的最终回峰指令。这是静态边界待复核，不是设备故障复现。

## 验证与缺失项

- [17项隔离测试](vision-teaching-test.json)：提取原Search、上视包装、坐标组成、单步包装和真实MatchResult默认构造函数编译；仅插值诊断文本为C#5改为常量。覆盖空模板、空值重试/取消、边界位移、DryCycle、NaN/Infinity、错误类型及异常传播。
- 相机服务、标定、硬件、UI和底层运动均为替身；未验证实际图像算法、标定精度、运动安全或对焦终止性。生产源码未修改，风险未修复。
- 待提供真实模板/标定/配置与配方，补外部MotionService和驱动契约、异常日志及离线硬件模拟，再做受控设备验收。
- 全局仍为29组部分复核、0组完整验收。本页19段独立证据不计为新增全局已验收模块。

复现：node scripts/test-vision-teaching.cjs；node scripts/build-vision-teaching-review.cjs --check；node scripts/verify-vision-teaching-browser.cjs。

验证结果：17项隔离检查通过，19段源码阅读器原文/链接/搜索检查通过，1440/850/390宽度无溢出或页面脚本错误；本轮verify-all: PASS。以上均为离线检查。
