# 坐标模块：视觉结果到机械目标

2026-09-28。限定复核坐标加载、正反转换及点胶入口；未验收全部标定和运动SDK。

## 实际链路

- 点胶ConvertVisionResultInG0将MatchResult中心和拍照轴位置交给相机从属坐标系；未传位置时读取当前轴位置。MoveToG0Pos3D入口再把G0目标转换为点胶机械坐标。这里只证明坐标接入位置，不等于后续轴移动已完成。[结果791–821](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L791)；[移动入口129–144](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L129)。
- MachineCoordinateSystem.GetInstance按需读取JSON，null则新建；Init按UpperName查找父对象，没有在此校验父项存在或形成环。Refresh仅清空单例，Save调用JSON helper，没有本地事务或catch。[33–88](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L33)。
- 配置文件在启动目录Settings/DeviceParams/MachineCoordinateSystem/MachineCoordinateSystem.json；标定文件由同目录名称加.iwcal导入。[StaticPara21–30](../../trunk/AKRS.Galaxy2.CoordinateSystems/StaticPara.cs#L21)；[Import168–179](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs#L168)。
- CreateCoordinateSystem若找不到上层且upperName为G0，会创建、保存并直接返回G0，本次不会继续创建请求的子坐标；其他缺失父级抛异常。有父级时先删除同名项，再添加新普通/从属坐标并保存。[103–134](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L103)。
- GeneralCoordinateSystem.SelfPosToG0沿父引用收集当前层到根的链，再依次Forward；G0PosToSelf沿同一链逆序Back。停止条件是父引用null，不检查根名是否G0；无环检测，缺父可能提前停止，成环配置可能不终止。这里是代码边界，实际配置是否发生需核实。[44–101](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/GeneralCoordinateSystem.cs#L44)。
- DependentCoordinateSystem.SelfPosToG0加静态锁：自身Forward→加传入上层坐标→调用直接父级Forward，只处理这两层，不继续遍历祖先；父级null未见防护。其G0PosToSelf(List)只是返回new AKRSPoint3D，不能当作已实现的逆转换。[44–61](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/DependentCoordinateSystem.cs#L44)。
- Base的General正向为旋转加Distance、Z相加；反向去偏移和角度。Degree直接传Math.Sin/Cos，这段使用弧度，不能因变量名断言是角度制。Vm正向按需读标定并转换后叠Z；Vm的3D逆向直接抛不支持异常。[84–109](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs#L84)；[140–162](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs#L140)。
- VM转换Realistic分支直接返回转换点；其他三种相机模式均用固定像素中心(1224,1024)的转换结果减目标转换结果，未知模式返回null。CalculateMvdPointF设置Position/Negative、输入点、Run，再取Result；未见本地校验SDK运行状态。[241–294](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs#L241)。

## 输入输出与缺口

输入是坐标树JSON、Distance/Degree、像素点/轴位置和.iwcal；输出是计算后的点或异常。上述转换方法没有实际轴运动指令，运动执行属于上层控制器及硬件模块。

- 待核实所有坐标构建调用、G0创建约定、父级缺失/成环、配置角度单位及完整标定/补偿链。
- 待验证固定像素中心与真实相机分辨率的匹配；从属坐标父级层数与当前设备结构是否一致。
- JSON helper、标定SDK和加载DLL版本、运动安全/超时/停止路径仍未闭环。
- 本轮未修改生产源码，未进行构建或设备运行。
